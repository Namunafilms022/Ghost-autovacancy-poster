# 👻 Ghost AutoVacancy Poster

AI-powered pipeline for extracting job vacancies from WhatsApp messages, generating posters + captions, and auto-publishing to social media.

```
Message → Extract → Validate → Poster → Caption → Queue → Rule Match → Auto-Publish
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py --dashboard
```

Open `http://localhost:5000`

## Commands

| Command | Description |
|---------|-------------|
| `python main.py --dashboard` | Web UI (port 5000) |
| `python main.py --api` | REST API (port 8000, FastAPI + `/docs`) |
| `python main.py --worker` | Background auto-publisher |
| `python main.py --pipeline --input msg.txt` | Run full pipeline on file |
| `python main.py --input . --no-publish` | Parse & save only |

## Pipeline Flow

```
WhatsApp Message
  ↓ [extractVacancy] — parse title, company, salary, location, etc.
  ↓ [validateVacancy] — advisory confidence check
  ↓ [DuplicateDetector] — 7-field weighted comparison
  ↓ [VacancyParser → DB] — save to SQLite
  ↓ [PosterGenerator] — HTML poster with 4-layer rendering
  ↓ [generateCaptions] — per-platform caption (FB/LinkedIn/IG/Twitter/TG)
  ↓ [enqueue] → QueueItem in DB
  ↓ [AutomationRule] — immediate or scheduled
  ↓ [Worker] — polls queue → auto-publishes
```

## API (FastAPI)

```bash
python main.py --api
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Hiring Software Engineer at Google, Bangalore, 15LPA"}'
```

Interactive docs: `http://localhost:8000/docs`

## Dashboard Pages

- `/` — Vacancy cards with filters
- `/editor/<id>` — Live poster editor
- `/queue` — Queue management + worker controls
- `/social` — Social accounts (FB/LinkedIn/IG/Twitter/TG)
- `/automation` — Rules engine (immediate/scheduled/conditions)
- `/analytics` — Publishing stats & platform health

## Supported Platforms

| Platform | Status |
|----------|--------|
| Facebook | ✅ Working (groups via FacebookPublisher) |
| LinkedIn | 🔧 Stub |
| Instagram | 🔧 Stub |
| Twitter/X | 🔧 Stub |
| Telegram | 🔧 Stub |

## Project Structure

```
├── main.py                  # CLI entry point
├── api_server.py            # FastAPI webhook server
├── ghost_module/            # Core SDK (10 APIs)
│   ├── pipeline.py          # End-to-end pipeline
│   ├── publish_manager.py   # Platform dispatcher + retry logic
│   ├── queue_service.py     # Queue CRUD
│   ├── social_service.py    # Social accounts CRUD
│   ├── automation.py        # Rule engine
│   ├── worker.py            # Background auto-publisher
│   ├── health.py            # Platform health checks
│   ├── analytics.py         # Publish logging + stats
│   ├── summarizer.py        # Summarize vacancy
│   └── translator.py        # Translate (en/ne/hi)
├── dashboard/               # Flask web UI
├── database/                # SQLAlchemy models
├── poster/                  # Poster generator (4-layer HTML/CSS)
├── captions/                # Caption generator (5 platforms)
├── duplicate/               # Duplicate detector
├── publisher/               # Facebook publisher
├── parser/                  # Vacancy parser
├── validator/               # Validation engine
├── tests/                   # 465 tests
└── config/settings.json     # Facebook tokens & poster settings
```

## Configuration

Edit `config/settings.json`:

```json
{
  "facebook": {
    "access_token": "EAA...",
    "group_ids": ["123", "456"],
    "api_version": "v18.0"
  },
  "poster_contact": {
    "replace_phone": "+977-9800000000",
    "replace_email": "hr@company.com",
    "replace_enabled": true
  }
}
```

## Testing

```bash
/usr/bin/python3 -m pytest tests/ -q
```
