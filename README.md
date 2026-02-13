# PDF Resume Generator (Sample)

This repository generates a clean, one-page PDF resume from structured data.

## Rationale

Generating a resume via code can be useful when you care about deterministic formatting and automated text extraction:

- **Consistent formatting:** the PDF layout is deterministic (update content → regenerate → same spacing/margins every time).
- **Machine-readable text layer:** the output is drawn as real text (not a screenshot), which is typically easier for ATS/HR systems to extract.
- **ATS-friendly option:** `--style ats` avoids common parsing pitfalls like multi-column alignment and right-justified date columns.

This can improve extractability, but it does not guarantee screening outcomes; content relevance still matters.

- Primary script: `generate_resume_pdf.py`
- Dependency list: `requirements.txt`
- Resume input data: `sample_input.json` (passed via `--data`)
- Output (default): `resume_output.pdf` (or whatever you pass via `--output`)

## What it is

A small Python + ReportLab tool that programmatically lays out a resume (header, summary, skills, experience, projects, education, certifications) and writes a print-ready PDF.

This approach is useful when you want repeatable formatting and easy regeneration (e.g., tweak content → rerun → get a consistent PDF).

## How it works (high level)

- `generate_resume_pdf.py` loads `sample_input.json` (or the file you pass via `--data`) and builds a `ResumeData` object.
- The script uses ReportLab’s `Canvas` to draw text and section dividers onto a letter-sized page.
- It wraps long lines so content fits within the margins.
- It saves a single-page PDF.

### ATS-friendly output

The default `--style ats` layout is designed to be easier for automated systems to extract:

- Single-column, top-to-bottom flow
- Left-aligned dates (no right-aligned columns)
- ASCII bullets (`-`) instead of Unicode bullets
- Labeled contact lines (e.g., `Email: ...`) to reduce ambiguity

Note: no PDF format can guarantee perfect parsing across every ATS. These choices are generally safer than heavily visual or multi-column layouts.

## Generate a PDF

Run with your own input/output filenames:

```powershell
python generate_resume_pdf.py --data <your_resume.json> --output <your_resume.pdf>
```

Example (using the included sample input):

```powershell
python generate_resume_pdf.py --data sample_input.json --output resume_output.pdf
```

Optional: generate a more visually aligned version (for comparison):

```powershell
python generate_resume_pdf.py --data sample_input.json --style pretty --output resume_sample_pretty.pdf
```

This writes `resume_output.pdf` (or your chosen `--output`) to the repository root.

## CLI options

- `--output <path>`: output PDF path (default: `resume_output.pdf`)
- `--data <path>`: JSON file with resume content (required)
- `--style <ats|pretty>`: layout style (default: `ats`).

Example:

```powershell
python generate_resume_pdf.py --data sample_input.json --output sample_resume.pdf --style ats
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

If a section is missing or empty, it will simply render as empty in the PDF.

## Setup (Windows)

### 1) Install Python

1. Download and install Python 3.10+ from https://www.python.org/downloads/
2. During install, check **“Add python.exe to PATH”**.
3. Verify in PowerShell:

```powershell
python --version
pip --version
```

If `python` isn’t found, re-run the installer and enable PATH. You may also need to disable the Microsoft Store “App execution alias” for Python in Windows settings.

### 2) Create and activate a virtual environment

From the repository root:

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Troubleshooting

- **`pip` or `python` not recognized**: Python is not on PATH. Reinstall Python and select “Add to PATH”.
- **Activation blocked**: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then re-activate.
- **PDF not updating**: ensure you are running from the repository root and opening the newest output file.

## Notes

- Page size is US Letter.
- Fonts default to built-in PDF fonts (Helvetica). The script includes a best-effort attempt to use Inter if `Inter-Regular.ttf` and `Inter-Bold.ttf` are present, but it works without them.
