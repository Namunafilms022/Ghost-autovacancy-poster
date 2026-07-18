import pytest
from parser.models import JobDetails
from ghost_module.summarizer import (
    summarize_vacancy, summarizeVacancy, SummaryResult,
)


def make_jd(**overrides) -> JobDetails:
    defaults = dict(
        title='Senior Web Developer',
        company='TechCorp',
        location='Kathmandu',
        salary_min=80000,
        salary_max=120000,
        job_type='full_time',
        experience_level='senior',
        requirements=['HTML', 'CSS', 'JavaScript', 'React', 'Node.js'],
        benefits=['Health Insurance', 'Remote Work', 'Bonus'],
    )
    defaults.update(overrides)
    return JobDetails(**defaults)


class TestCamelCaseAlias:
    def test_alias(self):
        assert summarizeVacancy is summarize_vacancy


class TestSummaryResult:
    def test_returns_summaryresult(self):
        r = summarize_vacancy(make_jd())
        assert isinstance(r, SummaryResult)

    def test_full_job(self):
        r = summarize_vacancy(make_jd())
        assert r.title == 'Senior Web Developer'
        assert r.company == 'TechCorp'
        assert r.location == 'Kathmandu'
        assert 'Rs.80,000' in r.salary
        assert 'Rs.120,000' in r.salary
        assert r.experience == 'Senior Level'

    def test_short_summary_format(self):
        r = summarize_vacancy(make_jd())
        assert 'Senior Web Developer at TechCorp' in r.short_summary
        assert 'based in Kathmandu' in r.short_summary
        assert 'offering' in r.short_summary
        assert r.short_summary.endswith('.')

    def test_max_five_bullets(self):
        r = summarize_vacancy(make_jd())
        assert len(r.bullet_points) <= 5

    def test_bullets_ordered_by_importance(self):
        r = summarize_vacancy(make_jd())
        assert r.bullet_points[0] == 'Kathmandu'
        assert 'Rs' in r.bullet_points[1]

    def test_bullet_includes_skills(self):
        r = summarize_vacancy(make_jd())
        skills_bullet = [b for b in r.bullet_points if 'HTML' in b]
        assert len(skills_bullet) >= 1
        assert 'JavaScript' in skills_bullet[0]

    def test_requirements_truncated(self):
        many = [f'Skill{i}' for i in range(10)]
        r = summarize_vacancy(make_jd(requirements=many))
        skills = [b for b in r.bullet_points if 'Skill' in b]
        if skills:
            assert '…' in skills[0]

    def test_benefits_bullet(self):
        r = summarize_vacancy(make_jd(requirements=[], salary_min=None, salary_max=None))
        has_benefits = any('Health' in b for b in r.bullet_points)
        assert has_benefits


class TestHandleMissingFields:
    def test_missing_title(self):
        r = summarize_vacancy(make_jd(title=None))
        assert r.title == 'Untitled Position'

    def test_missing_company(self):
        r = summarize_vacancy(make_jd(company=None))
        assert r.company == 'Unknown Company'

    def test_missing_location(self):
        r = summarize_vacancy(make_jd(location=None))
        assert r.location == 'Location not specified'

    def test_missing_salary(self):
        r = summarize_vacancy(make_jd(salary_min=None, salary_max=None))
        assert r.salary == 'Not specified'

    def test_missing_experience(self):
        r = summarize_vacancy(make_jd(experience_level=None))
        assert r.experience == 'Not specified'

    def test_minimal_job(self):
        r = summarize_vacancy(JobDetails())
        assert r.title == 'Untitled Position'
        assert r.company == 'Unknown Company'
        assert r.salary == 'Not specified'
        assert r.experience == 'Not specified'
        assert len(r.bullet_points) == 0

    def test_short_summary_with_missing_location(self):
        r = summarize_vacancy(make_jd(location=None))
        assert 'based in' not in r.short_summary

    def test_empty_bullets_for_empty_jd(self):
        r = summarize_vacancy(JobDetails())
        assert r.bullet_points == []


class TestSalaryFormatting:
    def test_salary_range(self):
        r = summarize_vacancy(make_jd(salary_min=50000, salary_max=80000))
        assert 'Rs.50,000 - Rs.80,000' in r.salary

    def test_salary_single_value(self):
        r = summarize_vacancy(make_jd(salary_min=60000, salary_max=60000))
        assert 'Rs.60,000' in r.salary
        assert '-' not in r.salary

    def test_salary_min_only(self):
        r = summarize_vacancy(make_jd(salary_min=75000, salary_max=None))
        assert 'Rs.75,000' in r.salary

    def test_salary_max_only(self):
        r = summarize_vacancy(make_jd(salary_min=None, salary_max=100000))
        assert 'Rs.100,000' in r.salary

    def test_salary_with_period(self):
        r = summarize_vacancy(make_jd(job_type='monthly'))
        assert '/month' in r.salary or 'month' in r.salary


class TestExperienceFormatting:
    def test_entry_level(self):
        r = summarize_vacancy(make_jd(experience_level='entry'))
        assert r.experience == 'Entry Level'

    def test_mid_level(self):
        r = summarize_vacancy(make_jd(experience_level='mid'))
        assert r.experience == 'Mid Level'

    def test_lead_level(self):
        r = summarize_vacancy(make_jd(experience_level='lead'))
        assert r.experience == 'Lead / Manager'

    def test_any_experience(self):
        r = summarize_vacancy(make_jd(experience_level='any'))
        assert r.experience == 'Any Experience'

    def test_unexpected_value(self):
        r = summarize_vacancy(make_jd(experience_level='director'))
        assert r.experience == 'Director'
