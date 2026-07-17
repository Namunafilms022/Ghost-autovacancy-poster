from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

from .models import JobDetails

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """You are a job posting parser. Extract structured information from the given vacancy message.
Return ONLY valid JSON with these fields:
- title: job title (string or null)
- company: company name (string or null)
- location: job location (string or null)
- salary_min: minimum salary as a raw number (number or null) — do NOT multiply by 1000 for "k"
- salary_max: maximum salary as a raw number (number or null) — do NOT multiply by 1000 for "k"
- salary_currency: currency code like "USD", "INR", "NPR", "EUR", "GBP" (string or null)
- job_type: employment type e.g. "Full-time", "Part-time", "Contract", "Internship" (string or null)
- experience_level: e.g. "Entry", "Mid", "Senior", "Lead" (string or null)
- requirements: list of requirement strings (array of strings)
- benefits: list of benefit strings (array of strings)
- contact_email: email address (string or null)
- contact_phone: phone number (string or null)

Keep all values as raw strings — do not normalize. Output ONLY the JSON object, no other text."""


def _parse_salary(text: str) -> tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None

    parts = re.split(r'[-–—to]+', text)
    values: list[float] = []

    for part in parts:
        part = part.strip()
        part = part.replace(',', '').replace('$', '').replace('\u20b9', '').replace('\u20ac', '').replace('\u00a3', '')
        m = re.search(r'(\d+(?:\.\d+)?)\s*(k|K|L|lakh|cr|crore)?', part, re.IGNORECASE)
        if m:
            num = float(m.group(1))
            suffix = (m.group(2) or '').lower()
            if suffix == 'k':
                num *= 1000
            elif suffix == 'l' or suffix == 'lakh':
                num *= 100000
            elif suffix == 'cr' or suffix == 'crore':
                num *= 10000000
            values.append(num)

    if len(values) >= 2:
        return values[0], values[1]
    if len(values) == 1:
        return values[0], values[0]
    return None, None


def _extract_field(text: str, *patterns: str) -> Optional[str]:
    for pattern in patterns:
        m = re.search(
            r'(?:^|\n)\s*(?:\*)?' + pattern + r'(?:\*)?\s*[:–-]?\s*(.+?)(?:\n|$)',
            text, re.IGNORECASE | re.MULTILINE
        )
        if m:
            val = m.group(1).strip().strip('*').strip()
            if val:
                return val
    return None


def _header_pattern(header: str) -> str:
    return r'(?:^|\n)\s*(?:\*)?' + header + r'(?:\*)?\s*[:–-]?\s*(?:\*)?\s*(?:\n|$)'


def _extract_all_bullets_in_range(text: str, start_header: str, end_headers: list[str]) -> list[str]:
    pat = _header_pattern(start_header)
    start_match = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
    if not start_match:
        return []

    start_pos = start_match.end()
    end_pos = len(text)

    for hdr in end_headers:
        m = re.search(
            _header_pattern(hdr),
            text[start_pos:], re.IGNORECASE | re.MULTILINE
        )
        if m:
            end_pos = start_pos + m.start()
            break

    block = text[start_pos:end_pos]
    items = []
    for line in block.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^[-*•]\s*(.+)$', line)
        if m:
            items.append(m.group(1).strip())
    return items


def _load_groq_key() -> str:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('parser', {}).get('groq_api_key', '')
    except (FileNotFoundError, json.JSONDecodeError):
        return ''


def _parse_groq_response(data: dict, raw_message: str) -> Optional[dict]:
    try:
        content = data['choices'][0]['message']['content']
        parsed = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError):
        return None

    salary_min = parsed.get('salary_min')
    salary_max = parsed.get('salary_max')
    if salary_min is not None:
        salary_min = float(salary_min)
    if salary_max is not None:
        salary_max = float(salary_max)

    return {
        'title': parsed.get('title') or None,
        'company': parsed.get('company') or None,
        'location': parsed.get('location') or None,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'job_type': parsed.get('job_type') or None,
        'experience_level': parsed.get('experience_level') or None,
        'requirements': parsed.get('requirements', []),
        'benefits': parsed.get('benefits', []),
        'contact_email': parsed.get('contact_email') or None,
        'contact_phone': parsed.get('contact_phone') or None,
    }


def _call_groq(text: str, api_key: str) -> Optional[dict]:
    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': GROQ_MODEL,
                'messages': [
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user', 'content': text},
                ],
                'response_format': {'type': 'json_object'},
                'temperature': 0.1,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        return _parse_groq_response(resp.json(), text)
    except (requests.RequestException, ValueError):
        return None


def _regex_parse(text: str) -> dict:
    email_re = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    phone_re = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}')

    title = (
        _extract_field(text, 'Job Title', 'Position', 'Role')
        or _regex_extract_title_hiring(text)
    )
    company = _extract_field(text, 'Company', 'Organization', 'Employer', 'Firm', 'At')
    location = _extract_field(text, 'Location', 'Place', 'City', 'Workplace', 'Office')

    salary_min, salary_max = None, None
    salary_text = _extract_field(text, 'Salary', 'Pay', 'Compensation', 'Stipend')
    if salary_text:
        salary_min, salary_max = _parse_salary(salary_text)

    job_type = _extract_field(text, 'Job Type', 'Employment Type', 'Type')
    experience_level = _extract_field(text, 'Experience(?: Level)?', 'Level', 'Seniority')

    requirements = _extract_all_bullets_in_range(
        text, 'Requirements?', ['Benefits?', 'Contact', 'Salary', 'Location', 'Company']
    )
    benefits = _extract_all_bullets_in_range(
        text, 'Benefits?', ['Requirements?', 'Contact', 'Salary']
    )

    contact_email = None
    contact_phone = None
    contact_line = _extract_field(text, 'Contact', 'Contact Info', 'Reach us', 'WhatsApp')
    if contact_line:
        email_match = email_re.search(contact_line)
        if email_match:
            contact_email = email_match.group(0)
        phone_match = phone_re.search(contact_line)
        if phone_match:
            contact_phone = phone_match.group(0)

    if not contact_email:
        email_match = email_re.search(text)
        if email_match:
            contact_email = email_match.group(0)

    if not contact_phone:
        phone_match = phone_re.search(text)
        if phone_match:
            contact_phone = phone_match.group(0)

    return {
        'title': title,
        'company': company,
        'location': location,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'job_type': job_type,
        'experience_level': experience_level,
        'requirements': requirements,
        'benefits': benefits,
        'contact_email': contact_email,
        'contact_phone': contact_phone,
    }


def _regex_extract_title_hiring(text: str) -> Optional[str]:
    m = re.search(
        r'(?:hiring|looking for|recruiting|opening for|requirement for|vacancy for|need a|need an|need )'
        r'\s+(?:a|an|the|a few)?\s*(.+?)(?:\n|\.|,|!)',
        text, re.IGNORECASE
    )
    if m:
        title = m.group(1).strip()
        if len(title) < 100:
            return title
    return None


class VacancyParser:
    def __init__(self, use_groq: bool = True, api_key: Optional[str] = None):
        self.use_groq = use_groq
        self.api_key = api_key if api_key is not None else _load_groq_key()

    def parse(self, text: str) -> JobDetails:
        fields: dict = {
            'title': None,
            'company': None,
            'location': None,
            'salary_min': None,
            'salary_max': None,
            'job_type': None,
            'experience_level': None,
            'requirements': [],
            'benefits': [],
            'contact_email': None,
            'contact_phone': None,
        }

        if self.use_groq and self.api_key:
            result = _call_groq(text, self.api_key)
            if result:
                fields.update(result)
            else:
                fields.update(_regex_parse(text))
        else:
            fields.update(_regex_parse(text))

        return JobDetails(
            title=fields['title'],
            company=fields['company'],
            description=text[:500] if text else None,
            location=fields['location'],
            salary_min=fields['salary_min'],
            salary_max=fields['salary_max'],
            job_type=fields['job_type'],
            experience_level=fields['experience_level'],
            requirements=fields['requirements'] or [],
            benefits=fields['benefits'] or [],
            contact_email=fields['contact_email'],
            contact_phone=fields['contact_phone'],
            raw_message=text,
        )
