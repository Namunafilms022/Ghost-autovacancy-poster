from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from parser.models import JobDetails


SALARY_PERIOD_LABELS: dict[str, str] = {
    'monthly': '/month', 'yearly': '/year', 'hourly': '/hr', 'daily': '/day',
}


@dataclass
class SummaryResult:
    title: str
    company: str
    location: str
    salary: str
    experience: str
    short_summary: str
    bullet_points: List[str] = field(default_factory=list)


def _fmt_salary(jd: JobDetails) -> str:
    if jd.salary_min is None and jd.salary_max is None:
        return 'Not specified'
    parts = []
    if jd.salary_min is not None:
        parts.append(f'Rs.{jd.salary_min:,.0f}')
    if jd.salary_max is not None and jd.salary_max != jd.salary_min:
        parts.append(f'Rs.{jd.salary_max:,.0f}')
    label = SALARY_PERIOD_LABELS.get((jd.job_type or '').lower(), '')
    return ' - '.join(parts) + label


def _fmt_experience(jd: JobDetails) -> str:
    level = (jd.experience_level or '').strip()
    if not level:
        return 'Not specified'
    label_map = {
        'entry': 'Entry Level', 'mid': 'Mid Level',
        'senior': 'Senior Level', 'lead': 'Lead / Manager',
        'any': 'Any Experience',
    }
    return label_map.get(level.lower(), level.capitalize())


BULLET_FIELD_ORDER = [
    ('location', lambda jd: jd.location),
    ('salary', lambda jd: _fmt_salary(jd) if jd.salary_min is not None or jd.salary_max is not None else None),
    ('experience', lambda jd: _fmt_experience(jd) if (jd.experience_level or '').strip() else None),
    ('job_type', lambda jd: (jd.job_type or '').replace('_', ' ').title() if jd.job_type else None),
    ('requirements', lambda jd: ' '.join(jd.requirements[:3]) + ('…' if len(jd.requirements) > 3 else '') if jd.requirements else None),
    ('benefits', lambda jd: ' '.join(jd.benefits[:2]) + ('…' if len(jd.benefits) > 2 else '') if jd.benefits else None),
]


def summarize_vacancy(job_details: JobDetails) -> SummaryResult:
    title = job_details.title or 'Untitled Position'
    company = job_details.company or 'Unknown Company'
    location = job_details.location or 'Location not specified'
    salary = _fmt_salary(job_details)
    experience = _fmt_experience(job_details)

    bullets: List[str] = []
    for _, extractor in BULLET_FIELD_ORDER:
        val = extractor(job_details)
        if val:
            bullets.append(val)
        if len(bullets) >= 5:
            break

    summary_parts = [f'{title} at {company}']
    if location and location != 'Location not specified':
        summary_parts.append(f'based in {location}')
    if salary != 'Not specified':
        summary_parts.append(f'offering {salary}')
    short_summary = ', '.join(summary_parts) + '.'

    return SummaryResult(
        title=title,
        company=company,
        location=location,
        salary=salary,
        experience=experience,
        short_summary=short_summary,
        bullet_points=bullets,
    )


summarizeVacancy = summarize_vacancy
