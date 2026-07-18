import pytest

from duplicate import DuplicateDetector, DuplicateResult
from duplicate.detector import (
    _text_similarity, _salary_overlap, _list_similarity,
    _calculate_similarity, _generate_reason, _extract_section_items,
    _get_req_benefits, _build_merge_suggestion,
    WEIGHT_TITLE, WEIGHT_COMPANY, WEIGHT_LOCATION, WEIGHT_SALARY,
    WEIGHT_DESCRIPTION, WEIGHT_REQUIREMENTS, WEIGHT_BENEFITS,
)
from parser import JobDetails
from database.init import init_db, drop_db
from database.session import get_session
from database.models import Vacancy


def create_vacancy(title='Engineer', company='Corp',
                   location='Kathmandu', salary_min=50000.0,
                   salary_max=80000.0, processed=True,
                   is_duplicate=False,
                   raw_message='', description=None,
                   job_type=None, experience_level=None) -> int:
    session = get_session()
    v = Vacancy(
        title=title, company=company, location=location,
        salary_min=salary_min, salary_max=salary_max,
        processed=processed, is_duplicate=is_duplicate,
        raw_message=raw_message, description=description,
        job_type=job_type, experience_level=experience_level,
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
    return DuplicateDetector(similarity_threshold=0.75)


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


class TestListSimilarity:
    def test_identical(self):
        assert _list_similarity(['Python', 'Django'], ['Python', 'Django']) == 1.0

    def test_partial(self):
        s = _list_similarity(['Python', 'Django', 'SQL'], ['Python', 'React'])
        assert s == 0.25

    def test_no_overlap(self):
        assert _list_similarity(['Python'], ['Java']) == 0.0

    def test_empty(self):
        assert _list_similarity([], ['Python']) == 0.0
        assert _list_similarity(['Python'], []) == 0.0
        assert _list_similarity([], []) == 0.0

    def test_case_insensitive(self):
        s = _list_similarity(['Python'], ['python'])
        assert s == 1.0

    def test_whitespace_insensitive(self):
        s = _list_similarity(['  Python  '], ['python'])
        assert s == 1.0


class TestExtractSectionItems:
    def test_extract_requirements(self):
        text = '*Requirements*\n- Python\n- Django\n\n*Benefits*\n- Health insurance'
        items = _extract_section_items(text, [
            'requirements', 'requirement', 'qualifications'])
        assert 'Python' in items
        assert 'Django' in items

    def test_extract_benefits(self):
        text = '*Requirements*\n- Python\n\n*Benefits*\n- Health insurance\n- Free lunch'
        items = _extract_section_items(text, [
            'benefits', 'benefit', 'what we offer'])
        assert 'Health insurance' in items
        assert 'Free lunch' in items

    def test_alternate_header(self):
        text = 'Qualifications:\n- Python\n- SQL'
        items = _extract_section_items(text, [
            'requirements', 'qualifications'])
        assert 'Python' in items
        assert 'SQL' in items

    def test_no_section(self):
        assert _extract_section_items('Just some text about Python and Django', [
            'requirements']) == []

    def test_none_text(self):
        assert _extract_section_items(None, ['requirements']) == []

    def test_empty_text(self):
        assert _extract_section_items('', ['requirements']) == []


class TestGetReqBenefits:
    def test_returns_both(self):
        text = '*Requirements*\n- Python\n\n*Benefits*\n- Insurance'
        reqs, ben = _get_req_benefits(text)
        assert 'Python' in reqs
        assert 'Insurance' in ben

    def test_only_requirements(self):
        text = '*Requirements*\n- Python\n- Django'
        reqs, ben = _get_req_benefits(text)
        assert 'Python' in reqs
        assert ben == []

    def test_only_benefits(self):
        text = '*Benefits*\n- Insurance'
        reqs, ben = _get_req_benefits(text)
        assert reqs == []
        assert 'Insurance' in ben

    def test_none(self):
        assert _get_req_benefits(None) == ([], [])

    def test_empty(self):
        assert _get_req_benefits('') == ([], [])


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

    def test_weight_normalization(self):
        d = JobDetails(title='Software Engineer', company='ABC Corp',
                       location='Lalitpur', salary_min=60000.0,
                       salary_max=100000.0)
        session = get_session()
        v = Vacancy(title='Software Engineer', company='ABC Corp',
                    location='Lalitpur', salary_min=60000.0,
                    salary_max=100000.0, processed=True)

        _, fields = _calculate_similarity(d, v)
        session.close()

        active = (WEIGHT_TITLE + WEIGHT_COMPANY + WEIGHT_LOCATION
                  + WEIGHT_SALARY)
        assert fields['weighted_title'] == pytest.approx(1.0 * WEIGHT_TITLE)
        total = sum(fields[k] for k in fields if k.startswith('weighted_'))
        assert total == pytest.approx(active)

    def test_description_similarity(self):
        d = JobDetails(title='Dev', company='Co',
                       description='Looking for a Python developer with 5 years experience')
        session = get_session()
        v = Vacancy(title='Dev', company='Co',
                    description='Looking for a Python developer with 5 years experience',
                    processed=True)
        score, fields = _calculate_similarity(d, v)
        session.close()
        assert fields['description'] == 1.0

    def test_requirements_similarity(self):
        d = JobDetails(title='Dev', company='Co',
                       requirements=['Python', 'Django', 'SQL'])
        session = get_session()
        v = Vacancy(title='Dev', company='Co',
                    raw_message='*Requirements*\n- Python\n- Django\n\n*Benefits*\n- Insurance',
                    processed=True)
        score, fields = _calculate_similarity(d, v)
        session.close()
        assert fields['requirements'] > 0.5

    def test_benefits_similarity(self):
        d = JobDetails(title='Dev', company='Co',
                       benefits=['Health insurance', 'Free lunch'])
        session = get_session()
        v = Vacancy(title='Dev', company='Co',
                    raw_message='*Benefits*\n- Health insurance\n- Free lunch',
                    processed=True)
        score, fields = _calculate_similarity(d, v)
        session.close()
        assert fields['benefits'] == 1.0

    def test_new_fields_in_field_scores(self):
        d = JobDetails(title='Dev', company='Co')
        session = get_session()
        v = Vacancy(title='Dev', company='Co', processed=True)
        _, fields = _calculate_similarity(d, v)
        session.close()
        assert 'description' in fields
        assert 'requirements' in fields
        assert 'benefits' in fields
        assert 'weighted_description' in fields
        assert 'weighted_requirements' in fields
        assert 'weighted_benefits' in fields


class TestGenerateReason:
    def test_same_company_position(self):
        r = _generate_reason(0.9, 0.9, 0, 0, 0, 0, 0, 0.92)
        assert 'Same company and position' in r
        assert 'score: 0.92' in r

    def test_title_match(self):
        r = _generate_reason(0.85, 0.5, 0, 0, 0, 0, 0, 0.80)
        assert 'Matching job title' in r

    def test_company_match(self):
        r = _generate_reason(0.5, 0.9, 0, 0, 0, 0, 0, 0.60)
        assert 'Same company' in r

    def test_requirements_overlap(self):
        r = _generate_reason(0, 0, 0, 0, 0, 0.7, 0, 0.70)
        assert 'Overlapping requirements' in r

    def test_benefits_match(self):
        r = _generate_reason(0, 0, 0, 0, 0, 0, 0.8, 0.50)
        assert 'Same benefits' in r

    def test_low_scores_fallback(self):
        r = _generate_reason(0.4, 0.3, 0.2, 0.1, 0.3, 0.0, 0.0, 0.30)
        assert 'similarity' in r.lower()


class TestDuplicateDetector:
    def test_no_candidates_returns_not_duplicate(self, detector):
        details = JobDetails(title='Software Engineer', company='Tech Co')
        result = detector.detect(details)
        assert result.is_duplicate is False
        assert result.similarity_score == 0.0
        assert result.matched_vacancy_id is None

    def test_detect_duplicate_exact_match(self, detector):
        create_vacancy(
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
        assert result.similarity_score >= 0.75

    def test_detect_duplicate_fuzzy_match(self, detector):
        create_vacancy(
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
        assert result.similarity_score > 0.5
        assert result.matched_vacancy_id is not None

    def test_different_jobs_not_duplicate(self, detector):
        create_vacancy(
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
        vid = create_vacancy(
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
        existing_id = create_vacancy(
            title='Python Developer',
            company='Tech Corp',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )

        new_id = create_vacancy(
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
        create_vacancy(
            title='Senior Python Programmer',
            company='Tech Inc',
            location='Kathmandu',
        )

        details = JobDetails(
            title='Senior Python Programmer',
            company='Tech Inc',
            location='Lalitpur',
        )

        low = DuplicateDetector(similarity_threshold=0.5)
        result = low.detect(details)
        assert result.is_duplicate is True

        high = DuplicateDetector(similarity_threshold=0.99)
        result = high.detect(details)
        assert result.is_duplicate is False

    def test_field_scores_in_result(self, detector):
        create_vacancy(
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
        for f in ('title', 'company', 'location', 'salary',
                  'description', 'requirements', 'benefits'):
            assert f in result.field_scores
        assert result.field_scores['title'] == 1.0
        assert result.field_scores['company'] == 1.0

    def test_reason_in_result(self, detector):
        create_vacancy(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
        )

        details = JobDetails(
            title='Senior Python Developer',
            company='Tech Company Inc.',
            location='San Francisco, CA',
        )

        result = detector.detect(details)
        assert result.reason is not None
        assert 'score:' in result.reason

    def test_merge_suggestion_in_result_when_duplicate(self, detector):
        create_vacancy(
            title='Python Developer',
            company='Tech Corp',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
            raw_message='*Benefits*\n- Health insurance\n- Free lunch',
        )

        details = JobDetails(
            title='Python Developer',
            company='Tech Corp',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )

        result = detector.detect(details)
        assert result.merge_suggestion is not None
        assert isinstance(result.merge_suggestion, dict)
        assert 'benefits' in result.merge_suggestion

    def test_company_similarity_high_weight(self, detector):
        create_vacancy(
            title='Python Developer',
            company='Google',
            location='Kathmandu',
        )

        details = JobDetails(
            title='Frontend Developer',
            company='Google',
            location='Kathmandu',
            salary_min=120000.0, salary_max=180000.0,
        )

        result = detector.detect(details)
        assert result.similarity_score > 0.3

    def test_matches_based_on_requirements(self, detector):
        create_vacancy(
            title='Dev', company='Co',
            raw_message='*Requirements*\n- Python\n- Django\n- SQL\n- React',
        )

        details = JobDetails(
            title='Dev', company='Co',
            requirements=['Python', 'Django', 'SQL', 'React'],
        )

        result = detector.detect(details)
        assert result.field_scores['requirements'] > 0.9

    def test_requirements_and_benefits_boost_score(self, detector):
        create_vacancy(
            title='Developer', company='Tech Co',
            raw_message='*Requirements*\n- Python\n- Django\n\n*Benefits*\n- Health insurance\n- Remote work',
        )

        details = JobDetails(
            title='Developer', company='Tech Co',
            requirements=['Python', 'Django'],
            benefits=['Health insurance', 'Remote work'],
        )

        result = detector.detect(details)
        assert result.is_duplicate is True

    def test_detect_multiple_candidates_best_wins(self, detector):
        create_vacancy(
            title='Random Job', company='Unknown',
        )
        best_id = create_vacancy(
            title='Target Position', company='Target Co',
            location='Kathmandu',
        )

        details = JobDetails(
            title='Target Position', company='Target Co',
            location='Kathmandu',
        )

        result = detector.detect(details)
        assert result.matched_vacancy_id == best_id

    def test_duplicate_result_has_merge_suggestion(self, detector):
        create_vacancy(
            title='Dev', company='Co',
            raw_message='*Benefits*\n- Insurance',
        )

        details = JobDetails(
            title='Dev', company='Co',
        )

        result = detector.detect(details)
        if result.is_duplicate:
            assert result.merge_suggestion is not None
            assert isinstance(result.merge_suggestion, dict)


class TestDetectBatch:
    def test_batch_returns_correct_count(self, detector):
        create_vacancy(title='Dev', company='C')

        jobs = [
            JobDetails(title='Dev', company='C'),
            JobDetails(title='Designer', company='D'),
        ]

        results = detector.detect_batch(jobs)
        assert len(results) == 2

    def test_batch_with_vacancy_ids(self, detector):
        existing_id = create_vacancy(
            title='Same Job', company='Same Co',
            location='Kathmandu',
            salary_min=50000.0, salary_max=80000.0,
        )
        new_id = create_vacancy(
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


class TestSuggestMerge:
    def test_suggest_merge_returns_dict(self, detector):
        vid1 = create_vacancy(
            title='Python Dev', company='Co',
            salary_min=50000.0, salary_max=80000.0,
        )
        vid2 = create_vacancy(
            title='Python Developer', company='Co',
        )
        suggestions = detector.suggest_merge(vid1, vid2)
        assert isinstance(suggestions, dict)

    def test_suggest_merge_salary_when_one_missing(self, detector):
        vid1 = create_vacancy(
            title='Python Dev', company='Co',
            salary_min=None, salary_max=None,
        )
        vid2 = create_vacancy(
            title='Python Dev', company='Co',
            salary_min=50000.0, salary_max=80000.0,
        )
        suggestions = detector.suggest_merge(vid1, vid2)
        assert 'salary' in suggestions
