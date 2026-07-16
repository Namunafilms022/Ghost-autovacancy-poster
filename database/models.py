"""
SQLAlchemy ORM models for database tables.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
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
