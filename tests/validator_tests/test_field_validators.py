import sys
sys.path.insert(0, '/root/project')

import pytest
from validator.field_validators import (
    validate_company,
    validate_position,
    validate_salary,
    validate_location,
    validate_requirements,
    validate_benefits,
    validate_deadline,
    validate_contact,
    validate_email,
    validate_phone,
    validate_website,
)
from validator.models import ConfidenceLevel


class TestValidateCompany:
    def test_valid_company(self):
        r = validate_company('Tech Company Inc.')
        assert r.confidence >= 0.9
        assert r.passed

    def test_short_name(self):
        r = validate_company('A')
        assert r.confidence < 0.5
        assert not r.passed

    def test_lowercase(self):
        r = validate_company('tech company')
        assert 0.4 <= r.confidence <= 0.6

    def test_llc(self):
        r = validate_company('Acme Corp.')
        assert r.confidence >= 0.9

    def test_missing(self):
        r = validate_company(None)
        assert r.is_missing
        assert r.confidence == 0.0


class TestValidatePosition:
    def test_senior_role(self):
        r = validate_position('Senior Python Developer')
        assert r.confidence >= 0.9

    def test_short_title(self):
        r = validate_position('Job')
        assert r.confidence < 0.5

    def test_generic_title(self):
        r = validate_position('hiring')
        assert r.confidence < 0.5

    def test_engineer(self):
        r = validate_position('Software Engineer')
        assert r.confidence >= 0.8

    def test_missing(self):
        r = validate_position(None)
        assert r.is_missing


class TestValidateSalary:
    def test_valid_range(self):
        r = validate_salary(50000, 80000)
        assert r.confidence >= 0.9
        assert r.passed

    def test_negative(self):
        r = validate_salary(-100, 100)
        assert r.confidence < 0.5

    def test_min_greater_than_max(self):
        r = validate_salary(100, 50)
        assert r.confidence < 0.5

    def test_wide_range(self):
        r = validate_salary(10000, 200000)
        assert r.confidence < 0.7

    def test_only_min(self):
        r = validate_salary(60000, None)
        assert 0.5 <= r.confidence <= 0.7

    def test_missing(self):
        r = validate_salary(None, None)
        assert r.is_missing


class TestValidateLocation:
    def test_city_state(self):
        r = validate_location('San Francisco, CA')
        assert r.confidence >= 0.8

    def test_remote(self):
        r = validate_location('Remote')
        assert r.confidence >= 0.8

    def test_short(self):
        r = validate_location('X')
        assert not r.passed

    def test_missing(self):
        r = validate_location(None)
        assert r.is_missing


class TestValidateRequirements:
    def test_multiple_items(self):
        r = validate_requirements(['Python', 'Django', 'PostgreSQL', 'Docker Compose', 'AWS'])
        assert r.confidence >= 0.8

    def test_single_item(self):
        r = validate_requirements(['Python'])
        assert r.confidence < 0.5

    def test_empty(self):
        r = validate_requirements([])
        assert r.is_missing

    def test_brief_items(self):
        r = validate_requirements(['A', 'B', 'C', 'D'])
        assert r.confidence < 0.7


class TestValidateBenefits:
    def test_multiple(self):
        r = validate_benefits(['Health', '401k', 'Remote'])
        assert r.confidence >= 0.8

    def test_empty(self):
        r = validate_benefits([])
        assert r.confidence < 0.5


class TestValidateDeadline:
    def test_found(self):
        r = validate_deadline('Apply by 2024-12-31')
        assert r.confidence >= 0.8

    def test_not_mentioned(self):
        r = validate_deadline('No date mentioned in this text')
        assert r.confidence < 0.5

    def test_missing(self):
        r = validate_deadline(None)
        assert r.is_missing


class TestValidateContact:
    def test_with_email_phone(self):
        r = validate_contact('Contact: john@test.com, +1-555-123-4567')
        assert r.confidence >= 0.9

    def test_only_email(self):
        r = validate_contact('Contact: john@test.com')
        assert r.confidence >= 0.8

    def test_not_found(self):
        r = validate_contact('No contact info')
        assert r.confidence < 0.5

    def test_missing(self):
        r = validate_contact(None)
        assert r.is_missing


class TestValidateEmail:
    def test_valid(self):
        r = validate_email('john@company.com')
        assert r.confidence >= 0.9

    def test_personal_domain(self):
        r = validate_email('john@gmail.com')
        assert r.confidence < 0.8

    def test_invalid_format(self):
        r = validate_email('not-an-email')
        assert not r.passed

    def test_missing(self):
        r = validate_email(None)
        assert r.is_missing


class TestValidatePhone:
    def test_valid_10_digits(self):
        r = validate_phone('+1 (555) 123-4567')
        assert r.confidence >= 0.9

    def test_too_short(self):
        r = validate_phone('123')
        assert not r.passed

    def test_missing_area_code(self):
        r = validate_phone('123-4567')
        assert r.confidence < 0.7

    def test_missing(self):
        r = validate_phone(None)
        assert r.is_missing


class TestValidateWebsite:
    def test_valid_url(self):
        r = validate_website('https://company.com')
        assert r.confidence >= 0.9

    def test_invalid_url(self):
        r = validate_website('just text')
        assert r.confidence < 0.5

    def test_missing(self):
        r = validate_website(None)
        assert r.is_missing
