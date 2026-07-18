import pytest
from parser import VacancyParser, JobDetails


@pytest.fixture
def parser():
    return VacancyParser()


class TestBasicParsing:
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


class TestSalaryParsing:
    def test_inr_salary(self, parser):
        text = """Position: Software Engineer
Company: ABC Pvt Ltd
Salary: ₹6,00,000 - ₹12,00,000"""
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


class TestContactExtraction:
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


class TestEdgeCases:
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

        from parser import JobDetails
        details = JobDetails(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            description='We are looking for an experienced Python developer...',
            location='San Francisco, CA',
            salary_min=120000,
            salary_max=180000,
            job_type='Full-time',
            experience_level='Senior',
            requirements=['Python', 'Django', '5+ years experience'],
            benefits=['Health Insurance', '401k', 'Remote'],
        )
        assert details.title == result.title
        assert details.company == result.company
