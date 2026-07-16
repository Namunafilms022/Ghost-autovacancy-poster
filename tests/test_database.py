"""
Database initialization and integration tests for Phase 0.
"""

import pytest
import os
from pathlib import Path
from datetime import datetime

from database.init import init_db, drop_db, reset_db
from database.models import Vacancy, VacancyPoster, PublishedPost
from database.session import get_session, SessionLocal


class TestDatabaseInitialization:
    """Tests for database initialization and basic operations."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Reset database before each test
        reset_db()
        yield
        # Clean up after test
        drop_db()
    
    def test_database_file_created(self):
        """Test that SQLite database file is created."""
        init_db()
        
        # Check if database file exists
        db_path = Path("ghost_vacancies.db")
        assert db_path.exists(), "Database file should be created"
    
    def test_all_tables_created(self):
        """Test that all required tables are created."""
        init_db()
        
        # Get table names from the database
        from sqlalchemy import inspect
        inspector = inspect(get_session().get_bind())
        table_names = inspector.get_table_names()
        
        # Verify all expected tables exist
        assert 'vacancies' in table_names, "Vacancies table should be created"
        assert 'vacancy_posters' in table_names, "VacancyPoster table should be created"
        assert 'published_posts' in table_names, "PublishedPost table should be created"
    
    def test_insert_vacancy(self):
        """Test inserting a sample vacancy into the database."""
        init_db()
        session = get_session()
        
        # Create a sample vacancy
        vacancy = Vacancy(
            title='Senior Python Developer',
            description='We are looking for an experienced Python developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
            salary_min=120000.0,
            salary_max=180000.0,
            job_type='Full-time',
            experience_level='Senior',
            raw_message='Sample vacancy message',
            processed=False
        )
        
        # Insert into database
        session.add(vacancy)
        session.commit()
        
        # Verify insertion
        assert vacancy.id is not None, "Vacancy should have an ID after insertion"
        
        session.close()
    
    def test_read_vacancy(self):
        """Test reading a vacancy from the database."""
        init_db()
        session = get_session()
        
        # Create and insert a vacancy
        vacancy = Vacancy(
            title='Senior Python Developer',
            description='We are looking for an experienced Python developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
            salary_min=120000.0,
            salary_max=180000.0,
            job_type='Full-time',
            experience_level='Senior',
            raw_message='Sample vacancy message',
            processed=False
        )
        session.add(vacancy)
        session.commit()
        vacancy_id = vacancy.id
        
        session.close()
        
        # Create new session and read the vacancy
        session = get_session()
        retrieved_vacancy = session.query(Vacancy).filter(
            Vacancy.id == vacancy_id
        ).first()
        
        # Verify all fields
        assert retrieved_vacancy is not None, "Vacancy should be retrieved"
        assert retrieved_vacancy.title == 'Senior Python Developer'
        assert retrieved_vacancy.company == 'Tech Company Inc.'
        assert retrieved_vacancy.location == 'San Francisco, CA'
        assert retrieved_vacancy.salary_min == 120000.0
        assert retrieved_vacancy.salary_max == 180000.0
        assert retrieved_vacancy.job_type == 'Full-time'
        assert retrieved_vacancy.experience_level == 'Senior'
        assert retrieved_vacancy.is_duplicate is False
        assert retrieved_vacancy.processed is False
        
        session.close()
    
    def test_insert_and_read_vacancy_poster(self):
        """Test inserting and reading a vacancy poster."""
        init_db()
        session = get_session()
        
        # Create and insert a vacancy first
        vacancy = Vacancy(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
            job_type='Full-time',
            processed=False
        )
        session.add(vacancy)
        session.commit()
        vacancy_id = vacancy.id
        
        # Create and insert a poster
        poster = VacancyPoster(
            vacancy_id=vacancy_id,
            html_content='<html><body>Senior Python Developer at Tech Company</body></html>',
            template_name='professional',
            theme='professional'
        )
        session.add(poster)
        session.commit()
        poster_id = poster.id
        
        session.close()
        
        # Read back the poster
        session = get_session()
        retrieved_poster = session.query(VacancyPoster).filter(
            VacancyPoster.id == poster_id
        ).first()
        
        assert retrieved_poster is not None
        assert retrieved_poster.vacancy_id == vacancy_id
        assert retrieved_poster.template_name == 'professional'
        assert retrieved_poster.theme == 'professional'
        assert '<body>' in retrieved_poster.html_content
        
        session.close()
    
    def test_multiple_vacancies(self):
        """Test inserting and retrieving multiple vacancies."""
        init_db()
        session = get_session()
        
        # Insert multiple vacancies
        vacancies_data = [
            {
                'title': 'Senior Python Developer',
                'company': 'Tech Company Inc.',
                'location': 'San Francisco, CA',
                'job_type': 'Full-time'
            },
            {
                'title': 'Junior Frontend Engineer',
                'company': 'Web Startup',
                'location': 'New York, NY',
                'job_type': 'Full-time'
            },
            {
                'title': 'DevOps Engineer',
                'company': 'Cloud Services Ltd.',
                'location': 'Remote',
                'job_type': 'Full-time'
            }
        ]
        
        for data in vacancies_data:
            vacancy = Vacancy(**data, processed=False)
            session.add(vacancy)
        
        session.commit()
        session.close()
        
        # Retrieve all vacancies
        session = get_session()
        all_vacancies = session.query(Vacancy).all()
        
        assert len(all_vacancies) == 3, "Should have 3 vacancies"
        assert all_vacancies[0].title == 'Senior Python Developer'
        assert all_vacancies[1].title == 'Junior Frontend Engineer'
        assert all_vacancies[2].title == 'DevOps Engineer'
        
        session.close()
    
    def test_vacancy_timestamps(self):
        """Test that vacancy timestamps are set automatically."""
        init_db()
        session = get_session()
        
        before_insert = datetime.utcnow()
        
        vacancy = Vacancy(
            title='Test Job',
            company='Test Company',
            job_type='Full-time',
            processed=False
        )
        session.add(vacancy)
        session.commit()
        
        after_insert = datetime.utcnow()
        
        # Verify timestamps
        assert vacancy.created_at is not None, "created_at should be set"
        assert vacancy.updated_at is not None, "updated_at should be set"
        assert before_insert <= vacancy.created_at <= after_insert
        assert before_insert <= vacancy.updated_at <= after_insert
        
        session.close()
    
    def test_database_reset(self):
        """Test that database reset works correctly."""
        init_db()
        session = get_session()
        
        # Insert a vacancy
        vacancy = Vacancy(
            title='Test Job',
            company='Test Company',
            job_type='Full-time',
            processed=False
        )
        session.add(vacancy)
        session.commit()
        session.close()
        
        # Verify vacancy exists
        session = get_session()
        count_before = session.query(Vacancy).count()
        assert count_before == 1
        session.close()
        
        # Reset database
        reset_db()
        
        # Verify vacancy is gone
        session = get_session()
        count_after = session.query(Vacancy).count()
        assert count_after == 0, "Database should be empty after reset"
        session.close()
