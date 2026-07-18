import pytest
from datetime import datetime

from normalizer import Normalizer, NormalizedResult, JobType, ExperienceLevel
from normalizer.normalizer import _normalize_job_type, _normalize_experience
from parser import JobDetails
from database.init import init_db, drop_db
from database.session import get_session
from database.models import Vacancy


def create_vacancy(title='Software Engineer', company='Tech Co',
                   raw_message=None) -> int:
    session = get_session()
    v = Vacancy(
        title=title, company=company, processed=False,
        raw_message=raw_message or '',
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
def normalizer():
    return Normalizer()


class TestJobTypeNormalization:
    def test_full_time_variants(self):
        for inp in ['Full-time', 'Full Time', 'fulltime', 'FULL_TIME', 'Permanent']:
            assert _normalize_job_type(inp) == 'full_time'

    def test_part_time(self):
        for inp in ['Part-time', 'Part Time', 'parttime']:
            assert _normalize_job_type(inp) == 'part_time'

    def test_contract(self):
        for inp in ['Contract', 'contractual', 'Temporary']:
            assert _normalize_job_type(inp) == 'contract'

    def test_internship(self):
        for inp in ['Internship', 'Intern', 'Trainee']:
            assert _normalize_job_type(inp) == 'internship'

    def test_freelance(self):
        for inp in ['Freelance', 'Freelancer', 'Freelancing']:
            assert _normalize_job_type(inp) == 'freelance'

    def test_none(self):
        assert _normalize_job_type(None) is None
        assert _normalize_job_type('') is None

    def test_unknown(self):
        assert _normalize_job_type('Unknown Type') is None


class TestExperienceNormalization:
    def test_entry_variants(self):
        for inp in ['Entry', 'Entry Level', 'Junior', 'Jr', 'Fresher', 'Beginner']:
            assert _normalize_experience(inp) == 'entry'

    def test_mid(self):
        for inp in ['Mid', 'Mid Level', 'Intermediate']:
            assert _normalize_experience(inp) == 'mid'

    def test_senior(self):
        for inp in ['Senior', 'Sr', 'Senior Level', 'Experienced']:
            assert _normalize_experience(inp) == 'senior'

    def test_lead(self):
        for inp in ['Lead', 'Team Lead', 'Manager']:
            assert _normalize_experience(inp) == 'lead'

    def test_any(self):
        for inp in ['Any', 'Any Level', 'All', 'Not Required', 'None']:
            assert _normalize_experience(inp) == 'any'

    def test_none(self):
        assert _normalize_experience(None) is None


class TestSalaryNormalization:
    def test_npr_monthly_default(self, normalizer):
        details = JobDetails(
            title='Dev', company='C',
            salary_min=50000.0, salary_max=80000.0,
            raw_message='Salary: 50000 - 80000',
        )
        result = normalizer.normalize(details, create_vacancy(raw_message=details.raw_message))
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.salary_min == 50000.0
        assert v.salary_max == 80000.0
        session.close()

    def test_usd_yearly_conversion(self, normalizer):
        details = JobDetails(
            title='Dev', company='C',
            salary_min=120000.0, salary_max=180000.0,
            raw_message='Salary: $120k - $180k per year',
        )
        vid = create_vacancy(raw_message=details.raw_message)
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.salary_min == pytest.approx(120000.0 / 12 * 135, rel=1)
        assert v.salary_max == pytest.approx(180000.0 / 12 * 135, rel=1)
        session.close()

    def test_inr_yearly(self, normalizer):
        details = JobDetails(
            title='Dev', company='C',
            salary_min=600000.0, salary_max=1200000.0,
            raw_message='Salary: ₹6,00,000 - ₹12,00,000 per year',
        )
        vid = create_vacancy(raw_message=details.raw_message)
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.salary_min == pytest.approx(600000.0 / 12 * 1.6, rel=1)
        assert v.salary_max == pytest.approx(1200000.0 / 12 * 1.6, rel=1)
        session.close()

    def test_hourly_usd(self, normalizer):
        details = JobDetails(
            title='Dev', company='C',
            salary_min=50.0, salary_max=75.0,
            raw_message='Salary: $50 - $75 per hour',
        )
        vid = create_vacancy(raw_message=details.raw_message)
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.salary_min == pytest.approx(50.0 * 176 * 135, rel=1)
        session.close()

    def test_no_salary(self, normalizer):
        details = JobDetails(title='Dev', company='C')
        vid = create_vacancy(raw_message='')
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.salary_min is None
        assert v.salary_max is None
        session.close()


class TestValidation:
    def test_title_required(self, normalizer):
        details = JobDetails(title=None, company='C')
        vid = create_vacancy()
        result = normalizer.normalize(details, vid)
        assert not result.success
        assert any('title' in e for e in result.errors)

    def test_empty_title(self, normalizer):
        details = JobDetails(title='   ', company='C')
        vid = create_vacancy()
        result = normalizer.normalize(details, vid)
        assert not result.success

    def test_nonexistent_vacancy(self, normalizer):
        details = JobDetails(title='Dev', company='C')
        result = normalizer.normalize(details, 99999)
        assert not result.success
        assert any('not found' in e for e in result.errors)

    def test_valid_data(self, normalizer):
        details = JobDetails(
            title='  Senior  Python  Dev  ',
            company='  Tech  Corp  ',
            location='  Kathmandu,  Nepal  ',
            job_type='Full-time',
            experience_level='Senior',
        )
        vid = create_vacancy(raw_message='')
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.title == 'Senior Python Dev'
        assert v.company == 'Tech Corp'
        assert v.location == 'Kathmandu, Nepal'
        assert v.job_type == 'full_time'
        assert v.experience_level == 'senior'
        assert v.processed is True
        session.close()


class TestDatabaseUpdate:
    def test_sets_processed_true(self, normalizer):
        details = JobDetails(title='Dev', company='C')
        vid = create_vacancy(title='Old', company='Old')
        normalizer.normalize(details, vid)

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.processed is True
        assert v.title == 'Dev'
        assert v.company == 'C'
        session.close()

    def test_updates_all_fields(self, normalizer):
        details = JobDetails(
            title='Backend Engineer',
            company='Startup Nepal',
            location='Lalitpur',
            salary_min=80000.0, salary_max=150000.0,
            job_type='Contract',
            experience_level='Mid',
            requirements=['Python', 'Django'],
            benefits=['Remote'],
            contact_email='hr@startup.np',
            contact_phone='9851234567',
            raw_message='We are hiring a Backend Engineer!\nSalary: 80000 - 150000',
        )
        vid = create_vacancy(raw_message=details.raw_message)
        result = normalizer.normalize(details, vid)
        assert result.success

        session = get_session()
        v = session.query(Vacancy).first()
        assert v.title == 'Backend Engineer'
        assert v.company == 'Startup Nepal'
        assert v.location == 'Lalitpur'
        assert v.job_type == 'contract'
        assert v.experience_level == 'mid'
        assert v.processed is True
        session.close()

    def test_multiple_normalizations(self, normalizer):
        for i in range(3):
            create_vacancy(title=f'Old{i}', raw_message='')

        session = get_session()
        assert session.query(Vacancy).count() == 3
        session.close()

        session = get_session()
        for v in session.query(Vacancy).all():
            details = JobDetails(title=f'Updated {v.id}', company='New Co')
            normalizer.normalize(details, v.id)
        session.close()

        session = get_session()
        for v in session.query(Vacancy).all():
            assert v.processed is True
            assert v.title.startswith('Updated')
            assert v.company == 'New Co'
        session.close()
