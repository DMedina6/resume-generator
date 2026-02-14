"""Generate a one-page resume PDF from a JSON file.

This script intentionally uses low-level ReportLab drawing primitives (Canvas + drawString)
instead of higher-level layout engines. That keeps output predictable and ATS-friendly.

Mental model (ReportLab basics):
- The page coordinate system is measured in points (1 inch = 72 points).
- The origin (0, 0) is at the bottom-left corner of the page.
- Text is drawn at a *baseline* (x, y). After drawing a line, we manually subtract from
    `y` to move down the page.

Layout approach:
- Each section renderer takes a starting `y` and returns the next `y`.
- Empty fields/sections are skipped so we never render "dangling" labels or blank lines.

If you're new to ReportLab:
- Think of `Canvas` as a "pen" you draw with. There is no automatic layout: you must
    choose fonts, positions, and line spacing yourself.
- Most functions in this file follow the same pattern:
    1) draw some text at the current y
    2) subtract from y to move down
    3) return the updated y
"""

from __future__ import annotations

# `from __future__ import annotations` lets us write type hints that refer to classes
# defined later, and generally keeps type hints from affecting runtime performance.

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, List, Literal, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


Style = Literal["ats", "pretty"]

# `Style` is a *type hint* only. At runtime it's just a string.
# We use it to keep `--style` values constrained to "ats" or "pretty".

# Data shapes used within ResumeData. These aliases are purely for readability.
ExperienceItem = Tuple[str, str, str, List[str]]  # (company, role, dates, bullets)
ProjectItem = Tuple[str, str, List[str]]  # (name, meta, bullets)
EducationItem = Tuple[str, str, str]  # (degree, school, dates)


def _as_text(value: Any) -> str:
    """Convert JSON values to display text (None/whitespace -> "")."""
    # JSON can contain `null` (Python: None) or values with extra whitespace.
    # Normalizing here keeps the drawing code simple.
    if value is None:
        return ""
    return str(value).strip()


@dataclass(frozen=True)
class ResumeData:
    """Normalized resume content used by the PDF renderer.

    All string fields should already be trimmed. Missing values are represented as
    empty strings/lists so renderers can simply "skip if empty".
    """

    name: str
    title: str
    location: str
    phone: str
    email: str
    website: str
    linkedin: str
    github: str

    summary: str
    skills: List[str]

    experience: List[ExperienceItem]
    projects: List[ProjectItem]
    education: List[EducationItem]
    certifications: List[str]


# ----------------------------
# JSON -> ResumeData
# ----------------------------


def _resume_from_mapping(payload: dict[str, Any]) -> ResumeData:
    """Convert a JSON object into normalized `ResumeData` (missing/blank -> empty)."""
    # Keep this permissive: callers can omit keys, and empty strings are treated as
    # "do not render".
    #
    # Tip if you're newer to Python: the `payload.get("key", default)` pattern returns
    # the value for "key" if it exists, otherwise it returns the given default.
    return ResumeData(
        name=_as_text(payload.get("name", "")),
        title=_as_text(payload.get("title", "")),
        location=_as_text(payload.get("location", "")),
        phone=_as_text(payload.get("phone", "")),
        email=_as_text(payload.get("email", "")),
        website=_as_text(payload.get("website", "")),
        linkedin=_as_text(payload.get("linkedin", "")),
        github=_as_text(payload.get("github", "")),
        summary=_as_text(payload.get("summary", "")),
        # The list-comprehension syntax here means:
        # "for each element in the input list, convert it to text, and collect results"
        skills=[_as_text(s) for s in payload.get("skills", [])],
        experience=[
            (
                _as_text(item.get("company", "")),
                _as_text(item.get("role", "")),
                _as_text(item.get("dates", "")),
                [_as_text(b) for b in item.get("bullets", [])],
            )
            for item in payload.get("experience", [])
        ],
        projects=[
            (
                _as_text(item.get("name", "")),
                _as_text(item.get("meta", "")),
                [_as_text(b) for b in item.get("bullets", [])],
            )
            for item in payload.get("projects", [])
        ],
        education=[
            (
                _as_text(item.get("degree", "")),
                _as_text(item.get("school", "")),
                _as_text(item.get("dates", "")),
            )
            for item in payload.get("education", [])
        ],
        certifications=[_as_text(c) for c in payload.get("certifications", [])],
    )


def _register_fonts() -> None:
    """Try to register nicer fonts if available; fall back to built-ins."""
    # If these TTFs aren't present, ReportLab will use built-in Helvetica.
    # Registering fonts makes them available to `setFont`, but we still need to opt-in
    # by passing the registered font names (e.g., "Inter").
    #
    # This is intentionally "best effort" so the script runs on any machine.
    try:
        pdfmetrics.registerFont(TTFont("Inter", "Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "Inter-Bold.ttf"))
    except Exception:
        pass


def _wrap_text(
    canvas: Canvas,
    text: str,
    max_width: float,
    font_name: str,
    font_size: int,
) -> List[str]:
    """Greedy word-wrap for a single paragraph based on rendered width.

    Notes:
    - Uses `canvas.stringWidth` so wrapping reflects the actual PDF font metrics.
    - Does not hyphenate; a single very-long word may overflow.
    """
    if not text or not text.strip():
        return []

    # Split by whitespace into "words". We then build up lines word-by-word until
    # adding another word would exceed `max_width`.
    words = text.split()
    lines: List[str] = []
    current: List[str] = []

    # In ReportLab, measuring and drawing both depend on the active font.
    canvas.setFont(font_name, font_size)
    for word in words:
        candidate = (" ".join(current + [word])).strip()
        if canvas.stringWidth(candidate, font_name, font_size) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_rule(canvas: Canvas, x: float, y: float, w: float) -> None:
    """Draw a light horizontal divider."""
    # `line(x1, y1, x2, y2)` draws a straight line in the current stroke color.
    canvas.setStrokeColor(colors.HexColor("#D6D6D6"))
    canvas.setLineWidth(1)
    canvas.line(x, y, x + w, y)


def _draw_section_title(
    canvas: Canvas,
    title: str,
    x: float,
    y: float,
    w: float,
    *,
    style: Style,
) -> float:
    """Draw a section heading and return the next baseline y position."""
    # ReportLab uses *stateful* drawing: font/color settings stick until changed.
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#222222"))

    # ATS: keep headings simple for cleaner text extraction.
    canvas.drawString(x, y, title.upper())
    if style == "pretty":
        _draw_rule(canvas, x, y - 6, w)
        return y - 20
    return y - 16


def _draw_bullets(
    canvas: Canvas,
    bullets: Iterable[str],
    x: float,
    y: float,
    w: float,
    font_name: str = "Helvetica",
    font_size: int = 10,
    leading: int = 13,
    bullet_char: str = "•",
) -> float:
    """Draw a bullet list and return the next baseline y position.

    We manually handle indentation and wrapping so bullets look consistent across
    PDF viewers and stay single-column for ATS parsing.
    """
    bullet_indent = 10  # where the bullet glyph is drawn
    text_indent = 22  # where wrapped text starts

    # `leading` is the vertical spacing between baselines.

    canvas.setFillColor(colors.HexColor("#222222"))
    for b in bullets:
        b = (b or "").strip()
        if not b:
            continue
        wrapped = _wrap_text(canvas, b, max_width=w - text_indent, font_name=font_name, font_size=font_size)
        if not wrapped:
            continue

        # Bullet glyph (only once per bullet item).
        canvas.setFont(font_name, font_size)
        canvas.drawString(x + bullet_indent, y, bullet_char)

        # First wrapped line appears on the same baseline as the bullet.
        canvas.drawString(x + text_indent, y, wrapped[0])
        y -= leading

        # Remaining lines: keep the same text indent, no additional bullet glyph.
        for line in wrapped[1:]:
            canvas.drawString(x + text_indent, y, line)
            y -= leading

    return y


def _draw_tag_row(canvas: Canvas, tags: List[str], x: float, y: float, w: float) -> float:
    """Draw a compact comma-separated tag row (e.g., skills), wrapped."""
    # This is used for the Skills section to keep a keyword-dense line without
    # resorting to multi-column layouts.
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#222222"))

    line = ""
    # We build a comma-separated line until it would overflow, then start a new line.
    for tag in tags:
        piece = (", " if line else "") + tag
        candidate = line + piece
        if canvas.stringWidth(candidate, "Helvetica", 10) <= w:
            line = candidate
        else:
            canvas.drawString(x, y, line)
            y -= 13
            line = tag
    if line:
        canvas.drawString(x, y, line)
        y -= 13
    return y


def _clean_str(value: Any) -> str:
    """Convert a value to a trimmed string (None -> "")."""
    return str(value).strip() if value is not None else ""


def _is_blank(value: Any) -> bool:
    """True when a value is missing/empty after trimming."""
    return not _clean_str(value)


def _draw_header(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Draw name/title/contact block and return the next baseline y position."""
    # Header uses slightly larger fonts and a different color for visual hierarchy.
    name = _clean_str(data.name)
    title = _clean_str(data.title)

    if name:
        # `setFillColor` controls text color; `setFont` controls font face/size.
        c.setFillColor(colors.HexColor("#111111"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(x, y, name)
        y -= 18

    if title:
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(x, y, title)
        y -= 16
    elif name:
        y -= 6

    # Contact info: never render labels/separators for empty values.
    # This avoids artifacts like "LinkedIn:" showing up when the JSON has "linkedin": "".
    location = _clean_str(data.location)
    phone = _clean_str(data.phone)
    email = _clean_str(data.email)
    website = _clean_str(data.website)
    linkedin = _clean_str(data.linkedin)
    github = _clean_str(data.github)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#444444"))

    contact_lines: List[str] = []
    if style == "ats":
        # ATS: prefer predictable, labeled lines over dense inline separators.
        # We build each contact line only if there is at least one real value.
        if location:
            contact_lines.append(f"Location: {location}")
        if phone or email:
            parts: List[str] = []
            if phone:
                parts.append(f"Phone: {phone}")
            if email:
                parts.append(f"Email: {email}")
            if parts:
                contact_lines.append(" | ".join(parts))
        if website or linkedin or github:
            parts = []
            if website:
                parts.append(f"Website: {website}")
            if linkedin:
                parts.append(f"LinkedIn: {linkedin}")
            if github:
                parts.append(f"GitHub: {github}")
            if parts:
                contact_lines.append(" | ".join(parts))
    else:
        # Pretty: compact contact info into one wrapped line.
        parts = [p for p in [location, phone, email, website, linkedin, github] if p]
        if parts:
            contact_lines = _wrap_text(
                c,
                "  |  ".join(parts),
                max_width=content_w,
                font_name="Helvetica",
                font_size=9,
            )

    if contact_lines:
        # Each `contact_lines` entry may still be long, so we wrap again.
        for line in contact_lines:
            for wrapped in _wrap_text(c, line, max_width=content_w, font_name="Helvetica", font_size=9):
                c.drawString(x, y, wrapped)
                y -= 11
        y -= 6

    if style == "pretty" and (name or title or contact_lines):
        _draw_rule(c, x, y, content_w)
        y -= 18
    else:
        y -= 12

    return y


def _draw_summary_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Summary section if `summary` is present."""
    # A resume can be valid without a summary; skip it entirely if empty.
    summary = _clean_str(data.summary)
    if not summary:
        return y

    y = _draw_section_title(c, "Summary", x, y, content_w, style=style)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#222222"))
    # Summary is treated as one paragraph and wrapped across multiple lines.
    for line in _wrap_text(c, summary, max_width=content_w, font_name="Helvetica", font_size=10):
        c.drawString(x, y, line)
        y -= 13
    y -= 6
    return y


def _draw_skills_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Skills section if at least one skill is present."""
    # Skills are treated as a simple list of strings to keep the JSON schema easy.
    skills = [s.strip() for s in data.skills if str(s).strip()]
    if not skills:
        return y

    y = _draw_section_title(c, "Skills", x, y, content_w, style=style)
    y = _draw_tag_row(c, skills, x, y, content_w)
    y -= 6
    return y


def _draw_experience_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Experience section if at least one entry has content."""
    # We pre-filter items so partially empty entries don't produce blank headers.
    items = []
    for company, role, dates, bullets in data.experience:
        company_s = _clean_str(company)
        role_s = _clean_str(role)
        dates_s = _clean_str(dates)
        bullets_s = [b.strip() for b in bullets if str(b).strip()]
        if company_s or role_s or dates_s or bullets_s:
            items.append((company_s, role_s, dates_s, bullets_s))

    if not items:
        return y

    y = _draw_section_title(c, "Experience", x, y, content_w, style=style)
    for company, role, dates, bullets in items:
        c.setFillColor(colors.HexColor("#222222"))
        c.setFont("Helvetica-Bold", 11)

        if style == "ats":
            # ATS: avoid right-aligned date columns.
            left = " - ".join([p for p in [company, role] if p])
            if dates:
                left = f"{left} ({dates})" if left else f"({dates})"
            if left:
                c.drawString(x, y, left)
        else:
            left = " — ".join([p for p in [company, role] if p])
            if left:
                c.drawString(x, y, left)
            if dates:
                c.setFont("Helvetica", 10)
                c.setFillColor(colors.HexColor("#555555"))
                # `drawRightString` aligns the text so its *right edge* is at this x.
                c.drawRightString(x + content_w, y, dates)

        y -= 14
        bullet_char = "-" if style == "ats" else "•"
        y = _draw_bullets(c, bullets, x, y, content_w, bullet_char=bullet_char)
        y -= 6
    return y


def _draw_projects_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Projects section if at least one entry has content."""
    items = []
    for name, meta, bullets in data.projects:
        name_s = _clean_str(name)
        meta_s = _clean_str(meta)
        bullets_s = [b.strip() for b in bullets if str(b).strip()]
        if name_s or meta_s or bullets_s:
            items.append((name_s, meta_s, bullets_s))

    if not items:
        return y

    y = _draw_section_title(c, "Projects", x, y, content_w, style=style)
    for name, meta, bullets in items:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#222222"))

        if style == "ats":
            # ATS: keep project header as a single left-aligned line.
            header = name
            if meta:
                header = f"{name} ({meta})" if name else meta
            if header:
                c.drawString(x, y, header)
        else:
            if name:
                c.drawString(x, y, name)
            if meta:
                c.setFont("Helvetica", 10)
                c.setFillColor(colors.HexColor("#555555"))
                c.drawRightString(x + content_w, y, meta)

        y -= 14
        bullet_char = "-" if style == "ats" else "•"
        y = _draw_bullets(c, bullets, x, y, content_w, bullet_char=bullet_char)
        y -= 6
    return y


def _draw_education_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Education section if at least one entry has content."""
    items = []
    for degree, school, dates in data.education:
        degree_s = _clean_str(degree)
        school_s = _clean_str(school)
        dates_s = _clean_str(dates)
        if degree_s or school_s or dates_s:
            items.append((degree_s, school_s, dates_s))

    if not items:
        return y

    y = _draw_section_title(c, "Education", x, y, content_w, style=style)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#222222"))
    for degree, school, dates in items:
        if style == "ats":
            # ATS: keep dates inline to avoid multi-column extraction issues.
            left = " - ".join([p for p in [degree, school] if p])
            if dates:
                left = f"{left} ({dates})" if left else f"({dates})"
            if left:
                c.drawString(x, y, left)
        else:
            left = " — ".join([p for p in [degree, school] if p])
            if left:
                c.drawString(x, y, left)
            if dates:
                c.setFillColor(colors.HexColor("#555555"))
                c.drawRightString(x + content_w, y, dates)
                c.setFillColor(colors.HexColor("#222222"))
        y -= 13
    y -= 6
    return y


def _draw_certifications_section(
    c: Canvas,
    data: ResumeData,
    *,
    x: float,
    y: float,
    content_w: float,
    style: Style,
) -> float:
    """Render the Certifications section if at least one certification is present."""
    certs = [c_.strip() for c_ in data.certifications if str(c_).strip()]
    if not certs:
        return y

    y = _draw_section_title(c, "Certifications", x, y, content_w, style=style)
    bullet_char = "-" if style == "ats" else "•"
    y = _draw_bullets(c, certs, x, y, content_w, bullet_char=bullet_char)
    return y


def generate_pdf(output_path: str, data: ResumeData, *, style: Style = "ats") -> None:
    """Generate a one-page resume PDF.

    This generator intentionally does *not* paginate; if content runs off the page,
    it will be clipped. The intended usage is a one-page resume.
    """
    _register_fonts()

    page_w, page_h = LETTER
    # `inch` is a convenience constant from ReportLab: 1 * inch == 72 points.
    margin = 0.65 * inch
    content_w = page_w - 2 * margin

    c = Canvas(output_path, pagesize=LETTER)
    # `setTitle` sets PDF metadata (what you see in some PDF viewers).
    c.setTitle(f"Resume - {data.name}")

    x = margin
    y = page_h - margin  # start from the top margin and move downward

    # Render top-to-bottom; each section returns the next y position.
    # If a section has no content, it returns the original y unchanged.
    y = _draw_header(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_summary_section(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_skills_section(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_education_section(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_certifications_section(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_experience_section(c, data, x=x, y=y, content_w=content_w, style=style)
    y = _draw_projects_section(c, data, x=x, y=y, content_w=content_w, style=style)

    # Footer timestamp (subtle). Remove if you prefer a "static" resume file.
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawRightString(x + content_w, margin * 0.6, f"Generated {date.today().isoformat()}")

    c.showPage()
    # `save()` finalizes the PDF file.
    c.save()


def main() -> None:
    """CLI entrypoint."""
    # `argparse` turns command-line flags into Python variables.
    parser = argparse.ArgumentParser(description="Generate a one-page PDF resume.")
    parser.add_argument(
        "--output",
        default="resume_output.pdf",
        help="Output PDF path (default: resume_output.pdf)",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to a JSON file with resume fields.",
    )
    parser.add_argument(
        "--style",
        choices=["ats", "pretty"],
        default="ats",
        help="Layout style. 'ats' favors predictable text extraction; 'pretty' uses more visual alignment.",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    # `Path` is a nicer way to work with file paths than raw strings.
    if not data_path.exists():
        raise FileNotFoundError(
            f"Resume JSON not found: {data_path}. Provide --data <file.json>."
        )

    # Read and parse JSON as UTF-8 so non-ASCII characters (e.g., en-dashes) work.
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    # We expect the JSON file to look like `{ "name": "...", "skills": [...], ... }`.
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    data = _resume_from_mapping(payload)

    generate_pdf(str(args.output), data, style=args.style)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
