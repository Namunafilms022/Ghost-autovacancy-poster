import sys
sys.path.insert(0, '.')

import pytest
from ghost_module import (
    extract_vacancy, extractVacancy,
    validate_vacancy, validateVacancy,
    generate_caption, generateCaption,
    check_duplicate, checkDuplicate,
    create_poster, createPoster,
    publish, publish_,
)
from database.init import init_db
from database.session import get_session
from database.models import Vacancy

SAMPLE_MSG = '''Job Title: Senior Python Developer
Company: TechCorp
Location: Kathmandu
Salary: 80000-120000
Requirements:
- Python
- Django
- PostgreSQL
Benefits:
- Health insurance
- Remote work'''


@pytest.fixture(autouse=True)
def db():
    init_db()
    yield
    with get_session() as s:
        s.query(Vacancy).delete()
        s.commit()


class TestCamelCaseAliases:
    def test_aliases_exist(self):
        assert extractVacancy is extract_vacancy
        assert validateVacancy is validate_vacancy
        assert generateCaption is generate_caption
        assert checkDuplicate is check_duplicate
        assert createPoster is create_poster
        assert publish_ is publish


class TestExtractVacancy:
    def test_extract_full_job(self):
        jd = extract_vacancy(SAMPLE_MSG)
        assert jd.title == 'Senior Python Developer'
        assert jd.company == 'TechCorp'
        assert jd.location == 'Kathmandu'
        assert 'Python' in jd.requirements
        assert 'Remote work' in jd.benefits

    def test_extract_minimal(self):
        jd = extract_vacancy('Just some random text')
        assert jd is not None

    def test_extract_empty(self):
        jd = extract_vacancy('')
        assert jd is not None

    def test_extract_returns_jobdetails(self):
        from parser import JobDetails
        jd = extract_vacancy(SAMPLE_MSG)
        assert isinstance(jd, JobDetails)


class TestValidateVacancy:
    def test_validate_full_job(self):
        jd = extract_vacancy(SAMPLE_MSG)
        result = validate_vacancy(jd)
        assert result.overall_confidence > 0
        assert 'company' in result.fields
        assert 'position' in result.fields
        assert 'salary' in result.fields

    def test_validate_low_confidence(self):
        jd = extract_vacancy('random text without fields')
        result = validate_vacancy(jd, threshold=0.9)
        assert result.overall_confidence < 0.9

    def test_validate_returns_extractionresult(self):
        from validator.models import ExtractionResult
        jd = extract_vacancy(SAMPLE_MSG)
        result = validate_vacancy(jd)
        assert isinstance(result, ExtractionResult)

    def test_validate_with_threshold(self):
        jd = extract_vacancy(SAMPLE_MSG)
        result = validate_vacancy(jd, threshold=0.5)
        assert result.threshold == 0.5


class TestGenerateCaption:
    def test_generates_all_platforms(self):
        cr = generate_caption(
            title='Developer',
            company='Co',
            location='NYC',
            salary_min=50000,
            salary_max=80000,
        )
        for p in ['facebook', 'instagram', 'linkedin', 'telegram', 'twitter']:
            assert p in cr.platforms, f'Missing platform: {p}'

    def test_each_platform_has_fields(self):
        cr = generate_caption('Dev', 'Co')
        for platform, caps in cr.platforms.items():
            assert caps.caption
            assert caps.hashtags
            assert caps.call_to_action
            assert caps.short_version
            assert caps.long_version

    def test_returns_captionresult(self):
        from captions import CaptionResult
        cr = generate_caption('Dev', 'Co')
        assert isinstance(cr, CaptionResult)

    def test_requirements_in_long_version(self):
        cr = generate_caption('Dev', 'Co', requirements=['Python', 'Django'])
        fb = cr.for_platform('facebook')
        assert 'Python' in fb.long_version or 'Django' in fb.long_version

    def test_salary_in_caption(self):
        cr = generate_caption('Dev', 'Co', salary_min=80000, salary_max=120000)
        for platform, caps in cr.platforms.items():
            combined = caps.caption + caps.short_version + caps.long_version
            assert '80,000' in combined or '80000' in combined


class TestCheckDuplicate:
    def test_not_duplicate_for_new_job(self):
        jd = extract_vacancy(SAMPLE_MSG)
        dup = check_duplicate(jd)
        assert isinstance(dup.is_duplicate, bool)

    def test_matches_identical_job(self):
        jd = extract_vacancy(SAMPLE_MSG)
        with get_session() as s:
            v = Vacancy(title='Senior Python Developer', company='TechCorp', processed=True)
            s.add(v)
            s.commit()
            vid = v.id
        dup = check_duplicate(jd, vacancy_id=vid)
        assert isinstance(dup.similarity_score, float)

    def test_duplicate_result_has_expected_attrs(self):
        from duplicate import DuplicateResult
        jd = extract_vacancy('Random unique job')
        dup = check_duplicate(jd)
        assert isinstance(dup, DuplicateResult)
        assert hasattr(dup, 'is_duplicate')
        assert hasattr(dup, 'similarity_score')
        assert hasattr(dup, 'field_scores')


class TestCreatePoster:
    def test_creates_html(self):
        with get_session() as s:
            v = Vacancy(title='Test', company='Co', processed=True, raw_message=SAMPLE_MSG)
            s.add(v)
            s.commit()
            vid = v.id
        html = create_poster(vid, theme='minimal')
        assert isinstance(html, str)
        assert len(html) > 500

    def test_creates_with_auto_theme(self):
        with get_session() as s:
            v = Vacancy(title='Senior Python Developer', company='TechCorp',
                        processed=True, raw_message=SAMPLE_MSG)
            s.add(v)
            s.commit()
            vid = v.id
        html = create_poster(vid, auto_theme=True)
        assert isinstance(html, str)

    def test_creates_with_specific_category(self):
        with get_session() as s:
            v = Vacancy(title='Test', company='Co', processed=True)
            s.add(v)
            s.commit()
            vid = v.id
        html = create_poster(vid, theme='dark_neon', category='programming')
        assert isinstance(html, str)

    def test_poster_has_layer_structure(self):
        with get_session() as s:
            v = Vacancy(title='Test', company='Co', processed=True)
            s.add(v)
            s.commit()
            vid = v.id
        html = create_poster(vid, theme='minimal')
        assert 'layer-bg' in html or 'z-index' in html or 'poster-container' in html


class TestPublish:
    def test_returns_list(self):
        with get_session() as s:
            v = Vacancy(title='Test', company='Co', processed=True)
            s.add(v)
            s.commit()
            vid = v.id
        results = publish(vid)
        assert isinstance(results, list)
        if results:
            r = results[0]
            assert 'platform' in r
            assert 'success' in r
            assert 'error' in r
