# PDF Resume Generator (Sample)

This repo generates a clean, one-page PDF resume from structured data.

## Why use this instead of a template editor?

Generating your resume via code can be a practical advantage when you care about consistency and automated parsing:

- **Consistent formatting:** the PDF layout is deterministic (update content → regenerate → same spacing/margins every time).
- **Machine-readable text layer:** the output is drawn as real text (not a screenshot), which is typically easier for ATS/HR systems to extract.
- **ATS-friendly option:** `--style ats` avoids common parsing pitfalls like multi-column alignment and right-justified date columns.

This can improve extractability, but it can’t guarantee passing filters or getting interviews—content relevance still matters.

- Primary script: `generate_resume_pdf.py`
- Dependency list: `requirements.txt`
- Editable sample data: `resume_sample.json`
- Output: `resume_sample.pdf` (or whatever you pass via `--output`)

## What it is

A small Python + ReportLab tool that programmatically lays out a resume (header, summary, skills, experience, projects, education, certifications) and writes a print-ready PDF.

This approach is useful when you want repeatable formatting and easy regeneration (e.g., tweak content → rerun → get a consistent PDF).

## How it works (high level)

- `generate_resume_pdf.py` builds a `ResumeData` object.
  - If you don’t pass `--data`, it uses built-in sample values.
  - If you pass `--data some.json`, it loads JSON and fills missing fields with sample defaults.
- The script uses ReportLab’s `Canvas` to draw text and section dividers onto a letter-sized page.
- It wraps long lines so content fits within the margins.
- It saves a single-page PDF.

### ATS-friendly output

The default `--style ats` layout is designed to be easier for automated systems to extract:

- Single-column, top-to-bottom flow
- Left-aligned dates (no right-aligned columns)
- ASCII bullets (`-`) instead of Unicode bullets
- Labeled contact lines (e.g., `Email: ...`) to reduce ambiguity

Note: no PDF format can guarantee perfect parsing across every ATS, but these choices tend to be safer than heavily visual layouts.

## Quick start (Windows)

### 1) Install Python on Windows

1. Download and install Python 3.10+ from https://www.python.org/downloads/
2. During install, check **“Add python.exe to PATH”**.
3. Verify in PowerShell:

```powershell
python --version
pip --version
```

If `python` isn’t found, re-run the installer and enable PATH, or use the “App execution aliases” settings in Windows to disable the Microsoft Store alias for Python.

### 2) Create and activate a virtual environment

From the repo folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Generate a PDF

Use built-in sample data:

```powershell
python generate_resume_pdf.py
```

This writes `resume_sample.pdf` in the repo directory.

## Using your own (still sample) values

Edit `resume_sample.json` (it’s already filled with placeholder/sample content), then run:

```powershell
python generate_resume_pdf.py --data resume_sample.json --output resume_from_json.pdf
```

## CLI options

- `--output <path>`: output PDF path (default: `resume_sample.pdf`)
- `--data <path>`: optional JSON file with resume content
- `--style ats|pretty`: layout style (default: `ats`)

Example:

```powershell
python generate_resume_pdf.py --data resume_sample.json --output Daniel_Resume.pdf --style ats
```

## JSON format

The JSON file is expected to be an object with these keys (all optional):

- `name`, `title`, `location`, `phone`, `email`, `website`, `linkedin`, `github` (strings)
- `summary` (string)
- `skills` (array of strings)
- `experience` (array of objects: `{ company, role, dates, bullets[] }`)
- `projects` (array of objects: `{ name, meta, bullets[] }`)
- `education` (array of objects: `{ degree, school, dates }`)
- `certifications` (array of strings)

If a section is missing or empty, the script falls back to built-in sample values for that section.

## Troubleshooting

- **`pip` or `python` not recognized**: Python isn’t on PATH. Reinstall Python and check “Add to PATH”.
- **Activation blocked**: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then re-activate.
- **PDF not updating**: ensure you’re running in the repo folder and opening the newest output file.

## Notes

- Page size is US Letter.
- Fonts default to built-in PDF fonts (Helvetica). The script includes a best-effort attempt to use Inter if `Inter-Regular.ttf` and `Inter-Bold.ttf` are present, but it works without them.
