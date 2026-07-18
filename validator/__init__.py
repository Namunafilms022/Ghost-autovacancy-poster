from __future__ import annotations

from typing import Optional

from .models import FieldValidation, ExtractionResult, ConfidenceLevel
from .field_validators import (
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
from .confidence import calculate_overall, DEFAULT_THRESHOLD


def validate_extraction(job_details, threshold: float = DEFAULT_THRESHOLD) -> ExtractionResult:
    fields = {
        'company': validate_company(getattr(job_details, 'company', None)),
        'position': validate_position(getattr(job_details, 'title', None)),
        'salary': validate_salary(
            getattr(job_details, 'salary_min', None),
            getattr(job_details, 'salary_max', None),
            getattr(job_details, 'raw_message', None),
        ),
        'location': validate_location(getattr(job_details, 'location', None)),
        'requirements': validate_requirements(getattr(job_details, 'requirements', [])),
        'benefits': validate_benefits(getattr(job_details, 'benefits', [])),
        'deadline': validate_deadline(getattr(job_details, 'raw_message', None)),
        'contact': validate_contact(getattr(job_details, 'raw_message', None)),
        'email': validate_email(getattr(job_details, 'contact_email', None)),
        'phone': validate_phone(getattr(job_details, 'contact_phone', None)),
        'website': validate_website(None),
    }

    return calculate_overall(fields, threshold)


__all__ = [
    'validate_extraction',
    'FieldValidation',
    'ExtractionResult',
    'ConfidenceLevel',
    'validate_company',
    'validate_position',
    'validate_salary',
    'validate_location',
    'validate_requirements',
    'validate_benefits',
    'validate_deadline',
    'validate_contact',
    'validate_email',
    'validate_phone',
    'validate_website',
    'calculate_overall',
    'DEFAULT_THRESHOLD',
]
