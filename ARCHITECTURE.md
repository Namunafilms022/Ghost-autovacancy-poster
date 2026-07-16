# Architecture Documentation

## System Architecture

Ghost Autovacancy Poster follows a modular pipeline architecture designed for scalability and maintainability.

### Pipeline Flow

```
┌─────────────────┐
│  Message Input  │
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │ Reader  │  ◄── Message ingestion from multiple sources
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Parser  │  ◄── Extract job details using NLP/AI
    └────┬────┘
         │
         ▼
    ┌───────────────┐
    │ Normalizer    │  ◄── Standardize data format
    └────┬──────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Duplicate Detector   │  ◄── Identify duplicate postings
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────┐
    │ Poster Generator │  ◄── Create HTML posters
    └────┬─────────────┘
         │
         ▼
    ┌──────────┐
    │Publisher │  ◄── Publish to multiple platforms
    └────┬─────┘
         │
         ▼
┌─────────────────────┐
│Output (Publishing)  │
│- Social Media       │
│- Job Boards         │
│- Custom Platforms   │
└─────────────────────┘
```

## Module Responsibilities

### Reader Module (`reader/`)
- **Purpose**: Ingests vacancy messages from multiple sources
- **Responsibilities**:
  - Connect to message sources (email, API, files, webhooks)
  - Fetch and queue messages for processing
  - Handle authentication and retries
- **Phase**: 1 (Implementation)
- **Dependencies**: None

### Parser Module (`parser/`)
- **Purpose**: Extracts structured job information from text
- **Responsibilities**:
  - Parse unstructured vacancy text
  - Extract job title, company, salary, requirements, etc.
  - Use NLP/AI for intelligent extraction
  - Return structured `JobDetails` objects
- **Phase**: 1 (Implementation)
- **Dependencies**: `nltk`, `spacy`, NLP models

### Normalizer Module (`normalizer/`)
- **Purpose**: Standardizes job data across formats
- **Responsibilities**:
  - Clean and validate extracted data
  - Standardize fields (e.g., job types, experience levels)
  - Normalize salary ranges, locations, dates
  - Handle data inconsistencies
- **Phase**: 1 (Implementation)
- **Dependencies**: `utils/`

### Duplicate Module (`duplicate/`)
- **Purpose**: Identifies duplicate job postings
- **Responsibilities**:
  - Compare new listings with existing ones
  - Calculate similarity scores
  - Flag likely duplicates with confidence levels
  - Store duplicate relationships in database
- **Phase**: 1 (Implementation)
- **Dependencies**: `database/`, ML libraries (future)

### Poster Module (`poster/`)
- **Purpose**: Generates professional HTML job posters
- **Responsibilities**:
  - Load HTML templates
  - Render templates with job data
  - Apply theme styling
  - Generate clean, consistent posters
  - Export to multiple formats (HTML, PDF)
- **Phase**: 2 (Implementation)
- **Dependencies**: `jinja2`, `parser/`

### Publisher Module (`publisher/`)
- **Purpose**: Distributes posters to multiple platforms
- **Responsibilities**:
  - Manage platform-specific APIs
  - Handle authentication and credentials
  - Format content for each platform
  - Schedule publications
  - Track publication status
- **Phase**: 3 (Implementation)
- **Dependencies**: Platform SDKs, API clients

### Database Module (`database/`)
- **Purpose**: Persistent data storage layer
- **Responsibilities**:
  - Define ORM models
  - Manage database connections
  - Handle migrations
  - Provide session management
- **Phase**: 0 (Complete)
- **Dependencies**: `sqlalchemy`, PostgreSQL

### Logger Module (`logger/`)
- **Purpose**: Structured logging throughout the system
- **Responsibilities**:
  - Provide consistent logging interface
  - Support JSON and text formats
  - Log to files and console
  - Handle log rotation
- **Phase**: 0 (Complete)
- **Dependencies**: Python stdlib `logging`

### Config Module (`config/`)
- **Purpose**: Centralized configuration management
- **Responsibilities**:
  - Load settings from JSON files
  - Provide config access throughout app
  - Support environment overrides
  - Validate configuration
- **Phase**: 0 (Complete)
- **Dependencies**: None

### Utils Module (`utils/`)
- **Purpose**: Shared helper functions and utilities
- **Responsibilities**:
  - Text processing and validation
  - Decorators (retry, timer, deprecated)
  - Common algorithms
- **Phase**: 0 (Complete)
- **Dependencies**: None

## Data Models

### Vacancy
```
- id: Primary key
- title: Job title
- description: Full job description
- company: Company name
- location: Job location
- salary_min, salary_max: Salary range
- job_type: Full-time, Part-time, etc.
- experience_level: Entry, Mid, Senior, etc.
- is_duplicate: Flag for duplicates
- duplicate_of: Reference to original posting
- raw_message: Original input message
- processed: Processing status
- created_at, updated_at: Timestamps
```

### VacancyPoster
```
- id: Primary key
- vacancy_id: Foreign key to Vacancy
- html_content: Generated HTML
- template_name: Template used
- theme: Applied theme
- created_at: Timestamp
```

### PublishedPost
```
- id: Primary key
- vacancy_id: Foreign key to Vacancy
- platform: Platform name (LinkedIn, Twitter, etc.)
- external_id: Platform's post ID
- status: pending, published, failed
- published_at: When published
- url: Link to published post
- created_at, updated_at: Timestamps
```

## Integration Points

### Future Integrations (Phase 3)
- LinkedIn API for job posting
- Twitter API for announcements
- Indeed API
- Facebook API
- Custom webhooks
- Email notifications

### Database Backend
- PostgreSQL (primary)
- Extensible to other SQL databases

### Message Sources
- Email (IMAP/SMTP)
- HTTP API endpoints
- File uploads (CSV, JSON)
- Webhooks
- Message queues (Celery/Redis)

## Scalability Considerations

1. **Asynchronous Processing**: Future phases will use Celery for background tasks
2. **Database Indexing**: Key fields indexed for performance
3. **Caching**: Redis support for duplicate detection caching
4. **Batch Processing**: Efficient handling of multiple vacancies
5. **Rate Limiting**: Platform-specific rate limit handling

## Security Considerations

1. **Configuration**: Secrets stored in environment variables
2. **Database**: Connection pooling and encryption
3. **API Keys**: Secure storage and rotation
4. **Input Validation**: All inputs validated before processing
5. **SQL Injection Prevention**: Using ORM (SQLAlchemy)

## Error Handling

- Graceful degradation on module failures
- Retry logic with exponential backoff
- Comprehensive logging of errors
- Error notifications for critical failures

## Testing Strategy

- Unit tests for each module
- Integration tests for pipeline
- Fixtures for test data
- Mocking for external dependencies
- Coverage targets: 80%+
