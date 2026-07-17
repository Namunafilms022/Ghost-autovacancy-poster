from __future__ import annotations

import re
from enum import Enum
from typing import Optional, List, Tuple

from parser.models import JobDetails
from database.models import Vacancy
from database.session import get_session


class JobType(str, Enum):
    FULL_TIME = 'full_time'
    PART_TIME = 'part_time'
    CONTRACT = 'contract'
    INTERNSHIP = 'internship'
    FREELANCE = 'freelance'


class ExperienceLevel(str, Enum):
    ENTRY = 'entry'
    MID = 'mid'
    SENIOR = 'senior'
    LEAD = 'lead'
    ANY = 'any'


_JOB_TYPE_ALIASES = {
    'full time': JobType.FULL_TIME, 'fulltime': JobType.FULL_TIME,
    'full-time': JobType.FULL_TIME, 'permanent': JobType.FULL_TIME,
    'part time': JobType.PART_TIME, 'parttime': JobType.PART_TIME,
    'part-time': JobType.PART_TIME,
    'contract': JobType.CONTRACT, 'contractual': JobType.CONTRACT,
    'temporary': JobType.CONTRACT,
    'internship': JobType.INTERNSHIP, 'intern': JobType.INTERNSHIP,
    'trainee': JobType.INTERNSHIP,
    'freelance': JobType.FREELANCE, 'freelancer': JobType.FREELANCE,
    'freelancing': JobType.FREELANCE, 'remote': JobType.FREELANCE,
}

_EXPERIENCE_ALIASES = {
    'entry': ExperienceLevel.ENTRY, 'entry level': ExperienceLevel.ENTRY,
    'junior': ExperienceLevel.ENTRY, 'jr': ExperienceLevel.ENTRY,
    'fresher': ExperienceLevel.ENTRY, 'beginner': ExperienceLevel.ENTRY,
    'mid': ExperienceLevel.MID, 'mid level': ExperienceLevel.MID,
    'intermediate': ExperienceLevel.MID,
    'senior': ExperienceLevel.SENIOR, 'sr': ExperienceLevel.SENIOR,
    'senior level': ExperienceLevel.SENIOR, 'experienced': ExperienceLevel.SENIOR,
    'lead': ExperienceLevel.LEAD, 'lead level': ExperienceLevel.LEAD,
    'team lead': ExperienceLevel.LEAD, 'manager': ExperienceLevel.LEAD,
    'any': ExperienceLevel.ANY, 'any level': ExperienceLevel.ANY,
    'all': ExperienceLevel.ANY, 'any experience': ExperienceLevel.ANY,
    'not required': ExperienceLevel.ANY, 'none': ExperienceLevel.ANY,
}

_CURRENCY_RATES = {
    'USD': 135.0,
    'INR': 1.6,
    'EUR': 145.0,
    'GBP': 170.0,
    'AUD': 90.0,
    'CAD': 100.0,
    'NPR': 1.0,
}

_PERIOD_MULTIPLIERS = {
    'yearly': 1.0 / 12.0,
    'annual': 1.0 / 12.0,
    'monthly': 1.0,
    'weekly': 4.33,
    'daily': 22.0,
    'hourly': 176.0,
}


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = ' '.join(value.split())
    return cleaned if cleaned else None


def _clean_list(items: List[str]) -> List[str]:
    return [s.strip() for s in items if s.strip()]


def _find_salary_line(text: str) -> Optional[str]:
    m = re.search(
        r'(?:^|\n)\s*(?:\*)?(?:Salary|Pay|Compensation|Stipend)(?:\*)?\s*[:–-]?\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE | re.MULTILINE
    )
    return m.group(1) if m else None


def _detect_currency(salary_text: str) -> str:
    if '₹' in salary_text:
        return 'INR'
    if '€' in salary_text:
        return 'EUR'
    if '£' in salary_text:
        return 'GBP'
    if '$' in salary_text:
        return 'USD'
    if re.search(r'\blakh\b|\bcrore\b', salary_text, re.IGNORECASE):
        return 'INR'
    return 'NPR'


def _detect_period(salary_text: str) -> str:
    t = salary_text.lower()
    if re.search(r'/year|/yr\b|per year|annually?\b| per annum\b|/pa\b', t):
        return 'yearly'
    if re.search(r'/hour|/hr\b|per hour|hourly', t):
        return 'hourly'
    if re.search(r'/day|per day|daily', t):
        return 'daily'
    if re.search(r'/week|per week|weekly', t):
        return 'weekly'
    if re.search(r'/month|per month|monthly|/mo\b', t):
        return 'monthly'
    return 'monthly'


def _normalize_salary_value(value: float, period: str, currency: str) -> float:
    monthly = value * _PERIOD_MULTIPLIERS.get(period, 1.0)
    rate = _CURRENCY_RATES.get(currency, 1.0)
    return round(monthly * rate, 2)


def _normalize_salary(job_details: JobDetails) -> Tuple[Optional[float], Optional[float]]:
    if job_details.salary_min is None and job_details.salary_max is None:
        return None, None

    raw = job_details.raw_message or ''
    salary_line = _find_salary_line(raw)
    ctx = salary_line or raw

    currency = _detect_currency(ctx)
    period = _detect_period(ctx)

    new_min = None
    new_max = None

    if job_details.salary_min is not None:
        new_min = _normalize_salary_value(job_details.salary_min, period, currency)
    if job_details.salary_max is not None:
        new_max = _normalize_salary_value(job_details.salary_max, period, currency)

    return new_min, new_max


def _normalize_job_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    t = raw.strip().lower().replace('_', ' ')
    for alias, jt in _JOB_TYPE_ALIASES.items():
        if alias in t:
            return jt.value
    return None


def _normalize_experience(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    t = raw.strip().lower().replace('_', ' ')
    for alias, el in _EXPERIENCE_ALIASES.items():
        if alias in t:
            return el.value
    return None


class NormalizedResult:
    def __init__(self, vacancy_id: int, success: bool = True,
                 errors: List[str] = None):
        self.vacancy_id = vacancy_id
        self.success = success
        self.errors = errors or []

    def __repr__(self) -> str:
        return f"<NormalizedResult(vacancy_id={self.vacancy_id}, success={self.success})>"


class Normalizer:
    def normalize(self, job_details: JobDetails, vacancy_id: int) -> NormalizedResult:
        errors = []

        title = _clean_text(job_details.title)
        if not title:
            errors.append("title is required and must not be empty")

        company = _clean_text(job_details.company)
        location = _clean_text(job_details.location)
        description = _clean_text(job_details.description)
        requirements = _clean_list(job_details.requirements)
        benefits = _clean_list(job_details.benefits)
        contact_email = _clean_text(job_details.contact_email)
        contact_phone = _clean_text(job_details.contact_phone)

        salary_min, salary_max = _normalize_salary(job_details)

        job_type = _normalize_job_type(job_details.job_type)
        experience_level = _normalize_experience(job_details.experience_level)

        if errors:
            return NormalizedResult(vacancy_id=vacancy_id, success=False, errors=errors)

        session = get_session()
        try:
            vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if not vacancy:
                return NormalizedResult(
                    vacancy_id=vacancy_id, success=False,
                    errors=[f"Vacancy with id {vacancy_id} not found"]
                )

            vacancy.title = title or 'Untitled'
            vacancy.company = company or 'Unknown'
            vacancy.location = location
            vacancy.description = description or (job_details.raw_message or '')[:500]
            vacancy.salary_min = salary_min
            vacancy.salary_max = salary_max
            vacancy.job_type = job_type
            vacancy.experience_level = experience_level
            vacancy.processed = True

            session.commit()
            return NormalizedResult(vacancy_id=vacancy_id, success=True)
        except Exception as e:
            session.rollback()
            return NormalizedResult(
                vacancy_id=vacancy_id, success=False,
                errors=[str(e)]
            )
        finally:
            session.close()
