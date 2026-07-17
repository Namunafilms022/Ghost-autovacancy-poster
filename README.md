# Ghost-autovacancy-poster

> **Automated job vacancy posting pipeline** — Parse, normalize, detect duplicates, and publish job postings across multiple platforms with a single click.

Ghost-autovacancy-poster is a Python-based automation system that ingests unstructured job vacancy messages, intelligently extracts job details using AI/NLP, standardizes data, identifies duplicates, generates professional HTML posters, and publishes them to multiple platforms (Facebook, Telegram, WhatsApp, etc.).

## 📋 Project Overview & Purpose

Ghost-autovacancy-poster solves the tedious task of manually processing and posting job vacancies. It automates the entire workflow:

- **Ingestion**: Reads vacancy messages from files, webhooks, emails, or APIs
- **Parsing**: Extracts structured job details (title, company, salary, requirements) using Groq AI or regex fallback
- **Normalization**: Standardizes data formats and validates fields
- **Duplicate Detection**: Identifies and flags duplicate job postings
- **Poster Generation**: Creates visually appealing HTML job posters with customizable themes
- **Publishing**: Distributes posters to Facebook, Telegram, WhatsApp, and more

**Target Users**: HR teams, recruitment agencies, job boards, and automated posting services.

---

## 🏗️ Architecture

### Pipeline Flow

```
┌─────────────────┐
│  Message Input  │  (Files, Webhooks, Email, API)
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │ Reader  │  ◄── Load messages from multiple sources
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Parser  │  ◄── Extract job details (AI-powered or regex)
    └────┬────┘
         │
         ▼
    ┌───────────────┐
    │ Normalizer    │  ◄── Standardize data format & validate
    └────┬──────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Duplicate Detector   │  ◄── Identify duplicate postings
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────┐
    │ Poster Generator │  ◄── Create HTML posters with themes
    └────┬─────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Publisher Pipeline   │  ◄── Publish to multiple platforms
    └────┬─────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│    Output (Publishing)          │
│  • Facebook Groups              │
│  • Telegram Channels            │
│  • WhatsApp Broadcast           │
│  • Custom Webhooks              │
└─────────────────────────────────┘
```

### Core Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **Reader** | Ingests vacancy messages from multiple sources | ✅ Phase 1 |
| **Parser** | Extracts structured job details using AI/NLP | ✅ Phase 1 |
| **Normalizer** | Standardizes and validates job data | ✅ Phase 1 |
| **Duplicate** | Identifies and flags duplicate postings | ✅ Phase 1 |
| **Poster** | Generates professional HTML posters | ✅ Phase 2 |
| **Publisher** | Publishes to social media & job boards | ✅ Phase 3 |
| **Database** | Persistent data storage (SQLAlchemy ORM) | ✅ Complete |
| **Dashboard** | Web UI for monitoring & management | ✅ Complete |

---

## ✨ Features

### Message Ingestion
- ✅ **File Reader**: Load vacancy messages from `.txt` files or directories
- ✅ **Webhook Server**: Receive messages via HTTP POST requests
- ✅ **Multi-source Support**: Extensible for email, APIs, and message queues

### Intelligent Parsing
- ✅ **AI-Powered (Groq API)**: Uses LLaMA 3.3 70B for intelligent extraction
- ✅ **Regex Fallback**: Robust pattern matching for structured extraction
- ✅ **Field Extraction**: Job title, company, location, salary, experience level, requirements, benefits, contact info
- ✅ **Salary Parsing**: Handles multiple formats (k, lakh, crore, decimals, currency symbols)

### Data Processing
- ✅ **Normalization**: Clean, validate, and standardize all fields
- ✅ **Duplicate Detection**: Similarity-based duplicate flagging with configurable thresholds
- ✅ **Data Persistence**: SQLite/PostgreSQL support via SQLAlchemy ORM

### Poster Generation
- ✅ **Template System**: Jinja2-based HTML template rendering
- ✅ **Multiple Themes**: `default`, `dark`, `minimal`
- ✅ **Professional Formatting**: Clean, consistent job poster layout
- ✅ **Contact Replacement**: Optionally replace contact details with generic ones

### Publishing
- ✅ **Facebook**: Post to Facebook groups
- ✅ **Telegram**: Notify via Telegram bots (planned)
- ✅ **WhatsApp**: Broadcast to WhatsApp groups (planned)
- ✅ **Platform Extensibility**: Easy to add new publishing targets

### Web Dashboard
- ✅ **Home Overview**: Daily statistics (vacancies, duplicates, published, failed)
- ✅ **Vacancy Listing**: Browse all processed vacancies
- ✅ **Vacancy Details**: View parsed data, poster HTML, publishing status
- ✅ **Duplicate Tracking**: See which vacancies are flagged as duplicates

---

## 🚀 Installation

### Prerequisites

- **Python 3.9+**
- **SQLite** (or PostgreSQL for production)
- **Git**

### Step 1: Clone the Repository

```bash
git clone https://github.com/Namunafilms022/ghost-autovacancy-poster.git
cd ghost-autovacancy-poster
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Settings

Copy the example configuration:

```bash
cp config/settings.example.json config/settings.json
```

Edit `config/settings.json` with your API keys and platform credentials (see [Configuration](#⚙️-configuration) section).

### Step 5: Initialize Database

```bash
python3 -c "from database.init import init_db; init_db()"
```

This creates the SQLite database and tables automatically.

### Step 6: Run the Pipeline

```bash
python3 main.py --input vacancies/
```

---

## ⚙️ Configuration

The system is configured via `config/settings.json`. Here's a breakdown of each section:

### `settings.json` Structure

```json
{
  "app": {
    "name": "Ghost-autovacancy-poster",
    "version": "0.1.0",
    "environment": "development",
    "debug": true,
    "log_level": "INFO"
  },
  "database": {
    "type": "sqlite",
    "path": "./ghost_vacancies.db",
    "echo": false
  },
  "reader": {
    "enabled": true,
    "timeout": 30,
    "max_retries": 3
  },
  "parser": {
    "enabled": true,
    "confidence_threshold": 0.7,
    "groq_api_key": "YOUR_GROQ_API_KEY_HERE"
  },
  "normalizer": {
    "enabled": true,
    "standardize_fields": true,
    "trim_whitespace": true
  },
  "duplicate": {
    "enabled": true,
    "similarity_threshold": 0.85,
    "algorithm": "basic"
  },
  "poster": {
    "enabled": true,
    "template_dir": "poster/templates",
    "output_format": "html",
    "theme": "professional"
  },
  "poster_contact": {
    "replace_enabled": true,
    "replace_phone": "9851001001",
    "replace_email": "ghost@jobposter.com"
  },
  "publisher": {
    "enabled": true,
    "platforms": ["facebook"],
    "max_retries": 3,
    "retry_delay_seconds": 2
  },
  "facebook": {
    "access_token": "",
    "group_ids": [],
    "api_version": "v18.0"
  },
  "telegram_bot": {
    "token": ""
  },
  "whatsapp_bot": {
    "enabled": true,
    "session_path": "./whatsapp_session",
    "webhook_port": 5001,
    "monitored_groups": []
  },
  "logging": {
    "level": "INFO",
    "format": "text",
    "file": "logs/app.log",
    "max_size_mb": 100,
    "backup_count": 5
  },
  "storage": {
    "type": "local",
    "path": "data/"
  }
}
```

### Configuration Reference

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| **app.environment** | string | Run environment (development/production) | `"production"` |
| **app.debug** | boolean | Enable debug logging | `false` |
| **database.type** | string | Database backend (sqlite/postgresql) | `"sqlite"` |
| **database.path** | string | Path to SQLite DB file | `"./ghost_vacancies.db"` |
| **parser.groq_api_key** | string | Groq API key for AI parsing | `"sk-..."` |
| **parser.confidence_threshold** | float | Minimum confidence for parsed fields | `0.7` |
| **duplicate.similarity_threshold** | float | Threshold for duplicate flagging | `0.85` |
| **poster.theme** | string | Poster theme (default/dark/minimal) | `"professional"` |
| **poster_contact.replace_enabled** | boolean | Replace contact details | `true` |
| **facebook.access_token** | string | Facebook API token | `"EAAbcd1234..."` |
| **telegram_bot.token** | string | Telegram bot token | `"123456:ABCdef..."` |

### Getting API Keys

#### Groq API
1. Visit [console.groq.com](https://console.groq.com)
2. Create an account and generate an API key
3. Add to `config/settings.json` under `parser.groq_api_key`

#### Facebook
1. Create a Facebook App at [developers.facebook.com](https://developers.facebook.com)
2. Generate a long-lived access token
3. Find your group ID
4. Add to `config/settings.json` under `facebook`

#### Telegram
1. Create a bot with [@BotFather](https://t.me/botfather)
2. Copy the bot token
3. Add to `config/settings.json` under `telegram_bot.token`

---

## 📝 Usage Examples

### Basic Usage: Process a Single File

```bash
python3 main.py --input vacancies/job_posting.txt
```

**Output:**
```
============================================================
  Ghost-autovacancy-poster
  Input: vacancies/job_posting.txt
============================================================

Found 1 message(s).

[1/1] Processing...
  Title:   Senior Python Developer
  Company: TechCorp Inc.
  [DB]   Saved as vacancy #1
  [OK]   Normalized vacancy #1
  [OK]   No duplicate found (best=0.42)
  [OK]   Poster generated for #1
  [✅] facebook: published (id=1234567890)

============================================================
  Done. 1 processed, 0 skipped.
============================================================
```

### Process Multiple Files from Directory

```bash
python3 main.py --input vacancies/
```

Automatically processes all `.txt` files in the `vacancies/` directory.

### Dry Run (Parse Without Saving)

```bash
python3 main.py --input vacancies/ --dry-run
```

Parses and shows results without writing to the database. Useful for testing.

### Skip Publishing

```bash
python3 main.py --input vacancies/ --no-publish
```

Processes vacancies but does not publish to social media platforms.

### Custom Theme

```bash
python3 main.py --input vacancies/ --theme dark
```

Available themes: `default`, `dark`, `minimal`

### Full Pipeline with Options

```bash
python3 main.py --input vacancies/ --theme dark --no-publish --dry-run
```

### CLI Help

```bash
python3 main.py --help
```

---

## 📊 Dashboard Screenshots Section

### 1. **Home Dashboard**

The home page displays a real-time overview of today's activity:

- **Total Vacancies Processed**: Number of new vacancies ingested today
- **Duplicate Flagged**: Count of duplicate postings identified
- **Successfully Published**: Posters published to platforms
- **Failed Publishes**: Publishing errors that need attention
- **Recent Vacancies**: Quick list of the 5 most recent vacancies

**Route**: `http://localhost:5000/`

### 2. **Vacancies List View**

Browse all processed vacancies with status indicators:

- **Title & Company**: Job posting details
- **Status Badge**: Pending, Processed, or Duplicate
- **Created Date**: Timestamp of ingestion
- **View Details**: Click to see full vacancy information

**Route**: `http://localhost:5000/vacancies`

### 3. **Vacancy Detail View**

Deep dive into a single vacancy:

- **Parsed Data**: Job title, company, location, salary range, job type, experience level
- **Requirements & Benefits**: Lists extracted from the posting
- **Contact Information**: Email and phone from the posting
- **Generated Poster**: Preview of the HTML poster
- **Publishing Status**: Which platforms have the poster been published to
- **Duplicate Info**: If flagged as duplicate, shows the original posting reference

**Route**: `http://localhost:5000/vacancies/<id>`

### Running the Dashboard

```bash
python3 dashboard/app.py
```

Access at: `http://localhost:5000`

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Core language | 3.9+ |
| **Flask** | Web framework (dashboard) | 3.0.0 |
| **SQLAlchemy** | ORM & database abstraction | 2.0.23 |
| **Pydantic** | Data validation & serialization | 2.4.2 |
| **Jinja2** | Template engine (HTML posters) | 3.1.2 |

### APIs & External Services
| Service | Purpose |
|---------|---------|
| **Groq API** | AI-powered vacancy parsing (LLaMA 3.3 70B) |
| **Facebook API** | Post to Facebook groups |
| **Telegram Bot API** | Send Telegram messages |
| **WhatsApp Web JS** | WhatsApp automation (Node.js integration) |

### Database
| Type | Purpose |
|------|---------|
| **SQLite** (default) | Development & small deployments |
| **PostgreSQL** | Production deployments |

### Development & Testing
| Tool | Purpose | Version |
|------|---------|---------|
| **pytest** | Unit & integration tests | 8.4.2 |
| **pytest-asyncio** | Async test support | 1.4.0 |
| **python-dotenv** | Environment variable management | 1.0.0 |
| **requests** | HTTP client for APIs | 2.31.0 |

### Messaging
| Library | Purpose | Version |
|---------|---------|---------|
| **python-telegram-bot** | Telegram bot integration | 20.7 |

---

## 👥 Contributing Guidelines

We welcome contributions! Whether it's bug reports, feature requests, or code improvements, please follow these guidelines:

### How to Contribute

1. **Fork the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ghost-autovacancy-poster.git
   cd ghost-autovacancy-poster
   git checkout -b feature/your-feature-name
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Make Your Changes**
   - Follow PEP 8 style guidelines
   - Add docstrings to functions and classes
   - Include type hints where possible
   - Update tests if applicable

5. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

6. **Commit with Meaningful Messages**
   ```bash
   git commit -m "feat: add WhatsApp poster support"
   git commit -m "fix: handle salary parsing edge cases"
   git commit -m "docs: update configuration guide"
   ```

   **Commit Types**:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation
   - `refactor`: Code refactoring
   - `test`: Adding/updating tests
   - `chore`: Dependency updates, tooling

7. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Submit a Pull Request**
   - Clear title describing the change
   - Link to any related issues
   - Describe what changed and why
   - Include any breaking changes

### Code Style

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- **Type Hints**: Use for all function parameters and return types
- **Docstrings**: Use triple-quoted strings for all modules, classes, and public functions
- **Testing**: Aim for 80%+ code coverage

### Development Areas

#### High Priority
- [ ] Implement remaining publisher modules (LinkedIn, Indeed, Twitter)
- [ ] Add comprehensive integration tests
- [ ] Improve duplicate detection algorithm (ML-based)
- [ ] Build advanced dashboard features

#### Medium Priority
- [ ] PostgreSQL support & optimization
- [ ] Celery task queue for async processing
- [ ] Email webhook integration
- [ ] Batch API endpoint

#### Low Priority
- [ ] Dark mode UI
- [ ] PDF poster export
- [ ] Scheduled posting
- [ ] Analytics dashboard

### Reporting Issues

Found a bug? Please file an issue with:
1. **Clear title** describing the problem
2. **Reproduction steps** to replicate the issue
3. **Expected vs actual behavior**
4. **Your environment**: OS, Python version, etc.
5. **Error logs** (if applicable)

### Community

- 💬 **Discussions**: Share ideas and ask questions
- 📚 **Wiki**: Contribute documentation and guides
- 🐛 **Issues**: Report bugs and request features
- ✨ **Pull Requests**: Submit code improvements

---

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Support

For questions, issues, or suggestions:

- **GitHub Issues**: [Report a bug or request a feature](https://github.com/Namunafilms022/ghost-autovacancy-poster/issues)
- **Email**: [Create an issue for inquiries]

---

## 🔗 Quick Links

- [Architecture Documentation](./ARCHITECTURE.md)
- [Configuration Guide](#-configuration)
- [API Documentation](./docs/api.md) *(coming soon)*
- [Development Guide](./docs/development.md) *(coming soon)*

---

**Made by Echosage 💀u
