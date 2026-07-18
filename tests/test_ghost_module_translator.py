import pytest
from parser.models import JobDetails
from ghost_module.translator import (
    translate_vacancy, translateVacancy, TranslationResult,
    SUPPORTED_LANGUAGES, LANGUAGE_LABELS,
)


def make_jd(**overrides) -> JobDetails:
    defaults = dict(
        title='Senior Web Developer',
        company='TechCorp',
        location='Kathmandu',
        salary_min=50000,
        salary_max=80000,
        job_type='full_time',
        experience_level='senior',
        requirements=['HTML', 'CSS', 'JavaScript'],
        benefits=['Health Insurance', 'Remote Work'],
    )
    defaults.update(overrides)
    return JobDetails(**defaults)


class TestCamelCaseAlias:
    def test_alias(self):
        assert translateVacancy is translate_vacancy


class TestSupportedLanguages:
    def test_english_supported(self):
        r = translate_vacancy(make_jd(), 'english')
        assert r.language == 'english'

    def test_nepali_supported(self):
        r = translate_vacancy(make_jd(), 'nepali')
        assert r.language == 'nepali'

    def test_hindi_supported(self):
        r = translate_vacancy(make_jd(), 'hindi')
        assert r.language == 'hindi'

    def test_case_insensitive(self):
        r = translate_vacancy(make_jd(), 'Nepali')
        assert r.language == 'nepali'

    def test_invalid_language_raises(self):
        with pytest.raises(ValueError):
            translate_vacancy(make_jd(), 'french')

    def test_language_label(self):
        r_en = translate_vacancy(make_jd(), 'english')
        assert r_en.language_label == 'English'
        r_ne = translate_vacancy(make_jd(), 'nepali')
        assert r_ne.language_label == 'नेपाली'
        r_hi = translate_vacancy(make_jd(), 'hindi')
        assert r_hi.language_label == 'हिन्दी'


class TestEnglishTranslation:
    def test_returns_translationresult(self):
        r = translate_vacancy(make_jd(), 'english')
        assert isinstance(r, TranslationResult)

    def test_fields_unchanged(self):
        r = translate_vacancy(make_jd(), 'english')
        assert r.title == 'Senior Web Developer'
        assert r.company == 'TechCorp'
        assert r.location == 'Kathmandu'
        assert '50,000' in r.salary
        assert '80,000' in r.salary
        assert r.job_type == 'Full Time'
        assert r.experience_level == 'Senior'
        assert r.requirements == ['HTML', 'CSS', 'JavaScript']
        assert r.benefits == ['Health Insurance', 'Remote Work']

    def test_empty_fields(self):
        r = translate_vacancy(JobDetails(), 'english')
        assert r.title == ''
        assert r.company == ''
        assert r.location == ''
        assert r.requirements == []


class TestNepaliTranslation:
    def test_title_translated(self):
        r = translate_vacancy(make_jd(title='Senior Developer'), 'nepali')
        assert 'Senior' not in r.title or r.title != 'Senior Developer'

    def test_common_job_type_translated(self):
        r = translate_vacancy(make_jd(job_type='full_time'), 'nepali')
        assert r.job_type == 'पूर्णकालीन'

    def test_part_time_translated(self):
        r = translate_vacancy(make_jd(job_type='part_time'), 'nepali')
        assert r.job_type == 'अंशकालीन'

    def test_experience_translated(self):
        r = translate_vacancy(make_jd(experience_level='senior'), 'nepali')
        assert r.experience_level == 'वरिष्ठ'

    def test_entry_level_translated(self):
        r = translate_vacancy(make_jd(experience_level='entry'), 'nepali')
        assert r.experience_level == 'प्रवेश स्तर'

    def test_requirements_translated(self):
        r = translate_vacancy(make_jd(requirements=['Communication', 'Team']), 'nepali')
        assert any('संचार' in req or 'टोली' in req for req in r.requirements)

    def test_salary_uses_ru(self):
        r = translate_vacancy(make_jd(job_type='monthly'), 'nepali')
        assert 'रु' in r.salary

    def test_location_known_words_translate(self):
        r = translate_vacancy(make_jd(location='Remote Office'), 'nepali')
        assert any(w in r.location for w in ['रिमोट', 'अफिस'])

    def test_unknown_words_unchanged(self):
        r = translate_vacancy(make_jd(title='React Developer'), 'nepali')
        assert 'React' in r.title


class TestHindiTranslation:
    def test_job_type_translated(self):
        r = translate_vacancy(make_jd(job_type='full_time'), 'hindi')
        assert r.job_type == 'पूर्णकालिक'

    def test_experience_translated(self):
        r = translate_vacancy(make_jd(experience_level='senior'), 'hindi')
        assert r.experience_level == 'वरिष्ठ'

    def test_requirements_translated(self):
        r = translate_vacancy(make_jd(requirements=['Communication', 'Management']), 'hindi')
        assert any('संचार' in req or 'प्रबंधन' in req for req in r.requirements)

    def test_unknown_words_unchanged(self):
        r = translate_vacancy(make_jd(title='Full Stack Engineer'), 'hindi')
        assert 'Full' in r.title and 'Stack' in r.title


class TestTranslationResultStructure:
    def test_has_all_expected_fields(self):
        r = translate_vacancy(make_jd(), 'nepali')
        assert hasattr(r, 'language')
        assert hasattr(r, 'language_label')
        assert hasattr(r, 'title')
        assert hasattr(r, 'company')
        assert hasattr(r, 'description')
        assert hasattr(r, 'location')
        assert hasattr(r, 'salary')
        assert hasattr(r, 'job_type')
        assert hasattr(r, 'experience_level')
        assert hasattr(r, 'requirements')
        assert hasattr(r, 'benefits')
        assert hasattr(r, 'raw')

    def test_requirements_is_list(self):
        r = translate_vacancy(make_jd(), 'hindi')
        assert isinstance(r.requirements, list)

    def test_benefits_is_list(self):
        r = translate_vacancy(make_jd(), 'nepali')
        assert isinstance(r.benefits, list)

    def test_salary_format_range(self):
        r = translate_vacancy(make_jd(salary_min=30000, salary_max=60000), 'hindi')
        assert '30,000' in r.salary
        assert '60,000' in r.salary

    def test_salary_single_value(self):
        r = translate_vacancy(make_jd(salary_min=75000, salary_max=75000), 'hindi')
        assert '75,000' in r.salary


class TestEdgeCases:
    def test_empty_job_details(self):
        r = translate_vacancy(JobDetails(), 'nepali')
        assert r.title == ''
        assert r.company == ''
        assert r.requirements == []
        assert r.benefits == []

    def test_partial_fields(self):
        r = translate_vacancy(JobDetails(title='Developer'), 'hindi')
        assert r.title != ''
        assert r.company == ''

    def test_multiple_requirements_translated(self):
        r = translate_vacancy(
            make_jd(requirements=['Good communication', 'Team work', 'Management skill']),
            'hindi',
        )
        for req in r.requirements:
            assert req

    def test_language_code_variants(self):
        r = translate_vacancy(make_jd(), 'nepali')
        assert r.language == 'nepali'

    def test_word_with_punctuation(self):
        r = translate_vacancy(make_jd(title='Kubernetes, Docker!'), 'nepali')
        assert 'Kubernetes' in r.title
        assert 'Docker' in r.title
