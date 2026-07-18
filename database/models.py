"""
SQLAlchemy ORM models for database tables.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from datetime import datetime

Base = declarative_base()


class Vacancy(Base):
    """Model for job vacancy records."""
    
    __tablename__ = 'vacancies'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    job_type = Column(String(50), nullable=True)
    experience_level = Column(String(100), nullable=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    duplicate_of = Column(Integer, nullable=True)
    raw_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed = Column(Boolean, default=False, index=True)
    
    def __repr__(self) -> str:
        return f"<Vacancy(id={self.id}, title={self.title}, company={self.company})>"


class VacancyPoster(Base):
    """Model for generated vacancy posters."""
    
    __tablename__ = 'vacancy_posters'
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, nullable=False, index=True)
    html_content = Column(Text, nullable=False)
    template_name = Column(String(255), nullable=True)
    theme = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f"<VacancyPoster(id={self.id}, vacancy_id={self.vacancy_id})>"


class PublishedPost(Base):
    """Model for published vacancy posts."""
    
    __tablename__ = 'published_posts'
    
    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(100), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)
    status = Column(String(50), default='pending', index=True)
    published_at = Column(DateTime, nullable=True)
    url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PublishedPost(id={self.id}, vacancy_id={self.vacancy_id}, platform={self.platform})>"


class QueueItem(Base):
    """Model for queue items waiting to be published."""

    __tablename__ = 'queue_items'

    QUEUE_STATUSES = ('draft', 'queued', 'publishing', 'published', 'failed', 'partially_published')

    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), default='queued', index=True)
    platforms = Column(JSON, default=dict)
    platform_states = Column(JSON, default=dict)
    poster_path = Column(String(500), nullable=True)
    caption_path = Column(String(500), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<QueueItem(id={self.id}, vacancy_id={self.vacancy_id}, status={self.status})>"


class SocialAccount(Base):
    """Connected social media accounts for publishing."""

    __tablename__ = 'social_accounts'

    PLATFORMS = ('facebook', 'linkedin', 'instagram', 'twitter', 'telegram')

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    account_id = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    refresh_token = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SocialAccount(id={self.id}, platform={self.platform}, name={self.account_name})>"


class PublishLog(Base):
    __tablename__ = 'publish_logs'

    id = Column(Integer, primary_key=True, index=True)
    vacancy_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    error = Column(Text, nullable=True)
    platform_post_id = Column(String(255), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<PublishLog(id={self.id}, vacancy={self.vacancy_id}, platform={self.platform}, status={self.status})>"


class AutomationRule(Base):
    __tablename__ = 'automation_rules'

    TRIGGERS = ('immediate', 'scheduled')

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    trigger = Column(String(50), nullable=False, default='immediate')
    schedule_time = Column(String(5), nullable=True)
    schedule_days = Column(JSON, default=list)
    platforms = Column(JSON, default=list)
    conditions = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AutomationRule(id={self.id}, name={self.name}, trigger={self.trigger})>"
