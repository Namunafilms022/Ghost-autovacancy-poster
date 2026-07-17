import pytest
from datetime import datetime

from duplicate import DuplicateDetector, DuplicateResult
from duplicate.detector import (_text_similarity, _salary_overlap,
                                _calculate_similarity, WEIGHT_TITLE,
                                WEIGHT_COMPANY, WEIGHT_LOCATION, WEIGHT_SALARY)
from parser import JobDetails
from database.init import init_db, drop_db
from database.session import get_session
from database.models import Vacancy


def create_processed_vacancy(title='Engineer', company='Corp',
                              location='Kathmandu', salary_min=50000.0,
                              salary_max=80000.0, processed=True,
                              is_duplicate=False,
                              raw_message='') -> int:
    session = get_session()
    v = Vacancy(
        title=title, company=company, location=location,
        salary_min=salary_min, salary_max=salary_max,
        processed=processed, is_duplicate=is_duplicate,
        raw_message=raw_message,
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
def detector():
    return DuplicateDetector(similarity_threshold=0.85)


class TestTextSimilarity:
    def test_identical(self):
        assert _text_similarity('Senior Python Dev', 'Senior Python Dev') == 1.0

    def test_case_insensitive(self):
        s = _text_similarity('SENIOR PYTHON DEV', 'senior python dev')
        assert s == 1.0

    def test_whitespace_insensitive(self):
        s = _text_similarity('  Senior  Python  Dev  ', 'Senior Python Dev')
        assert s == 1.0

    def test_similar_strings(self):
        s = _text_similarity('Senior Python Developer', 'Sr. Python Developer')
        assert 0.7 < s < 1.0

    def test_different_strings(self):
        assert _text_similarity('Plumber', 'Senior Python Dev') < 0.3

    def test_none_or_empty(self):
        assert _text_similarity(None, 'Dev') == 0.0
        assert _text_similarity('Dev', None) == 0.0
        assert _text_similarity('', 'Dev') == 0.0
        assert _text_similarity(None, None) == 0.0


class TestSalaryOverlap:
    def test_perfect_overlap(self):
        assert _salary_overlap(50000, 80000, 50000, 80000) == 1.0

    def test_partial_overlap(self):
        s = _salary_overlap(50000, 80000, 60000, 90000)
        assert s == 0.5

    def test_no_overlap(self):
        assert _salary_overlap(50000, 60000, 80000, 90000) == 0.0

    def test_one_contained(self):
        s = _salary_overlap(40000, 100000, 60000, 80000)
        assert 0.3 < s < 0.4

    def test_none_values(self):
        assert _salary_overlap(None, 80000, 50000, 80000) == 0.0
        assert _salary_overlap(50000, None, 50000, 80000) == 0.0
        assert _salary_overlap(None, None, 50000, 80000) == 0.0


class TestCalculateSimilarity:
    def test_identical_records(self):
        d = JobDetails(title='Dev', company='Corp', location='KT',
                       salary_min=50000.0, salary_max=80000.0)
        session = get_session()
        v = Vacancy(title='Dev', company='Corp', location='KT',
                    salary_min=50000.0, salary_max=80000.0,
                    processed=True)
        score, fields = _calculate_similarity(d, v)
        session.close()
        assert score == 1.0

    def test_different_records(self):
        d = JobDetails(title='Plumber', company='Fix It Co',
                       location='Pokhara', salary_min=30000.0,
                       salary_max=40000.0)
        session = get_session()
        v = Vacancy(title='Senior Python Dev', company='Tech Inc',
                    location='Kathmandu', salary_min=120000.0,
                    salary_max=180000.0, processed=True)
        score, fields = _calculate_similarity(d, v)
        session.close()
        assert score < 0.3

    def test_weight_distribution(self):
        d = JobDetails(title='Software Engineer', company='ABC Corp',
                       location='Lalitpur', salary_min=60000.0,
                       salary_max=100000.0)
        session = get_session()
        v = Vacancy(title='Software Engineer', company='ABC Corp',
                    location='Lalitpur', salary_min=60000.0,
                    salary_max=100000.0, processed=True)

        _, fields = _calculate_similarity(d, v)
        session.close()

        assert fields['weighted_title'] == pytest.approx(1.0 * WEIGHT_TITLE)
        assert fields['weighted_company'] == pytest.approx(1.0 * WEIGHT_COMPANY)
        assert fields['weighted_location'] == pytest.approx(1.0 * WEIGHT_LOCATION)
        assert fields['weighted_salary'] == pytest.approx(1.0 * WEIGHT_SALARY)
        total = (
            fields['weighted_title'] + fields['weighted_company']
            + fields['weighted_location'] + fields['weighted_salary']
        )
        assert total == pytest.approx(1.0)


class TestDuplicateDetector:
    def test_no_candidates_returns_not_duplicate(self, detector):
        details = JobDetails(title='Software Engineer', company='Tech Co')
        result = detector.detect(details)
        assert result.is_duplicate is False
        assert result.similarity_score == 0.0
        assert result.matched_vacancy_id is None

    def test_detect_duplicate_exact_match(self, detector):
        create_processed_vacancy(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
            salary_min=120000.0, salary_max=180000.0,
        )

        details = JobDetails(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
            salary_min=120000.0, salary_max=180000.0,
        )

        result = detector.detect(details)
        assert result.is_duplicate is True
        assert result.similarity_score >= 0.85

    def test_detect_duplicate_fuzzy_match(self, detector):
        create_processed_vacancy(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
        )

        details = JobDetails(
            title='Sr Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, California',
            salary_min=120000.0, salary_max=180000.0,
        )

        result = detector.detect(details)
        assert result.is_duplicate is False
        assert result.matched_vacancy_id is not None

    def test_different_jobs_not_duplicate(self, detector):
        create_processed_vacancy(
            title='Senior Python Developer',
            company='Tech Company Inc.',
        )

        details = JobDetails(
            title='Junior Plumber',
            company='Fix It Co.',
            location='Pokhara',
        )

        result = detector.detect(details)
        assert result.is_duplicate is False
        assert result.similarity_score < 0.5

    def test_detect_with_vacancy_id_skips_self(self, detector):
        vid = create_processed_vacancy(
            title='Unique Job Title XYZ',
            company='Unique Co',
        )

        details = JobDetails(
            title='Unique Job Title XYZ',
            company='Unique Co',
        )

        result = detector.detect(details, vacancy_id=vid)
        assert result.is_duplicate is False

    def test_detect_updates_db(self, detector):
        existing_id = create_processed_vacancy(
            title='Python Developer',
            company='Tech Corp',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )

        new_id = create_processed_vacancy(
            title='Python Developer', company='Tech Corp',
            location='Kathmandu', salary_min=50000.0,
            salary_max=80000.0, processed=False,
        )

        details = JobDetails(
            title='Python Developer', company='Tech Corp',
            location='Kathmandu', salary_min=50000.0,
            salary_max=80000.0,
        )

        result = detector.detect(details, vacancy_id=new_id)
        assert result.is_duplicate is True
        assert result.matched_vacancy_id == existing_id

        session = get_session()
        v = session.query(Vacancy).filter(Vacancy.id == new_id).first()
        assert v.is_duplicate is True
        assert v.duplicate_of == existing_id
        session.close()

    def test_custom_threshold(self, detector):
        create_processed_vacancy(
            title='Senior Python Programmer',
            company='Tech Inc',
        )

        details = JobDetails(
            title='Senior Python Programmer',
            company='Tech Inc',
        )

        low = DuplicateDetector(similarity_threshold=0.5)
        result = low.detect(details)
        assert result.is_duplicate is True

        high = DuplicateDetector(similarity_threshold=0.99)
        result = high.detect(details)
        assert result.is_duplicate is False

    def test_field_scores_in_result(self, detector):
        create_processed_vacancy(
            title='Software Engineer',
            company='ABC Corp',
            location='Lalitpur',
            salary_min=60000.0, salary_max=100000.0,
        )

        details = JobDetails(
            title='Software Engineer',
            company='ABC Corp',
            location='Lalitpur',
            salary_min=60000.0, salary_max=100000.0,
        )

        result = detector.detect(details)
        assert 'title' in result.field_scores
        assert 'company' in result.field_scores
        assert 'location' in result.field_scores
        assert 'salary' in result.field_scores
        assert result.field_scores['title'] == 1.0
        assert result.field_scores['company'] == 1.0

    def test_company_similarity_high_weight(self, detector):
        create_processed_vacancy(
            title='Python Developer',
            company='Google',
            location='Kathmandu',
        )

        details = JobDetails(
            title='Frontend Developer',
            company='Google',
            location='Kathmandu',
        )

        result = detector.detect(details)
        assert result.similarity_score > 0.5

    def test_detect_multiple_candidates_best_wins(self, detector):
        create_processed_vacancy(
            title='Random Job', company='Unknown',
        )
        best_id = create_processed_vacancy(
            title='Target Position', company='Target Co',
            location='Kathmandu',
        )

        details = JobDetails(
            title='Target Position', company='Target Co',
            location='Kathmandu',
        )

        result = detector.detect(details)
        assert result.matched_vacancy_id == best_id


class TestDetectBatch:
    def test_batch_returns_correct_count(self, detector):
        create_processed_vacancy(title='Dev', company='C')

        jobs = [
            JobDetails(title='Dev', company='C'),
            JobDetails(title='Designer', company='D'),
        ]

        results = detector.detect_batch(jobs)
        assert len(results) == 2

    def test_batch_with_vacancy_ids(self, detector):
        existing_id = create_processed_vacancy(
            title='Same Job', company='Same Co',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )
        new_id = create_processed_vacancy(
            title='Same Job', company='Same Co',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
            processed=False,
        )

        jobs = [JobDetails(
            title='Same Job', company='Same Co',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )]
        results = detector.detect_batch(jobs, vacancy_ids=[new_id])
        assert len(results) == 1
        assert results[0].is_duplicate is True
        assert results[0].matched_vacancy_id == existing_id
