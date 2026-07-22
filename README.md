# Resume Tailor

ATS-optimized resume rewriting powered by Claude AI — upload a PDF, paste a job description, get a tailored resume back.

<!-- Screenshot: Add a screenshot of the UI here -->

## Features

- **AI-Powered Rewriting** — Claude rewrites your resume to match job description keywords without fabricating experience
- **Keyword Match Scoring** — Regex-based extraction of 150+ tech skills, tools, and phrases with real match percentage
- **Adaptive PDF Generation** — Two-phase algorithm (binary search + greedy expansion) targets exactly 2 pages
- **European CV Template** — Two-column A4 layout with optional photo, sidebar for skills/certs, main area for experience
- **Automatic Refinement** — If keyword coverage falls below 85%, a second Claude pass incorporates missing terms
- **Inline Editing** — Adjust bullets, skills, summary, and certifications in-browser, then regenerate the PDF without another API call
- **Optional Photo Support** — Upload a headshot for European-style CVs

## How It Works

1. **Upload** — Drop a PDF resume and paste the target job description (50+ chars)
2. **Rewrite** — Claude analyzes both inputs and produces a structured JSON resume optimized for ATS
3. **Generate** — WeasyPrint renders a styled 2-page PDF with adaptive font sizing
4. **Score** — Keywords from the JD are matched against the output; if below 85%, Claude refines automatically
5. **Edit & Download** — Review keyword coverage, tweak content inline, regenerate, and download

## Setup on macOS

Everything below assumes a fresh Mac. Total setup time: ~5 minutes.

### 1. Install Homebrew (skip if you already have it)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install system dependencies

WeasyPrint needs these C libraries to render PDFs:

```bash
brew install python@3.11 pango cairo gdk-pixbuf libffi
```

### 3. Clone and set up the project

```bash
git clone https://github.com/ShubhamArora073/resume-tailor.git
cd resume-tailor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure your API key

```bash
cp .env.example .env
```

Open `.env` in any editor and set your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

You can get a key at [console.anthropic.com](https://console.anthropic.com).

### 5. Run the server

```bash
source venv/bin/activate   # if not already activated
python main.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser. That's it.

### Stopping the server

Press `Ctrl+C` in the terminal.

### Running it again later

```bash
cd resume-tailor
source venv/bin/activate
python main.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `AI_GATEWAY_URL` | No | Custom AI gateway URL (proxy) |
| `AI_GATEWAY_KEY` | No | API key for custom gateway |
| `AI_GATEWAY_USER` | No | User email for gateway auth |

## Usage

1. Drag and drop your current resume (PDF, max 5 MB)
2. Optionally upload a profile photo
3. Paste the full job description into the text area
4. Click **Tailor My Resume** and wait 30-60 seconds
5. Review the keyword match score and coverage tags
6. Edit any section inline if needed, then click **Regenerate PDF**
7. Download the tailored resume

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| AI | Claude (claude-sonnet-4-20250514) via Anthropic SDK |
| PDF Extraction | PyMuPDF |
| PDF Generation | WeasyPrint + Jinja2 |
| Frontend | Vanilla HTML/CSS/JS (no framework, no build step) |
| HTTP Client | httpx (async, mTLS-capable) |

## Running Tests

```bash
source venv/bin/activate
pytest
```

Test coverage includes API validation, the full `/tailor` pipeline (mocked), keyword extraction, match scoring, Claude prompt construction and response parsing, and PDF generation.

## License

MIT
