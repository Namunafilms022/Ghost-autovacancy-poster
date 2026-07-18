import pytest
import os
import re
import tempfile
from pathlib import Path

from poster import PosterGenerator
from poster.themes import (
    ALL_THEMES, AVAILABLE_THEMES, auto_select_theme, get_theme,
)
from database.init import init_db, drop_db
from database.session import get_session
from database.models import Vacancy, VacancyPoster


def create_vacancy(
    title='Software Engineer',
    company='Tech Corp',
    location='Kathmandu',
    salary_min=60000.0,
    salary_max=100000.0,
    job_type='full_time',
    experience_level='mid',
    processed=True,
    raw_message=(
        'We are hiring a Software Engineer!\n'
        'Company: Tech Corp\n'
        'Location: Kathmandu\n'
        'Salary: 60000 - 100000\n'
        'Requirements:\n'
        '- Python\n'
        '- Django\n'
        '- 2+ years experience\n'
        'Benefits:\n'
        '- Health Insurance\n'
        '- Remote Work\n'
        'Contact: hr@techcorp.com\n'
        'Phone: 9851234567'
    ),
) -> int:
    session = get_session()
    v = Vacancy(
        title=title, company=company, location=location,
        salary_min=salary_min, salary_max=salary_max,
        job_type=job_type, experience_level=experience_level,
        processed=processed, raw_message=raw_message,
    )
    session.add(v)
    session.commit()
    vid = v.id
    session.close()
    return vid


@pytest.fixture(autouse=True)
def db():
    init_db()
    yield
    drop_db()


@pytest.fixture
def poster():
    return PosterGenerator(replace_enabled=False)


class TestGenerate:
    def test_generates_html(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert isinstance(html, str)
        assert len(html) > 200
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

    def test_contains_title(self, poster):
        vid = create_vacancy(title='Lead DevOps Engineer')
        html = poster.generate(vid)
        assert 'Lead DevOps Engineer' in html

    def test_contains_company(self, poster):
        vid = create_vacancy(company='Nepal Tech Solutions')
        html = poster.generate(vid)
        assert 'Nepal Tech Solutions' in html

    def test_contains_location(self, poster):
        vid = create_vacancy(location='Pokhara')
        html = poster.generate(vid)
        assert 'Pokhara' in html

    def test_contains_salary(self, poster):
        vid = create_vacancy(salary_min=50000.0, salary_max=80000.0)
        html = poster.generate(vid)
        assert '50,000' in html
        assert '80,000' in html

    def test_contains_requirements(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert 'Python' in html
        assert 'Django' in html

    def test_contains_benefits(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert 'Health Insurance' in html
        assert 'Remote Work' in html

    def test_contains_contact(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert 'hr@techcorp.com' in html
        assert '9851234567' in html

    def test_job_type_formatted(self, poster):
        vid = create_vacancy(job_type='full_time')
        html = poster.generate(vid)
        assert 'Full-time' in html

    def test_experience_formatted(self, poster):
        vid = create_vacancy(experience_level='senior')
        html = poster.generate(vid)
        assert 'Senior Level' in html

    def test_vacancy_not_found(self, poster):
        with pytest.raises(ValueError, match='not found'):
            poster.generate(99999)

    def test_missing_fields_handled(self, poster):
        session = get_session()
        v = Vacancy(title='Dev', company='C', processed=True)
        session.add(v)
        session.commit()
        vid = v.id
        session.close()

        html = poster.generate(vid)
        assert 'Dev' in html
        assert 'C' in html

    def test_auto_theme_when_none(self, poster):
        vid = create_vacancy(job_type='internship')
        html = poster.generate(vid, theme=None)
        assert isinstance(html, str)
        assert len(html) > 200

    def test_all_themes_generate(self, poster):
        vid = create_vacancy()
        for theme_name in AVAILABLE_THEMES:
            html = poster.generate(vid, theme=theme_name)
            assert isinstance(html, str)
            assert len(html) > 200
            assert 'Software Engineer' in html


class TestThemes:
    def test_all_themes_defined(self):
        assert len(ALL_THEMES) >= 7
        assert 'minimal' in AVAILABLE_THEMES
        assert 'glass' in AVAILABLE_THEMES
        assert 'dark_neon' in AVAILABLE_THEMES
        assert 'corporate_hiring_red' in AVAILABLE_THEMES
        assert 'ghost' in AVAILABLE_THEMES
        assert 'cyberpunk' in AVAILABLE_THEMES
        assert 'blue_professional' in AVAILABLE_THEMES

    def test_theme_has_css_vars(self):
        for t in ALL_THEMES:
            vars = t.css_vars
            assert '--bg' in vars
            assert '--accent' in vars
            assert '--text-primary' in vars
            assert '--surface' in vars

    def test_theme_has_font(self):
        for t in ALL_THEMES:
            assert t.font.heading
            assert t.font.body

    def test_minimal_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='minimal')
        assert '#fafafa' in html

    def test_glass_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='glass')
        assert 'backdrop-filter' in html or 'Glass' in html or 'rgba' in html

    def test_dark_neon_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='dark_neon')
        assert '#00ff88' in html or '#0a0a0f' in html

    def test_corporate_hiring_red_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='corporate_hiring_red')
        assert '#dc2626' in html

    def test_ghost_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='ghost')
        assert '#8b5cf6' in html

    def test_cyberpunk_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='cyberpunk')
        assert '#f0e100' in html

    def test_blue_professional_theme(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid, theme='blue_professional')
        assert '#2563eb' in html

    def test_invalid_theme(self, poster):
        vid = create_vacancy()
        with pytest.raises(ValueError, match='Unknown theme'):
            poster.generate(vid, theme='nonexistent')


class TestAutoSelectTheme:
    def test_high_confidence(self):
        assert auto_select_theme(confidence=0.95) == 'blue_professional'

    def test_medium_confidence(self):
        assert auto_select_theme(confidence=0.75) == 'dark_neon'

    def test_low_confidence(self):
        assert auto_select_theme(confidence=0.4) == 'ghost'

    def test_freelance_job(self):
        assert auto_select_theme(job_type='freelance') == 'cyberpunk'

    def test_internship(self):
        assert auto_select_theme(job_type='internship') == 'glass'

    def test_senior_experience(self):
        assert auto_select_theme(experience='senior') == 'blue_professional'

    def test_junior_experience(self):
        assert auto_select_theme(experience='junior') == 'minimal'

    def test_default_fallback(self):
        assert auto_select_theme() == 'dark_neon'


class TestSave:
    def test_saves_html_file(self, poster):
        vid = create_vacancy()
        with tempfile.TemporaryDirectory() as d:
            path = poster.save(vid, os.path.join(d, 'poster.html'))
            assert path.exists()
            content = path.read_text(encoding='utf-8')
            assert '<!DOCTYPE html>' in content

    def test_save_with_theme(self, poster):
        vid = create_vacancy()
        with tempfile.TemporaryDirectory() as d:
            path = poster.save(vid, os.path.join(d, 'poster.html'), theme='cyberpunk')
            content = path.read_text(encoding='utf-8')
            assert '#f0e100' in content


class TestDatabaseRecord:
    def test_saves_vacancy_poster_record(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)

        session = get_session()
        records = session.query(VacancyPoster).filter(
            VacancyPoster.vacancy_id == vid
        ).all()
        assert len(records) == 1
        assert records[0].html_content == html
        assert records[0].template_name == 'theme.html'
        assert records[0].theme in AVAILABLE_THEMES
        session.close()

    def test_multiple_generations_create_multiple_records(self, poster):
        vid = create_vacancy()
        poster.generate(vid, theme='minimal')
        poster.generate(vid, theme='cyberpunk')

        session = get_session()
        records = session.query(VacancyPoster).filter(
            VacancyPoster.vacancy_id == vid
        ).all()
        assert len(records) == 2
        assert records[0].theme != records[1].theme
        session.close()

    def test_poster_record_has_html(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)

        session = get_session()
        record = session.query(VacancyPoster).filter(
            VacancyPoster.vacancy_id == vid
        ).first()
        assert record.html_content == html
        assert len(record.html_content) > 100
        session.close()

    def test_theme_name_stored_in_record(self, poster):
        vid = create_vacancy()
        poster.generate(vid, theme='ghost')
        session = get_session()
        record = session.query(VacancyPoster).filter(
            VacancyPoster.vacancy_id == vid
        ).first()
        assert record.theme == 'ghost'
        session.close()


class TestPhoneReplacement:
    def test_replaces_phone_with_custom_number(self, poster):
        vid = create_vacancy()
        replacer = PosterGenerator(replace_phone='9841002002', replace_email=None,
                                    replace_enabled=True)
        html = replacer.generate(vid)
        assert '9841002002' in html
        assert '9851234567' not in html

    def test_replaces_email_when_configured(self, poster):
        vid = create_vacancy()
        replacer = PosterGenerator(replace_phone=None, replace_email='agent@mydomain.com',
                                    replace_enabled=True)
        html = replacer.generate(vid)
        assert 'agent@mydomain.com' in html
        assert 'hr@techcorp.com' not in html

    def test_replaces_both_phone_and_email(self, poster):
        vid = create_vacancy()
        replacer = PosterGenerator(replace_phone='9841002002',
                                    replace_email='agent@mydomain.com',
                                    replace_enabled=True)
        html = replacer.generate(vid)
        assert '9841002002' in html
        assert 'agent@mydomain.com' in html
        assert '9851234567' not in html
        assert 'hr@techcorp.com' not in html

    def test_original_phone_preserved_when_disabled(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert '9851234567' in html


class TestEdgeCases:
    def test_no_raw_message(self, poster):
        vid = create_vacancy(raw_message='')
        html = poster.generate(vid)
        assert 'Software Engineer' in html

    def test_minimal_data(self, poster):
        session = get_session()
        v = Vacancy(title='Dev', company='Co', processed=True)
        session.add(v)
        session.commit()
        vid = v.id
        session.close()

        html = poster.generate(vid)
        assert 'Dev' in html
        assert 'Co' in html

    def test_html_is_valid_structure(self, poster):
        vid = create_vacancy()
        html = poster.generate(vid)
        assert html.count('<html') == 1
        assert html.count('</html>') == 1
        assert html.count('<body') == 1
        assert html.count('</body>') == 1
        assert html.count('<head') == 1
        assert html.count('</head>') == 1
