from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from database.session import get_session
from database.models import Vacancy, VacancyPoster
from .themes import (
    get_theme,
    auto_select_theme,
    AVAILABLE_THEMES,
    ALL_THEMES,
    Theme,
)
from .backgrounds import detect_category, background_svg, overlay_gradient, CATEGORIES
from .layers import build_layer_context, LayerContext
from .company import get_company_branding

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
_TEMPLATE_NAME = 'theme.html'
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

_THEME_ICONS = {
    'minimal': {
        'location': '📍', 'job_type': '💼', 'exp': '📊',
        'salary': '💰', 'req': '📋', 'benefit': '✨',
        'contact': '📬', 'email': '✉️', 'phone': '📞',
        'footer': '·',
    },
    'glass': {
        'location': '⊡', 'job_type': '⊡', 'exp': '⊡',
        'salary': '⊡', 'req': '⊡', 'benefit': '⊡',
        'contact': '⊡', 'email': '⊡', 'phone': '⊡',
        'footer': '·',
    },
    'dark_neon': {
        'location': '◆', 'job_type': '▶', 'exp': '▲',
        'salary': '◆', 'req': '▶', 'benefit': '✦',
        'contact': '◈', 'email': '◈', 'phone': '◈',
        'footer': '◆',
    },
    'corporate_hiring_red': {
        'location': '📍', 'job_type': '💼', 'exp': '📊',
        'salary': '💰', 'req': '📋', 'benefit': '⭐',
        'contact': '📬', 'email': '✉️', 'phone': '📞',
        'footer': '·',
    },
    'ghost': {
        'location': '○', 'job_type': '○', 'exp': '○',
        'salary': '◎', 'req': '○', 'benefit': '○',
        'contact': '○', 'email': '○', 'phone': '○',
        'footer': '·',
    },
    'cyberpunk': {
        'location': '►', 'job_type': '►', 'exp': '►',
        'salary': '◄', 'req': '►', 'benefit': '◆',
        'contact': '◄', 'email': '◄', 'phone': '◄',
        'footer': '►◄',
    },
    'blue_professional': {
        'location': '📍', 'job_type': '💼', 'exp': '📊',
        'salary': '💰', 'req': '📋', 'benefit': '🏆',
        'contact': '📧', 'email': '📧', 'phone': '📞',
        'footer': '·',
    },
}

_THEME_BULLETS = {
    'minimal': '--',
    'glass': '⊡',
    'dark_neon': '◆',
    'corporate_hiring_red': '▸',
    'ghost': '○',
    'cyberpunk': '►',
    'blue_professional': '✓',
}

_SALARY_PREFIXES = {
    'corporate_hiring_red': '₹',
    'dark_neon': '₿',
}

_SECTION_SIZES = {
    'minimal': '11px',
    'ghost': '13px',
}

_SALARY_SIZES = {
    'minimal': '24px',
}

_META_STYLES = {
    'glass': {'bg': 'rgba(255,255,255,0.1)', 'color': '#fff', 'border': 'border: 1px solid rgba(255,255,255,0.15);'},
    'dark_neon': {'bg': '#1a1a24', 'color': '#888899', 'border': 'border: 1px solid #2a2a3a;'},
    'cyberpunk': {'bg': '#1a1a2e', 'color': '#f0e100', 'border': 'border: 1px solid #f0e100;'},
}

_SECTION_BORDERS = {
    'minimal': '1px solid #eee',
    'glass': '1px solid rgba(255,255,255,0.1)',
    'dark_neon': '1px solid #2a2a3a',
    'cyberpunk': '1px solid #2a2a4a',
    'ghost': '1px solid #334155',
}

_FOOTER_BORDERS = {
    'glass': '1px solid rgba(255,255,255,0.08)',
    'dark_neon': '1px solid #1a1a24',
    'ghost': '1px solid #1e293b',
}

_BENEFIT_BORDERS = {
    'dark_neon': 'border: 1px solid #2a2a3a;',
    'ghost': 'border: 1px solid #334155;',
}

_CONTACT_BORDERS = {
    'glass': 'border: 1px solid rgba(255,255,255,0.1);',
    'dark_neon': 'border: 1px solid #2a2a3a;',
    'ghost': 'border: 1px solid #1e293b;',
}

_DECORATIVE_ICON_STYLES = {
    'subtle': {'size': '48px', 'opacity': '0.04'},
    'neon': {'size': '36px', 'opacity': '0.08'},
    'cyber': {'size': '28px', 'opacity': '0.06'},
}

_ICON_POSITIONS = [
    (5, 8), (85, 5), (10, 20), (75, 25), (90, 45),
    (8, 55), (80, 60), (15, 75), (88, 80), (5, 90),
    (50, 6), (45, 92), (70, 15), (30, 85), (92, 35),
]


def _format_job_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    mapping = {
        'full_time': 'Full-time', 'part_time': 'Part-time',
        'contract': 'Contract', 'internship': 'Internship',
        'freelance': 'Freelance',
    }
    return mapping.get(raw, raw.replace('_', ' ').title())


def _format_experience(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    mapping = {
        'entry': 'Entry Level', 'mid': 'Mid Level',
        'senior': 'Senior Level', 'lead': 'Lead',
        'any': 'Any Level',
    }
    return mapping.get(raw, raw.replace('_', ' ').title())


def _load_poster_contact() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('poster_contact', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _build_theme_context(theme: Theme) -> dict:
    name = theme.name
    icons = _THEME_ICONS.get(name, _THEME_ICONS['blue_professional'])
    meta = _META_STYLES.get(name, {'bg': 'rgba(255,255,255,0.12)', 'color': '#fff', 'border': ''})
    icon_style = _DECORATIVE_ICON_STYLES.get(theme.icons, {'size': '40px', 'opacity': '0.06'})

    return {
        'theme': name,
        'theme_icons_style': theme.icons,
        'css_vars': theme.css_vars,
        'font_link': theme.font_link,
        'font_stack': theme.font_stack,
        'card_style': theme.card_style,
        'meta_bg': meta['bg'],
        'meta_color': meta['color'],
        'meta_border': meta['border'],
        'section_heading_size': _SECTION_SIZES.get(name, '14px'),
        'section_border': _SECTION_BORDERS.get(name, '2px solid var(--border)'),
        'salary_size': _SALARY_SIZES.get(name, '28px'),
        'bullet_icon': _THEME_BULLETS.get(name, '✓'),
        'benefit_border': _BENEFIT_BORDERS.get(name, ''),
        'contact_border': _CONTACT_BORDERS.get(name, ''),
        'footer_border': _FOOTER_BORDERS.get(name, '1px solid var(--border)'),
        'location_icon': icons['location'],
        'job_type_icon': icons['job_type'],
        'exp_icon': icons['exp'],
        'salary_icon': icons['salary'],
        'salary_prefix': _SALARY_PREFIXES.get(name, 'Rs.'),
        'req_icon': icons['req'],
        'benefit_icon': icons['benefit'],
        'contact_icon': icons['contact'],
        'email_icon': icons['email'],
        'phone_icon': icons['phone'],
        'footer_icon': icons['footer'],
        'decorative_icon_size': icon_style['size'],
        'decorative_icon_opacity': icon_style['opacity'],
    }


def _build_layer_context_for_theme(name: str, theme: Theme,
                                    category: str) -> dict:
    bg = background_svg(category, theme.accent)
    overlay = overlay_gradient(category, name)
    lc = build_layer_context(category, bg, overlay)

    icon_positions = _ICON_POSITIONS[:len(lc.icons_decorative)]
    decorative = list(zip(lc.icons_decorative,
                          [f'{x}%' for _, x in icon_positions],
                          [f'{y}%' for y, _ in icon_positions]))

    text_margin = '16px' if lc.show_icons_layer else '0'
    blur = '12px' if 'glass' in name else '0px'
    surface_extra = ''
    if 'glass' in name:
        surface_extra = 'background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);'

    return {
        'background_svg': lc.background_svg,
        'background_category': lc.background_category,
        'overlay_css': lc.overlay_css,
        'show_icons_layer': lc.show_icons_layer,
        'decorative_icons': decorative,
        'text_margin': text_margin,
        'blur_amount': blur,
        'text_surface_style': surface_extra,
    }


def _extract_section(text: str, header: str, end_headers: list) -> list:
    pat = r'(?:^|\n)\s*(?:\*)?' + header + r'(?:\*)?\s*[:–-]?\s*(?:\n|$)(.*?)(?:\n\s*(?:\*)?(?:' + '|'.join(end_headers) + r')(?:\*)?|\Z)'
    m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    items = []
    for line in block.split('\n'):
        lm = re.match(r'^\s*[-*•]\s*(.+)$', line)
        if lm:
            items.append(lm.group(1).strip())
    return items


class PosterGenerator:
    def __init__(self, replace_phone: Optional[str] = None,
                 replace_email: Optional[str] = None,
                 replace_enabled: bool = True):
        config = _load_poster_contact()
        self.replace_enabled = replace_enabled and config.get('replace_enabled', False)
        self.replace_phone = replace_phone or config.get('replace_phone')
        self.replace_email = replace_email or config.get('replace_email')

    def generate(self, vacancy_id: int, theme: Optional[str] = None,
                 category: Optional[str] = None) -> str:
        session = get_session()
        try:
            vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if not vacancy:
                raise ValueError(f"Vacancy with id {vacancy_id} not found")

            job_cat = category or detect_category(vacancy.title, vacancy.raw_message)

            if theme is None:
                theme = auto_select_theme(
                    confidence=None,
                    job_type=vacancy.job_type,
                    experience=vacancy.experience_level,
                )

            theme_obj = get_theme(theme)
            template = _env.get_template(_TEMPLATE_NAME)

            requirements = _extract_section(
                vacancy.raw_message or '', 'Requirements?',
                ['Benefits?', 'Contact', 'Salary', 'Location', 'Company']
            ) or []

            benefits = _extract_section(
                vacancy.raw_message or '', 'Benefits?',
                ['Requirements?', 'Contact', 'Salary']
            ) or []

            company_name = vacancy.company or 'Unknown Company'
            branding = get_company_branding(company_name)

            ctx = _build_theme_context(theme_obj)
            ctx.update(_build_layer_context_for_theme(theme, theme_obj, job_cat))
            ctx.update({
                'vacancy_id': vacancy.id,
                'title': vacancy.title or 'Untitled Position',
                'company': company_name,
                'company_logo': branding.logo_data_uri,
                'company_logo_is_placeholder': branding.logo_is_placeholder,
                'company_website': branding.website_url,
                'brand_color': branding.brand_color,
                'brand_accent': branding.accent_color,
                'location': vacancy.location,
                'job_type': _format_job_type(vacancy.job_type),
                'experience_level': _format_experience(vacancy.experience_level),
                'salary_min': vacancy.salary_min,
                'salary_max': vacancy.salary_max,
                'requirements': requirements,
                'benefits': benefits,
                'contact_email': None,
                'contact_phone': None,
                'created_at': (vacancy.created_at.strftime('%B %d, %Y')
                               if vacancy.created_at else 'N/A'),
            })

            if vacancy.raw_message:
                email_m = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', vacancy.raw_message)
                if email_m:
                    ctx['contact_email'] = email_m.group(0)
                phone_m = re.search(
                    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
                    vacancy.raw_message
                )
                if phone_m:
                    original = phone_m.group(0)
                    ctx['contact_phone'] = (
                        self.replace_phone if self.replace_enabled and self.replace_phone
                        else original
                    )
                if email_m and self.replace_enabled and self.replace_email:
                    ctx['contact_email'] = self.replace_email

            html = template.render(**ctx)

            poster_record = VacancyPoster(
                vacancy_id=vacancy.id,
                html_content=html,
                template_name=_TEMPLATE_NAME,
                theme=theme,
            )
            session.add(poster_record)
            session.commit()

            return html
        except TemplateNotFound:
            raise ValueError(f"Template '{_TEMPLATE_NAME}' not found")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save(self, vacancy_id: int, output_path: str | Path,
             theme: Optional[str] = None,
             category: Optional[str] = None) -> Path:
        html = self.generate(vacancy_id, theme=theme, category=category)
        path = Path(output_path)
        path.write_text(html, encoding='utf-8')
        return path
