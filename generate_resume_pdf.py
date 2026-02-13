from __future__ import annotations

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


@dataclass(frozen=True)
class ResumeData:
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

    experience: List[Tuple[str, str, str, List[str]]]
    projects: List[Tuple[str, str, List[str]]]
    education: List[Tuple[str, str, str]]
    certifications: List[str]


def _resume_from_mapping(payload: dict[str, Any]) -> ResumeData:
    return ResumeData(
        name=str(payload.get("name", "")),
        title=str(payload.get("title", "")),
        location=str(payload.get("location", "")),
        phone=str(payload.get("phone", "")),
        email=str(payload.get("email", "")),
        website=str(payload.get("website", "")),
        linkedin=str(payload.get("linkedin", "")),
        github=str(payload.get("github", "")),
        summary=str(payload.get("summary", "")),
        skills=list(payload.get("skills", [])),
        experience=[
            (
                str(item.get("company", "")),
                str(item.get("role", "")),
                str(item.get("dates", "")),
                list(item.get("bullets", [])),
            )
            for item in payload.get("experience", [])
        ],
        projects=[
            (
                str(item.get("name", "")),
                str(item.get("meta", "")),
                list(item.get("bullets", [])),
            )
            for item in payload.get("projects", [])
        ],
        education=[
            (
                str(item.get("degree", "")),
                str(item.get("school", "")),
                str(item.get("dates", "")),
            )
            for item in payload.get("education", [])
        ],
        certifications=list(payload.get("certifications", [])),
    )


def _register_fonts() -> None:
    """Try to register nicer fonts if available; fall back to built-ins."""
    # Keep this conservative so it works on most machines.
    # If these TTFs aren't present, ReportLab will just use Helvetica.
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
    words = text.split()
    lines: List[str] = []
    current: List[str] = []

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
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(colors.HexColor("#222222"))

    # ATS mode favors simple text flow over decorative elements.
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
    bullet_indent = 10
    text_indent = 22

    canvas.setFillColor(colors.HexColor("#222222"))
    for b in bullets:
        wrapped = _wrap_text(canvas, b, max_width=w - text_indent, font_name=font_name, font_size=font_size)
        if not wrapped:
            continue

        # bullet
        canvas.setFont(font_name, font_size)
        canvas.drawString(x + bullet_indent, y, bullet_char)

        # first line
        canvas.drawString(x + text_indent, y, wrapped[0])
        y -= leading

        # remaining lines (no bullet)
        for line in wrapped[1:]:
            canvas.drawString(x + text_indent, y, line)
            y -= leading

    return y


def _draw_tag_row(canvas: Canvas, tags: List[str], x: float, y: float, w: float) -> float:
    """Draws a compact comma-separated skills row, wrapped."""
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(colors.HexColor("#222222"))

    line = ""
    for i, tag in enumerate(tags):
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


def generate_pdf(output_path: str, data: ResumeData, *, style: Style = "ats") -> None:
    _register_fonts()

    page_w, page_h = LETTER
    margin = 0.65 * inch
    content_w = page_w - 2 * margin

    c = Canvas(output_path, pagesize=LETTER)
    c.setTitle(f"Resume - {data.name}")

    x = margin
    y = page_h - margin

    # Header
    c.setFillColor(colors.HexColor("#111111"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x, y, data.name)

    y -= 18
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(x, y, data.title)

    # Contact info
    y -= 16
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#444444"))
    if style == "ats":
        # ATS mode: prefer predictable, labeled lines.
        contact_lines = [
            f"Location: {data.location}",
            f"Phone: {data.phone} | Email: {data.email}",
            f"Website: {data.website} | LinkedIn: {data.linkedin} | GitHub: {data.github}",
        ]
    else:
        contact = (
            f"{data.location}  |  {data.phone}  |  {data.email}  |  {data.website}  |  {data.linkedin}  |  {data.github}"
        )
        contact_lines = _wrap_text(c, contact, max_width=content_w, font_name="Helvetica", font_size=9)

    for line in contact_lines:
        for wrapped in _wrap_text(c, line, max_width=content_w, font_name="Helvetica", font_size=9):
            c.drawString(x, y, wrapped)
            y -= 11

    y -= 6
    if style == "pretty":
        _draw_rule(c, x, y, content_w)
        y -= 18
    else:
        y -= 12

    # Summary
    y = _draw_section_title(c, "Summary", x, y, content_w, style=style)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#222222"))
    for line in _wrap_text(c, data.summary, max_width=content_w, font_name="Helvetica", font_size=10):
        c.drawString(x, y, line)
        y -= 13
    y -= 6

    # Skills
    y = _draw_section_title(c, "Skills", x, y, content_w, style=style)
    y = _draw_tag_row(c, data.skills, x, y, content_w)
    y -= 6

    # Experience
    y = _draw_section_title(c, "Experience", x, y, content_w, style=style)
    for company, role, dates, bullets in data.experience:
        c.setFillColor(colors.HexColor("#222222"))
        c.setFont("Helvetica-Bold", 11)
        if style == "ats":
            c.drawString(x, y, f"{company} - {role} ({dates})")
        else:
            c.drawString(x, y, f"{company} — {role}")

            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawRightString(x + content_w, y, dates)
        y -= 14

        bullet_char = "-" if style == "ats" else "•"
        y = _draw_bullets(c, bullets, x, y, content_w, bullet_char=bullet_char)
        y -= 6

    # Projects
    y = _draw_section_title(c, "Projects", x, y, content_w, style=style)
    for name, meta, bullets in data.projects:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#222222"))
        if style == "ats":
            # Keep one left-aligned line to preserve reading order.
            c.drawString(x, y, f"{name} ({meta})" if meta else name)
        else:
            c.drawString(x, y, name)

            c.setFont("Helvetica", 10)
            c.setFillColor(colors.HexColor("#555555"))
            c.drawRightString(x + content_w, y, meta)
        y -= 14

        bullet_char = "-" if style == "ats" else "•"
        y = _draw_bullets(c, bullets, x, y, content_w, bullet_char=bullet_char)
        y -= 6

    # Education
    y = _draw_section_title(c, "Education", x, y, content_w, style=style)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#222222"))
    for degree, school, dates in data.education:
        if style == "ats":
            c.drawString(x, y, f"{degree} - {school} ({dates})")
        else:
            c.drawString(x, y, f"{degree} — {school}")
            c.setFillColor(colors.HexColor("#555555"))
            c.drawRightString(x + content_w, y, dates)
            c.setFillColor(colors.HexColor("#222222"))
        y -= 13

    y -= 6

    # Certifications
    y = _draw_section_title(c, "Certifications", x, y, content_w, style=style)
    bullet_char = "-" if style == "ats" else "•"
    y = _draw_bullets(c, data.certifications, x, y, content_w, bullet_char=bullet_char)

    # Footer timestamp (subtle)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawRightString(x + content_w, margin * 0.6, f"Generated {date.today().isoformat()}")

    c.showPage()
    c.save()


def main() -> None:
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
    if not data_path.exists():
        raise FileNotFoundError(
            f"Resume JSON not found: {data_path}. Provide --data <file.json>."
        )

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    data = _resume_from_mapping(payload)

    generate_pdf(str(args.output), data, style=args.style)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
