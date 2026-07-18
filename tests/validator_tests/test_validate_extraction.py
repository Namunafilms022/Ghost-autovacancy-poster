import sys
sys.path.insert(0, '/root/project')

import pytest
from validator import validate_extraction


class MockJobDetails:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestValidateExtraction:
    def test_complete_job(self):
        details = MockJobDetails(
            title='Senior Python Developer',
            company='Tech Corp Inc.',
            description='We need a Python expert',
            location='San Francisco, CA',
            salary_min=120000,
            salary_max=180000,
            job_type='Full-time',
            experience_level='Senior',
            requirements=['Python', 'Django', 'AWS', 'Docker', 'PostgreSQL'],
            benefits=['Health Insurance', '401k', 'Remote Work'],
            contact_email='hr@techcorp.com',
            contact_phone='+1-555-123-4567',
            raw_message='Join our team! Contact: hr@techcorp.com',
        )
        result = validate_extraction(details, threshold=0.5)
        assert not result.rejected
        assert result.overall_confidence > 0.7
        assert 'company' in result.fields

    def test_minimal_job(self):
        details = MockJobDetails(
            title='Worker',
            company='X',
            description=None,
            location=None,
            salary_min=None,
            salary_max=None,
            job_type=None,
            experience_level=None,
            requirements=[],
            benefits=[],
            contact_email=None,
            contact_phone=None,
            raw_message='hiring',
        )
        result = validate_extraction(details, threshold=0.7)
        assert result.rejected

    def test_missing_fields_tracked(self):
        details = MockJobDetails(
            title='Developer',
            company='Acme',
            description=None,
            location=None,
            salary_min=None,
            salary_max=None,
            job_type=None,
            experience_level=None,
            requirements=[],
            benefits=[],
            contact_email=None,
            contact_phone=None,
            raw_message=None,
        )
        result = validate_extraction(details, threshold=0.5)
        assert len(result.missing_fields) > 0
        assert 'salary' in result.missing_fields
        assert 'location' in result.missing_fields
