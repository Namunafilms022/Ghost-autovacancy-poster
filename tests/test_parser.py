import json
from unittest.mock import patch, MagicMock

import pytest
import requests

from parser import VacancyParser, JobDetails


def _mock_groq_response(overrides: dict = None) -> MagicMock:
    defaults = {
        'title': 'Senior Python Developer',
        'company': 'Tech Company Inc.',
        'location': 'San Francisco, CA',
        'salary_min': 120000.0,
        'salary_max': 180000.0,
        'salary_currency': 'USD',
        'job_type': 'Full-time',
        'experience_level': 'Senior',
        'requirements': ['5+ years of Python experience', 'Django expertise', 'Strong problem-solving skills'],
        'benefits': ['Health Insurance', '401k matching', 'Remote work option'],
        'contact_email': 'careers@techcompany.com',
        'contact_phone': '+1-555-123-4567',
    }
    if overrides:
        defaults.update(overrides)
    payload = {
        'choices': [{'message': {'content': json.dumps(defaults)}}]
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


@pytest.fixture
def parser():
    return VacancyParser(use_groq=False)


@pytest.fixture
def groq_parser():
    with patch('parser.parser.requests.post') as mock_post:
        mock_post.return_value = _mock_groq_response()
        yield VacancyParser(use_groq=True, api_key='test_key')


class TestRegexFallbackOnly:
    """Tests that always use regex path (Groq disabled / no key)."""

    def test_standard_message(self, parser):
        text = """We are hiring a Senior Python Developer!

Company: Tech Company Inc.
Location: San Francisco, CA
Salary: $120k - $180k
Job Type: Full-time

Requirements:
- 5+ years of Python experience
- Django expertise
- Strong problem-solving skills

Benefits:
- Health Insurance
- 401k matching
- Remote work option

Contact: careers@techcompany.com
Phone: +1-555-123-4567"""

        result = parser.parse(text)
        assert result.title == "Senior Python Developer"
        assert result.company == "Tech Company Inc."
        assert result.location == "San Francisco, CA"
        assert result.salary_min == 120000.0
        assert result.salary_max == 180000.0
        assert result.job_type == "Full-time"
        assert "5+ years of Python experience" in result.requirements
        assert "Django expertise" in result.requirements
        assert "Health Insurance" in result.benefits
        assert "401k matching" in result.benefits
        assert result.contact_email == "careers@techcompany.com"
        assert result.contact_phone in ("+1-555-123-4567", "555-123-4567")

    def test_whatsapp_bold_format(self, parser):
        text = """*Job Title:* Senior Python Developer
*Company:* Tech Company Inc.
*Location:* San Francisco, CA
*Salary:* $120k - $180k
*Job Type:* Full-time
*Requirements:*
- Python
- Django
- 5+ years experience
*Benefits:*
- Health Insurance
- 401k matching
*Contact:* careers@techcompany.com"""

        result = parser.parse(text)
        assert result.title == "Senior Python Developer"
        assert result.company == "Tech Company Inc."
        assert result.location == "San Francisco, CA"
        assert result.salary_min == 120000.0
        assert result.salary_max == 180000.0
        assert result.job_type == "Full-time"
        assert "Python" in result.requirements
        assert "Health Insurance" in result.benefits
        assert result.contact_email == "careers@techcompany.com"

    def test_inr_salary(self, parser):
        text = """Position: Software Engineer
Company: ABC Pvt Ltd
Salary: \u20b96,00,000 - \u20b912,00,000"""
        result = parser.parse(text)
        assert result.salary_min == 600000.0
        assert result.salary_max == 1200000.0

    def test_lakh_salary(self, parser):
        text = """Position: Software Engineer
Company: ABC Pvt Ltd
Salary: 6 Lakh - 12 Lakh"""
        result = parser.parse(text)
        assert result.salary_min == 600000.0
        assert result.salary_max == 1200000.0

    def test_crore_salary(self, parser):
        text = """Position: Senior Manager
Company: XYZ Corp
Salary: 1 Cr - 2 Cr"""
        result = parser.parse(text)
        assert result.salary_min == 10000000.0
        assert result.salary_max == 20000000.0

    def test_single_salary(self, parser):
        text = """Position: Intern
Company: Startup Inc
Salary: $30k"""
        result = parser.parse(text)
        assert result.salary_min == 30000.0

    def test_salary_without_suffix(self, parser):
        text = """Position: Developer
Company: Foo Inc
Salary: 50000 - 80000"""
        result = parser.parse(text)
        assert result.salary_min == 50000.0
        assert result.salary_max == 80000.0

    def test_email_extraction(self, parser):
        text = """Position: Dev
Company: Test
Contact: hr@testcompany.com"""
        result = parser.parse(text)
        assert result.contact_email == "hr@testcompany.com"

    def test_phone_extraction(self, parser):
        text = """Position: Dev
Company: Test
Contact: 9876543210"""
        result = parser.parse(text)
        assert result.contact_phone is not None

    def test_email_in_text(self, parser):
        text = """Hiring a Developer!
Company: Foo
Apply at jobs@foo.com"""
        result = parser.parse(text)
        assert result.contact_email == "jobs@foo.com"

    def test_minimal_message(self, parser):
        text = """Hiring a React Developer
Company: Web Studio"""
        result = parser.parse(text)
        assert result.title is not None
        assert result.company == "Web Studio"

    def test_empty_message(self, parser):
        result = parser.parse("")
        assert isinstance(result, JobDetails)

    def test_no_requirements_section(self, parser):
        text = """Position: Designer
Company: Design Co
Location: Remote"""
        result = parser.parse(text)
        assert result.title == "Designer"
        assert result.requirements == []

    def test_requirements_without_bullets(self, parser):
        text = """Position: Tester
Company: QA Ltd
Requirements: Python, Selenium, API testing"""
        result = parser.parse(text)
        assert result.title == "Tester"

    def test_sample_from_conftest_compatibility(self, parser):
        text = """
    We are hiring a Senior Python Developer!
    
    Company: Tech Company Inc.
    Location: San Francisco, CA
    Salary: $120k - $180k
    Job Type: Full-time
    
    Requirements:
    - 5+ years of Python experience
    - Django expertise
    - Strong problem-solving skills
    
    Benefits:
    - Health Insurance
    - 401k matching
    - Remote work option
    
    Contact: careers@techcompany.com
    """
        result = parser.parse(text)
        assert result.title == "Senior Python Developer"
        assert result.company == "Tech Company Inc."
        assert result.location == "San Francisco, CA"
        assert result.salary_min == 120000.0
        assert result.salary_max == 180000.0
        assert result.job_type == "Full-time"
        assert "5+ years of Python experience" in result.requirements
        assert "Django expertise" in result.requirements
        assert result.contact_email == "careers@techcompany.com"


class TestGroqParsing:
    """Tests that use Groq API (mocked) for parsing."""

    def test_groq_returns_job_details(self, groq_parser):
        text = "Some vacancy message"
        result = groq_parser.parse(text)
        assert isinstance(result, JobDetails)
        assert result.title == "Senior Python Developer"
        assert result.company == "Tech Company Inc."
        assert result.location == "San Francisco, CA"
        assert result.salary_min == 120000.0
        assert result.salary_max == 180000.0
        assert result.job_type == "Full-time"
        assert result.experience_level == "Senior"
        assert "5+ years of Python experience" in result.requirements
        assert "Health Insurance" in result.benefits
        assert result.contact_email == "careers@techcompany.com"
        assert result.contact_phone == "+1-555-123-4567"

    def test_groq_sets_raw_message_and_description(self, groq_parser):
        text = "We are hiring a Developer!\nCompany: Test Co"
        result = groq_parser.parse(text)
        assert result.raw_message == text
        assert result.description == text[:500]

    def test_groq_sets_empty_lists_when_null(self, groq_parser):
        with patch('parser.parser.requests.post') as mock_post:
            mock_post.return_value = _mock_groq_response({
                'requirements': None,
                'benefits': None,
            })
            p = VacancyParser(use_groq=True, api_key='test_key')
            result = p.parse("Some text")
            assert result.requirements == []
            assert result.benefits == []

    def test_groq_sends_correct_request(self, groq_parser):
        text = "Hiring a Python Developer!"
        with patch('parser.parser.requests.post') as mock_post:
            mock_post.return_value = _mock_groq_response()
            p = VacancyParser(use_groq=True, api_key='my_key')
            p.parse(text)

            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args['json']['model'] == 'llama-3.3-70b-versatile'
            assert call_args['json']['messages'][1]['content'] == text
            assert call_args['headers']['Authorization'] == 'Bearer my_key'
            assert call_args['json']['response_format'] == {'type': 'json_object'}


class TestGroqFallback:
    """Tests that Groq failure falls back to regex parsing."""

    def test_fallback_on_api_error(self, parser):
        text = """Position: Software Engineer
Company: ABC Corp
Location: Remote
Salary: 80000 - 120000
Contact: hr@abccorp.com"""

        with patch('parser.parser.requests.post') as mock_post:
            mock_post.return_value = _mock_groq_response()
            mock_post.side_effect = requests.exceptions.ConnectionError('API unreachable')
            p = VacancyParser(use_groq=True, api_key='test_key')
            result = p.parse(text)

        assert result.title == "Software Engineer"
        assert result.company == "ABC Corp"
        assert result.location == "Remote"
        assert result.salary_min == 80000.0
        assert result.salary_max == 120000.0
        assert result.contact_email == "hr@abccorp.com"

    def test_fallback_on_non_200(self, parser):
        text = """Position: Designer
Company: Design Studio"""

        with patch('parser.parser.requests.post') as mock_post:
            error_resp = MagicMock()
            error_resp.status_code = 401
            mock_post.return_value = error_resp
            p = VacancyParser(use_groq=True, api_key='bad_key')
            result = p.parse(text)

        assert result.title == "Designer"
        assert result.company == "Design Studio"

    def test_fallback_on_bad_json_response(self, parser):
        text = """Position: Tester
Company: QA Ltd"""

        with patch('parser.parser.requests.post') as mock_post:
            bad_resp = MagicMock()
            bad_resp.status_code = 200
            bad_resp.json.return_value = {'choices': [{'message': {'content': 'not json'}}]}
            mock_post.return_value = bad_resp
            p = VacancyParser(use_groq=True, api_key='test_key')
            result = p.parse(text)

        assert result.title == "Tester"
        assert result.company == "QA Ltd"

    def test_fallback_when_groq_disabled(self, parser):
        p = VacancyParser(use_groq=False)
        text = """Position: Dev
Company: Test"""
        result = p.parse(text)
        assert result.title == "Dev"
        assert result.company == "Test"

    def test_fallback_when_no_api_key(self, parser):
        p = VacancyParser(use_groq=True, api_key='')
        text = """Position: Dev
Company: Test"""
        result = p.parse(text)
        assert result.title == "Dev"
        assert result.company == "Test"


class TestGroqPartialData:
    """Tests Groq with partial/missing fields."""

    def test_groq_minimal_fields(self, groq_parser):
        with patch('parser.parser.requests.post') as mock_post:
            mock_post.return_value = _mock_groq_response({
                'title': 'Developer',
                'company': 'Startup',
                'location': None,
                'salary_min': None,
                'salary_max': None,
                'job_type': None,
                'experience_level': None,
                'requirements': [],
                'benefits': [],
                'contact_email': None,
                'contact_phone': None,
            })
            p = VacancyParser(use_groq=True, api_key='test_key')
            result = p.parse("Some text")

        assert result.title == 'Developer'
        assert result.company == 'Startup'
        assert result.location is None
        assert result.salary_min is None
        assert result.salary_max is None
        assert result.job_type is None
        assert result.experience_level is None
        assert result.requirements == []
        assert result.benefits == []
        assert result.contact_email is None
        assert result.contact_phone is None

    def test_groq_salary_null_values(self, groq_parser):
        with patch('parser.parser.requests.post') as mock_post:
            mock_post.return_value = _mock_groq_response({
                'salary_min': None,
                'salary_max': None,
            })
            p = VacancyParser(use_groq=True, api_key='test_key')
            result = p.parse("Test")
        assert result.salary_min is None
        assert result.salary_max is None
