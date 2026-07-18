# Ghost AutoVacancy Poster

A production-ready pipeline for automatically extracting, validating, enriching, and packaging job vacancies received via WhatsApp into a READY_TO_PUBLISH package. This repository provides the Ghost SDK and supporting utilities to turn raw messages into platform-ready posters and captions for multi-platform publishing.

---

## Features

- Automatic vacancy extraction
- Validation pipeline
- Duplicate detection
- Poster generation
- Multi-platform caption generation
- Translation
- Queue package generation
- Ghost SDK integration

---

## Architecture

```text
WhatsApp
    │
    ▼
Text Cleaner
    │
    ▼
Vacancy Extractor
    │
    ▼
Validator
    │
    ▼
Duplicate Detector
    │
    ▼
Database
    │
    ▼
Poster Generator
    │
    ▼
Caption Generator
    │
    ▼
READY_TO_PUBLISH Package
```

---

## Pipeline Flow

1. Detect new WhatsApp vacancy
2. Clean raw text
3. Extract structured vacancy
4. Validate extraction
5. Check duplicate
6. Save to database
7. Generate poster
8. Generate captions
9. Generate READY_TO_PUBLISH package

---

## Queue Output

The pipeline emits READY_TO_PUBLISH packages into the queue under `queue/ready/`. Each package is a compact JSON payload that contains the extracted vacancy metadata and references to generated assets ready for final publishing.

Directory layout:

queue/
    ready/

Example JSON payload:

```json
{
  "vacancy_id": "...",
  "company": "...",
  "position": "...",
  "poster": "...",
  "caption": "...",
  "status": "READY_TO_PUBLISH"
}
```

This READY_TO_PUBLISH package is intended to be consumed by the Ghost AutoPost Agent. The AutoPost Agent watches `queue/ready/`, downloads the package, performs any platform-specific media uploads and API calls, schedules or publishes the post to target platforms, and updates publish status.

---

## Ghost SDK APIs

Public SDK functions exposed for integration and automation:

- extractVacancy()
- validateVacancy()
- generateCaption()
- checkDuplicate()
- createPoster()
- publish()
- summarizeVacancy()
- translateVacancy()

Each API is composable and may be used independently or chained into custom pipelines. Refer to the SDK docstrings and examples in `examples/` for usage details and parameter contracts.

---

## Project Structure

A brief overview of important folders:

- src/ - Core pipeline implementation and the Ghost SDK modules
- docs/ - Extended documentation, design notes, and API references
- tests/ - Unit and integration tests
- queue/ - Local queue emulation and READY_TO_PUBLISH packages used during development
- assets/ - Templates, fonts, images and other static resources used by poster generation
- examples/ - Example inputs and usage snippets
- config/ - Configuration templates and examples

---

## Running

Installation

1. Create and activate a Python virtual environment (recommended):

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate    # Windows (PowerShell)

2. Install dependencies:

   pip install -r requirements.txt

Commands

- Run the end-to-end pipeline:

  python main.py --pipeline -i vacancies/

- Typical development commands:

  - Parse a single file: `python main.py --input vacancies/job_posting.txt`
  - Dry run: `python main.py --input vacancies/ --dry-run`
  - Skip publishing: `python main.py --input vacancies/ --no-publish`

Pipeline execution

Use the `--pipeline` flag to run the full pipeline from ingestion through READY_TO_PUBLISH package generation. For testing or development you can call the SDK functions directly to execute specific stages (extract, validate, poster, etc.).

Example:

python main.py --pipeline -i vacancies/

---

## Testing

- 365 tests passing
- Zero regressions

Run the test suite locally with:

pytest -q

Automated tests cover extraction, validation, duplicate detection, poster generation, and caption generation.

---

## Roadmap

Current status:

- ✅ SDK
- ✅ Extraction
- ✅ Validation
- ✅ Duplicate Detection
- ✅ Poster Generation
- ✅ Caption Generation
- ✅ READY_TO_PUBLISH

Next project:

- Ghost AutoPost Agent

---

## Screenshots

Add screenshots to help new users and contributors quickly see the dashboard and generated posters. Below are recommended filenames, alt text, and placement instructions — I can add the image files for you if you upload them or confirm I should use the images you attached in this conversation.

Recommended location in the repository:

- docs/screenshots/

Recommended filenames (you uploaded four images; please confirm or provide different names):

- docs/screenshots/1_poster_full_mobile.png  — Poster full view (mobile)
- docs/screenshots/2_poster_card_mobile.png  — Poster card view (mobile)
- docs/screenshots/3_terminal_output.png     — Test & terminal output (CI / pytest)
- docs/screenshots/4_dashboard_duplicate.png — Dashboard view (duplicate flagged)

To embed screenshots in the README use the following markdown (example):

```markdown
## Screenshots

Poster (full view)

![Poster - full view](docs/screenshots/1_poster_full_mobile.png)

Poster (card)

![Poster - card](docs/screenshots/2_poster_card_mobile.png)

Test output / terminal

![Terminal tests](docs/screenshots/3_terminal_output.png)

Dashboard (duplicate detection)

![Dashboard duplicate](docs/screenshots/4_dashboard_duplicate.png)
```

If you'd like smaller thumbnails with captions, you can use HTML in the README for finer control. Example:

```html
<p align="center">
  <img src="docs/screenshots/1_poster_full_mobile.png" width="360" alt="Poster full view" />
  <img src="docs/screenshots/2_poster_card_mobile.png" width="240" alt="Poster card" />
</p>
```

How I can proceed for you (choose one):

1. I will add the screenshots you attached here into `docs/screenshots/` and commit them, then embed them in the README exactly as shown above. (I'll need your confirmation — and permission to read and add the images attached in this conversation.)

2. I will only update the README to include the screenshot section and instructions (already done). You will add the image files yourself by committing them to `docs/screenshots/` using the recommended filenames and markdown.

3. I will create a pull request that adds both images and the README update if you provide the image files (upload or paste), and you prefer a PR flow.

Tell me which option you want. If you choose option 1 or 3, please confirm and I'll add the images now (I will use the four images you attached in this chat as the source). If you prefer to upload different image files, provide them or tell me the filenames to use.

---

Version: v1.0.0-beta

Production-ready pipeline for autonomous vacancy processing.
