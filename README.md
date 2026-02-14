# PDF Resume Generator 

This repository generates a clean, one-page PDF resume from structured data.

## Overview

This is a small Python + ReportLab tool that turns a resume JSON file into a print-ready, one-page PDF.

- Windows executable: `resume-generator.exe`
- Python script: `resume_generator.py`
- Example input / template JSON: `sample_input.json`

### ATS-friendly output

ATS = **Applicant Tracking System** (software used by companies/recruiters to parse, search, and filter resumes). The generator aims for ATS-friendlier output.

The layout is designed to be optimized for automated systems to extract:

- Single-column, top-to-bottom flow
- Deterministic, predictable formatting for consistent parsing
- Left-aligned dates (no right-aligned columns)
- ASCII bullets (`-`) instead of Unicode bullets
- Labeled contact lines (e.g., `Email: ...`) to reduce ambiguity

Note: no PDF format can guarantee perfect parsing across every ATS. These choices are generally safer than heavily visual or multi-column layouts.

## Run the Windows `.exe` (no Python)

If you have a packaged executable (for example `resume-generator.exe`), you can run it from PowerShell.

1. Put these files in the same folder:
  - `resume-generator.exe`
  - `sample_input.json` (edit it to match your resume)
2. Open PowerShell in that folder.
3. Run:

```powershell
.\resume-generator.exe --data .\sample_input.json --output .\resume_output.pdf
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

If a field/section is missing or empty, it will be skipped (not rendered) in the PDF.

## How it works

- `resume_generator.py` loads the JSON file you pass via `--data` and builds a `ResumeData` object.
- The script uses ReportLab’s `Canvas` to draw text and section dividers onto a letter-sized page.
- It wraps long lines so content fits within the margins.
- It saves a single-page PDF.

## Generate a PDF

Run with your own input/output filenames:

```powershell
python resume_generator.py --data <your_resume.json> --output <your_resume.pdf>
```

Example (using the included sample input):

```powershell
python resume_generator.py --data sample_input.json --output resume_output.pdf
```

Optional: generate a more visually aligned version (for comparison):

```powershell
python resume_generator.py --data sample_input.json --style pretty --output resume_sample_pretty.pdf
```

This writes `resume_output.pdf` (or your chosen `--output`) to the repository root.

## CLI options

- `--output <path>`: output PDF path (default: `resume_output.pdf`)
- `--data <path>`: JSON file with resume content (required)
- `--style <ats|pretty>`: layout style (default: `ats`).

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

## Build a Windows executable (no Python required)

From the repo root (with your venv activated):

```powershell
pip install pyinstaller
pyinstaller --onefile --name resume-generator resume_generator.py
```

The executable will be created at:

- `resume-generator.exe`

Run it like this (you still pass a JSON file as input):

```powershell
.\resume-generator.exe --data sample_input.json --output resume_output.pdf
```

## Troubleshooting

- **`pip` or `python` not recognized**: Python is not on PATH. Reinstall Python and select “Add to PATH”.
- **Activation blocked**: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then re-activate.
- **PDF not updating**: ensure you are running from the repository root and opening the newest output file.

## Notes

- Page size is US Letter.
- Fonts default to built-in PDF fonts (Helvetica). The script includes a best-effort attempt to use Inter if `Inter-Regular.ttf` and `Inter-Bold.ttf` are present, but it works without them.
