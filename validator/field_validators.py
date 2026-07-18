from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple, List

from .models import FieldValidation, ConfidenceLevel


def _make_field(name: str, value: Optional[str], confidence: float,
                issues: Optional[List[str]] = None,
                details: Optional[str] = None) -> FieldValidation:
    return FieldValidation(
        name=name,
        value=str(value) if value is not None else None,
        confidence=confidence,
        level=ConfidenceLevel.from_score(confidence),
        issues=issues or [],
        details=details,
    )


def _missing(name: str) -> FieldValidation:
    return _make_field(name, None, 0.0, issues=['Field is missing'])


def validate_company(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('company')

    issues = []
    stripped = value.strip()

    if len(stripped) < 2:
        issues.append('Company name is too short')
        return _make_field('company', stripped, 0.2, issues)

    if stripped.islower():
        issues.append('Company name is all lowercase')
        confidence = 0.5
    elif stripped.isupper():
        issues.append('Company name is all uppercase')
        confidence = 0.6
    elif re.search(r'(?:^|\s)(inc|llc|ltd|corp|gmbh|pvt|private|limited)\.?$', stripped, re.IGNORECASE):
        confidence = 1.0
    elif re.search(r'^(?:the|a|an)\s', stripped, re.IGNORECASE):
        issues.append('Starts with article, may be incomplete')
        confidence = 0.7
    else:
        confidence = 0.9

    return _make_field('company', stripped, confidence, issues)


def validate_position(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('position')

    issues = []
    stripped = value.strip()

    if len(stripped) < 5:
        issues.append('Position title is too short')
        return _make_field('position', stripped, 0.2, issues)

    generic_titles = {'job', 'position', 'vacancy', 'hiring', 'requirement',
                      'opening', 'role', 'work', 'employment'}
    if stripped.lower().strip() in generic_titles:
        issues.append('Generic position title')
        confidence = 0.3
    elif len(stripped) < 10:
        confidence = 0.6
    elif re.search(r'(?:senior|junior|lead|head|chief|principal|staff|associate|assistant)\s', stripped, re.IGNORECASE):
        confidence = 0.95
    elif re.search(r'(?:developer|engineer|manager|analyst|designer|consultant|specialist|coordinator|director)', stripped, re.IGNORECASE):
        confidence = 0.9
    else:
        confidence = 0.7

    return _make_field('position', stripped, confidence, issues)


def validate_salary(salary_min: Optional[float], salary_max: Optional[float],
                    raw_text: Optional[str] = None) -> FieldValidation:
    if salary_min is None and salary_max is None and not raw_text:
        return _missing('salary')

    issues = []
    value_str = None

    if salary_min is not None and salary_max is not None:
        value_str = f'{salary_min:.0f} - {salary_max:.0f}'
        if salary_min <= 0 or salary_max <= 0:
            issues.append('Salary value is zero or negative')
            confidence = 0.3
        elif salary_min > salary_max:
            issues.append('Minimum salary exceeds maximum')
            confidence = 0.3
        elif salary_max > salary_min * 10:
            issues.append('Salary range is unusually wide')
            confidence = 0.5
        elif salary_max - salary_min < 1000:
            issues.append('Salary range is very narrow')
            confidence = 0.7
        else:
            confidence = 0.95
    elif salary_min is not None:
        value_str = f'{salary_min:.0f}'
        confidence = 0.6
    elif salary_max is not None:
        value_str = f'{salary_max:.0f}'
        confidence = 0.5
    else:
        value_str = raw_text[:100] if raw_text else 'mentioned'
        confidence = 0.3
        issues.append('Could not parse numeric salary')

    return _make_field('salary', value_str, confidence, issues)


def validate_location(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('location')

    issues = []
    stripped = value.strip()

    if len(stripped) < 3:
        issues.append('Location is too short')
        return _make_field('location', stripped, 0.2, issues)

    if re.search(r'remote|work from home|wfh|anywhere|online', stripped, re.IGNORECASE):
        confidence = 0.85
    elif re.search(r',\s*(?:[A-Z]{2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$', stripped):
        confidence = 0.9
    elif re.search(r'(?:city|town|area|region|province|state|zip|pin)', stripped, re.IGNORECASE):
        confidence = 0.8
    elif stripped.isupper() and len(stripped) <= 5:
        issues.append('Location appears to be an abbreviation')
        confidence = 0.5
    else:
        confidence = 0.6

    return _make_field('location', stripped, confidence, issues)


def validate_requirements(requirements: list) -> FieldValidation:
    if not requirements:
        return _missing('requirements')

    issues = []
    cleaned = [r.strip() for r in requirements if r.strip()]
    count = len(cleaned)

    if count == 0:
        return _missing('requirements')

    if count == 1:
        issues.append('Only one requirement listed')
        confidence = 0.4
    elif count <= 3:
        confidence = 0.6
    else:
        confidence = 0.85

    short_items = sum(1 for r in cleaned if len(r) < 5)
    if short_items > count / 2:
        issues.append('Most requirements are very brief')
        confidence = min(confidence, 0.5)

    return _make_field('requirements', f'{count} items', confidence, issues,
                       details=' | '.join(cleaned[:5]))


def validate_benefits(benefits: list) -> FieldValidation:
    if not benefits:
        return _make_field('benefits', None, 0.3,
                           issues=['No benefits listed'],
                           details='Not mentioned')

    cleaned = [b.strip() for b in benefits if b.strip()]
    count = len(cleaned)

    if count == 0:
        return _make_field('benefits', None, 0.3,
                           issues=['No benefits listed'])
    if count <= 2:
        confidence = 0.6
    else:
        confidence = 0.85

    return _make_field('benefits', f'{count} items', confidence,
                       details=' | '.join(cleaned[:5]))


_DEADLINE_PATTERNS = [
    re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'),
    re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),
    re.compile(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
    re.compile(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\b', re.IGNORECASE),
]


def validate_deadline(raw_text: Optional[str]) -> FieldValidation:
    if not raw_text:
        return _missing('deadline')

    text = raw_text.lower()
    deadline_section = re.search(r'(?:deadline|apply by|last date|closing|closes|expires?|valid till|until)\s*[:–-]?\s*(.+)',
                                 text, re.IGNORECASE | re.MULTILINE)
    if not deadline_section:
        return _make_field('deadline', None, 0.2,
                           issues=['No deadline mentioned'])

    date_text = deadline_section.group(1).strip()
    for pat in _DEADLINE_PATTERNS:
        m = pat.search(date_text)
        if m:
            return _make_field('deadline', m.group(1), 0.9,
                               details='Deadline found')

    return _make_field('deadline', date_text[:80], 0.5,
                       issues=['Date format not recognized'],
                       details=date_text[:100])


def validate_contact(raw_text: Optional[str]) -> FieldValidation:
    if not raw_text:
        return _missing('contact')

    contact_section = re.search(r'(?:contact|reach us|apply|inquiry|reach out|contact info)\s*[:–-]?\s*(.+)',
                                raw_text, re.IGNORECASE | re.MULTILINE)
    if not contact_section:
        return _make_field('contact', None, 0.2,
                           issues=['No contact section found'])

    contact_text = contact_section.group(1).strip()
    if len(contact_text) < 5:
        return _make_field('contact', contact_text, 0.3,
                           issues=['Contact info too brief'])

    has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', contact_text))
    has_phone = bool(re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', contact_text))

    if has_email and has_phone:
        confidence = 1.0
    elif has_email:
        confidence = 0.85
    elif has_phone:
        confidence = 0.75
    else:
        confidence = 0.4
        issues = ['Contact section has no email or phone']

    return _make_field('contact', contact_text[:100], confidence,
                       details=contact_text[:200])


def validate_email(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('email')

    stripped = value.strip()
    if not re.match(r'^[\w.+-]+@[\w-]+\.[\w.-]+$', stripped):
        return _make_field('email', stripped, 0.2,
                           issues=['Invalid email format'])

    if re.search(r'(?:gmail|yahoo|hotmail|outlook|icloud)\.com$', stripped, re.IGNORECASE):
        confidence = 0.6
        issues = ['Uses personal email domain']
    elif re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', stripped, re.IGNORECASE):
        confidence = 0.95
        issues = []
    else:
        confidence = 0.7
        issues = []

    return _make_field('email', stripped, confidence, issues)


def validate_phone(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('phone')

    stripped = value.strip()
    digits = re.sub(r'\D', '', stripped)

    if len(digits) < 7:
        return _make_field('phone', stripped, 0.2,
                           issues=['Too few digits for a phone number'])
    if len(digits) > 15:
        return _make_field('phone', stripped, 0.3,
                           issues=['Too many digits for a phone number'])

    confidence = 0.9
    issues = []

    if len(digits) == 10:
        confidence = 0.95
    elif len(digits) == 7:
        issues.append('Missing area code')
        confidence = 0.5

    return _make_field('phone', stripped, confidence, issues)


def validate_website(value: Optional[str]) -> FieldValidation:
    if not value:
        return _missing('website')

    stripped = value.strip().lower()
    if not re.match(r'^https?://', stripped):
        stripped = 'http://' + stripped

    if re.match(r'^https?://[\w.-]+\.\w{2,}(?:/[\w./-]*)?$', stripped):
        return _make_field('website', value.strip(), 0.95)
    else:
        return _make_field('website', value.strip(), 0.3,
                           issues=['Invalid URL format'])
