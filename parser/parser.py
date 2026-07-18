from __future__ import annotations

import re
from typing import Optional

from .models import JobDetails


def _parse_salary(text: str) -> tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None

    parts = re.split(r'[-–—to]+', text)
    values: list[float] = []

    for part in parts:
        part = part.strip()
        part = part.replace(',', '').replace('$', '').replace('₹', '').replace('€', '').replace('£', '')
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


def _extract_bullets_after_header(text: str, header_pattern: str) -> list[str]:
    sections = re.split(_header_pattern(header_pattern), text, flags=re.IGNORECASE | re.MULTILINE)
    if len(sections) < 2:
        return []

    after = sections[1]
    lines = []
    for line in after.split('\n'):
        line = line.strip()
        if not line:
            continue
        next_header = re.match(
            r'(?:\*)?(?:Requirements?|Benefits?|Contact|Salary|Location|Company|Job Type|Experience)(?:\*)?\s*[:–-]?',
            line, re.IGNORECASE
        )
        if next_header:
            break
        m = re.match(r'^[-*•]\s*(.+)$', line)
        if m:
            lines.append(m.group(1).strip())
        elif not line.startswith('-') and not line.startswith('*') and not line.startswith('•'):
            continue
    return lines


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


class VacancyParser:
    def __init__(self):
        self.email_re = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
        self.phone_re = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}')

    def parse(self, text: str) -> JobDetails:
        result = JobDetails(raw_message=text, description=text[:500] if text else None)

        result.title = (
            _extract_field(text, 'Job Title', 'Position', 'Role')
            or self._extract_title_hiring(text)
        )

        result.company = _extract_field(text, 'Company', 'Organization', 'Employer', 'Firm', 'At')

        result.location = _extract_field(
            text, 'Location', 'Place', 'City', 'Workplace', 'Office'
        )

        salary_text = _extract_field(text, 'Salary', 'Pay', 'Compensation', 'Stipend')
        if salary_text:
            result.salary_min, result.salary_max = _parse_salary(salary_text)

        result.job_type = _extract_field(
            text, 'Job Type', 'Employment Type', 'Type'
        )

        result.experience_level = _extract_field(
            text, 'Experience(?: Level)?', 'Level', 'Seniority'
        )

        result.requirements = _extract_all_bullets_in_range(
            text, 'Requirements?', ['Benefits?', 'Contact', 'Salary', 'Location', 'Company']
        )

        result.benefits = _extract_all_bullets_in_range(
            text, 'Benefits?', ['Requirements?', 'Contact', 'Salary']
        )

        contact_line = _extract_field(text, 'Contact', 'Contact Info', 'Reach us', 'WhatsApp')
        if contact_line:
            email_match = self.email_re.search(contact_line)
            if email_match:
                result.contact_email = email_match.group(0)
            phone_match = self.phone_re.search(contact_line)
            if phone_match:
                result.contact_phone = phone_match.group(0)

        if not result.contact_email:
            email_match = self.email_re.search(text)
            if email_match:
                result.contact_email = email_match.group(0)

        if not result.contact_phone:
            phone_match = self.phone_re.search(text)
            if phone_match:
                result.contact_phone = phone_match.group(0)

        return result

    def _extract_title_hiring(self, text: str) -> Optional[str]:
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
