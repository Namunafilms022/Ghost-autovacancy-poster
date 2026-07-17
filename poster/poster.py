from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from database.session import get_session
from database.models import Vacancy, VacancyPoster

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
_THEME_MAP = {
    'default': 'default.html',
    'dark': 'dark.html',
    'minimal': 'minimal.html',
}

_AVAILABLE_THEMES = list(_THEME_MAP.keys())

_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _format_job_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    mapping = {
        'full_time': 'Full-time',
        'part_time': 'Part-time',
        'contract': 'Contract',
        'internship': 'Internship',
        'freelance': 'Freelance',
    }
    return mapping.get(raw, raw.replace('_', ' ').title())


def _format_experience(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    mapping = {
        'entry': 'Entry Level',
        'mid': 'Mid Level',
        'senior': 'Senior Level',
        'lead': 'Lead',
        'any': 'Any Level',
    }
    return mapping.get(raw, raw.replace('_', ' ').title())


def _parse_requirements(raw: Optional[str]) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    lines = [l.strip().lstrip('-*•').strip() for l in raw.split('\n') if l.strip()]
    return [l for l in lines if l]


def _parse_benefits(raw: Optional[str]) -> list:
    return _parse_requirements(raw)


POLLINATIONS_BASE = 'https://image.pollinations.ai/prompt/'


def _load_poster_config() -> dict:
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('poster', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _load_poster_contact() -> dict:
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('poster_contact', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _generate_pollinations_prompt(title: str, company: str, job_type: Optional[str] = None) -> str:
    parts = ['professional job vacancy banner']
    if title:
        parts.append(title)
    if company:
        parts.append(company)
    parts.extend(['modern corporate style', 'clean design', 'technology theme'])
    if job_type:
        parts.append(job_type)
    return ', '.join(parts)


def _build_pollinations_url(prompt: str, width: int = 1024, height: int = 512) -> str:
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    return f'{POLLINATIONS_BASE}{encoded}?width={width}&height={height}&seed={abs(hash(prompt)) % 100000}'


class PosterGenerator:
    def __init__(self, replace_phone: Optional[str] = None,
                 replace_email: Optional[str] = None,
                 replace_enabled: bool = True):
        config = _load_poster_contact()
        self.replace_enabled = replace_enabled and config.get('replace_enabled', False)
        self.replace_phone = replace_phone or config.get('replace_phone')
        self.replace_email = replace_email or config.get('replace_email')

    def generate(self, vacancy_id: int, theme: str = 'default') -> str:
        if theme not in _AVAILABLE_THEMES:
            raise ValueError(f"Unknown theme '{theme}'. Available: {_AVAILABLE_THEMES}")

        session = get_session()
        try:
            vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if not vacancy:
                raise ValueError(f"Vacancy with id {vacancy_id} not found")

            template_name = _THEME_MAP[theme]
            template = _env.get_template(template_name)

            requirements = []
            if vacancy.raw_message:
                import re
                req_section = re.search(
                    r'(?:^|\n)\s*(?:\*)?Requirements?(?:\*)?\s*[:–-]?\s*(?:\n|$)(.*?)(?:\n\s*(?:\*)?(?:Benefits?|Contact|Salary)(?:\*)?|\Z)',
                    vacancy.raw_message, re.IGNORECASE | re.DOTALL
                )
                if req_section:
                    block = req_section.group(1)
                    requirements = [
                        m.group(1).strip()
                        for line in block.split('\n')
                        if (m := __import__('re').match(r'^\s*[-*•]\s*(.+)$', line))
                    ]

            benefits = []
            if vacancy.raw_message:
                ben_section = re.search(
                    r'(?:^|\n)\s*(?:\*)?Benefits?(?:\*)?\s*[:–-]?\s*(?:\n|$)(.*?)(?:\n\s*(?:\*)?(?:Requirements?|Contact|Salary)(?:\*)?|\Z)',
                    vacancy.raw_message, re.IGNORECASE | re.DOTALL
                )
                if ben_section:
                    block = ben_section.group(1)
                    benefits = [
                        m.group(1).strip()
                        for line in block.split('\n')
                        if (m := __import__('re').match(r'^\s*[-*•]\s*(.+)$', line))
                    ]

            poster_cfg = _load_poster_config()
            use_image = poster_cfg.get('generate_image', True)

            poster_image = None
            if use_image:
                prompt = _generate_pollinations_prompt(
                    vacancy.title or 'Job Vacancy',
                    vacancy.company or '',
                    vacancy.job_type,
                )
                poster_image = _build_pollinations_url(prompt)

            context = {
                'vacancy_id': vacancy.id,
                'title': vacancy.title or 'Untitled Position',
                'company': vacancy.company or 'Unknown Company',
                'location': vacancy.location,
                'job_type': _format_job_type(vacancy.job_type),
                'experience_level': _format_experience(vacancy.experience_level),
                'salary_min': vacancy.salary_min,
                'salary_max': vacancy.salary_max,
                'requirements': requirements or (vacancy.raw_message and _parse_requirements(vacancy.raw_message) or []),
                'benefits': benefits or (vacancy.raw_message and _parse_benefits(vacancy.raw_message) or []),
                'contact_email': None,
                'contact_phone': None,
                'created_at': (vacancy.created_at.strftime('%B %d, %Y')
                               if vacancy.created_at else 'N/A'),
                'poster_image': poster_image,
            }

            if vacancy.raw_message:
                import re
                email_m = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', vacancy.raw_message)
                if email_m:
                    context['contact_email'] = email_m.group(0)
                phone_m = re.search(
                    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
                    vacancy.raw_message
                )
                if phone_m:
                    original = phone_m.group(0)
                    if self.replace_enabled and self.replace_phone:
                        context['contact_phone'] = self.replace_phone
                    else:
                        context['contact_phone'] = original

                if email_m:
                    if self.replace_enabled and self.replace_email:
                        context['contact_email'] = self.replace_email

            html = template.render(**context)

            poster_record = VacancyPoster(
                vacancy_id=vacancy.id,
                html_content=html,
                template_name=template_name,
                theme=theme,
            )
            session.add(poster_record)
            session.commit()

            return html
        except TemplateNotFound:
            raise ValueError(f"Template file '{_THEME_MAP.get(theme)}' not found for theme '{theme}'")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save(self, vacancy_id: int, output_path: str | Path,
             theme: str = 'default') -> Path:
        html = self.generate(vacancy_id, theme=theme)
        path = Path(output_path)
        path.write_text(html, encoding='utf-8')
        return path
