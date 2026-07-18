from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from parser.models import JobDetails


SUPPORTED_LANGUAGES = {'english': 'en', 'nepali': 'ne', 'hindi': 'hi'}
LANGUAGE_LABELS = {'english': 'English', 'nepali': 'नेपाली', 'hindi': 'हिन्दी'}


@dataclass
class TranslationResult:
    language: str
    language_label: str
    title: str
    company: str
    description: str
    location: str
    salary: str
    job_type: str
    experience_level: str
    requirements: List[str]
    benefits: List[str]
    raw: Dict[str, str] = field(default_factory=dict)


_SALARY_LABELS: Dict[str, dict] = {
    'ne': {'monthly': 'मासिक', 'yearly': 'वार्षिक', 'hourly': 'प्रति घण्टा', 'daily': 'दैनिक', 'rs': 'रु'},
    'hi': {'monthly': 'मासिक', 'yearly': 'वार्षिक', 'hourly': 'प्रति घंटा', 'daily': 'दैनिक', 'rs': '₹'},
}

_JOB_TYPE_TRANSLATIONS: Dict[str, dict] = {
    'ne': {
        'full_time': 'पूर्णकालीन', 'part_time': 'अंशकालीन',
        'contract': 'सम्झौता', 'internship': 'इन्टर्नशिप',
        'freelance': 'फ्रिलान्स',
    },
    'hi': {
        'full_time': 'पूर्णकालिक', 'part_time': 'अंशकालिक',
        'contract': 'अनुबंध', 'internship': 'इंटर्नशिप',
        'freelance': 'फ्रीलांस',
    },
}

_EXPERIENCE_TRANSLATIONS: Dict[str, dict] = {
    'ne': {
        'entry': 'प्रवेश स्तर', 'mid': 'मध्य स्तर',
        'senior': 'वरिष्ठ', 'lead': 'नेतृत्व / प्रबन्धक',
        'any': 'कुनै पनि',
    },
    'hi': {
        'entry': 'प्रवेश स्तर', 'mid': 'मध्य स्तर',
        'senior': 'वरिष्ठ', 'lead': 'नेतृत्व / प्रबंधक',
        'any': 'कोई भी',
    },
}

_WORD_TRANSLATIONS: Dict[str, dict] = {
    'ne': {
        'salary': 'तलब', 'location': 'स्थान', 'experience': 'अनुभव',
        'requirements': 'आवश्यकताहरू', 'benefits': 'सुविधाहरू',
        'job': 'जागिर', 'work': 'काम', 'hiring': 'भर्ती',
        'urgent': 'अत्यावश्यक', 'remote': 'रिमोट', 'office': 'अफिस',
        'required': 'आवश्यक', 'preferred': 'प्राथमिकता',
        'year': 'वर्ष', 'years': 'वर्ष', 'month': 'महिना',
        'communication': 'संचार', 'team': 'टोली',
        'skilled': 'दक्ष', 'knowledge': 'ज्ञान',
        'management': 'व्यवस्थापन', 'development': 'विकास',
        'senior': 'वरिष्ठ', 'junior': 'कनिष्ठ', 'developer': 'विकासक',
        'engineer': 'इन्जिनियर', 'designer': 'डिजाइनर', 'manager': 'प्रबन्धक',
        'analyst': 'विश्लेषक', 'specialist': 'विशेषज्ञ',
        'assistant': 'सहायक', 'executive': 'कार्यकारी',
        'director': 'निर्देशक', 'consultant': 'सल्लाहकार',
        'trainer': 'प्रशिक्षक', 'coordinator': 'समन्वयक',
        'supervisor': 'पर्यवेक्षक', 'technician': 'प्राविधिक',
        'operator': 'सञ्चालक', 'officer': 'अधिकृत',
    },
    'hi': {
        'salary': 'वेतन', 'location': 'स्थान', 'experience': 'अनुभव',
        'requirements': 'आवश्यकताएँ', 'benefits': 'लाभ',
        'job': 'नौकरी', 'work': 'काम', 'hiring': 'भर्ती',
        'urgent': 'अत्यावश्यक', 'remote': 'रिमोट', 'office': 'कार्यालय',
        'required': 'आवश्यक', 'preferred': 'प्राथमिकता',
        'year': 'वर्ष', 'years': 'वर्ष', 'month': 'महीना',
        'communication': 'संचार', 'team': 'टीम',
        'skilled': 'कुशल', 'knowledge': 'ज्ञान',
        'management': 'प्रबंधन', 'development': 'विकास',
        'senior': 'वरिष्ठ', 'junior': 'कनिष्ठ', 'developer': 'डेवलपर',
        'engineer': 'इंजीनियर', 'designer': 'डिजाइनर', 'manager': 'प्रबंधक',
        'analyst': 'विश्लेषक', 'specialist': 'विशेषज्ञ',
        'assistant': 'सहायक', 'executive': 'कार्यकारी',
        'director': 'निदेशक', 'consultant': 'सलाहकार',
        'trainer': 'प्रशिक्षक', 'coordinator': 'समन्वयक',
        'supervisor': 'पर्यवेक्षक', 'technician': 'तकनीशियन',
        'operator': 'संचालक', 'officer': 'अधिकारी',
    },
}


def _validate_language(language: str) -> str:
    lang = language.strip().lower()
    if lang in LANGUAGE_LABELS:
        return lang
    if lang in SUPPORTED_LANGUAGES.values():
        for name, code in SUPPORTED_LANGUAGES.items():
            if code == lang:
                return name
    raise ValueError(
        f"Unsupported language '{language}'. "
        f"Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"
    )


def _translate_word(word: str, lang: str) -> str:
    lower = word.lower().strip('.,!?;:()[]{}"\'')
    mapping = _WORD_TRANSLATIONS.get(lang, {})
    if lower in mapping:
        cased = mapping[lower]
        if word[0].isupper() if word else False:
            return cased[0].upper() + cased[1:] if len(cased) > 1 else cased.upper()
        return cased
    return word


def _translate_text(text: Optional[str], lang: str) -> str:
    if not text:
        return ''
    tokens = re.findall(r"[\w']+|[^\w]", text)
    return ''.join(_translate_word(t, lang) if t.isalpha() else t for t in tokens)


def _translate_list(items: List[str], lang: str) -> List[str]:
    return [_translate_text(item, lang) for item in items]


def _fmt_salary(
    salary_min: Optional[float],
    salary_max: Optional[float],
    job_type: Optional[str],
    lang: str,
) -> str:
    if salary_min is None and salary_max is None:
        return ''
    labels = _SALARY_LABELS.get(lang, _SALARY_LABELS.get('en', {}))
    rs = labels.get('rs', 'Rs.')
    period = labels.get((job_type or '').lower(), '')
    if salary_min is not None and salary_max is not None and salary_max != salary_min:
        return f'{rs}{salary_min:,.0f} - {rs}{salary_max:,.0f} {period}'.strip()
    if salary_min is not None:
        return f'{rs}{salary_min:,.0f} {period}'.strip()
    return f'{rs}{salary_max:,.0f} {period}'.strip()


def _translate_job_type(jt: Optional[str], lang: str) -> str:
    if not jt:
        return ''
    mapping = _JOB_TYPE_TRANSLATIONS.get(lang, {})
    return mapping.get(jt.lower(), jt.replace('_', ' ').title())


def _translate_experience(el: Optional[str], lang: str) -> str:
    if not el:
        return ''
    mapping = _EXPERIENCE_TRANSLATIONS.get(lang, {})
    return mapping.get(el.lower(), el.capitalize())


def translate_vacancy(job_details: JobDetails, language: str) -> TranslationResult:
    lang = _validate_language(language)
    code = SUPPORTED_LANGUAGES[lang]

    if code == 'en':
        return TranslationResult(
            language=lang,
            language_label=LANGUAGE_LABELS[lang],
            title=job_details.title or '',
            company=job_details.company or '',
            description=job_details.description or '',
            location=job_details.location or '',
            salary=_fmt_salary(job_details.salary_min, job_details.salary_max, job_details.job_type, lang),
            job_type=(job_details.job_type or '').replace('_', ' ').title() if job_details.job_type else '',
            experience_level=(job_details.experience_level or '').capitalize() if job_details.experience_level else '',
            requirements=job_details.requirements[:],
            benefits=job_details.benefits[:],
        )

    return TranslationResult(
        language=lang,
        language_label=LANGUAGE_LABELS[lang],
        title=_translate_text(job_details.title, code),
        company=_translate_text(job_details.company, code),
        description=_translate_text(job_details.description, code),
        location=_translate_text(job_details.location, code),
        salary=_fmt_salary(job_details.salary_min, job_details.salary_max, job_details.job_type, code),
        job_type=_translate_job_type(job_details.job_type, code),
        experience_level=_translate_experience(job_details.experience_level, code),
        requirements=_translate_list(job_details.requirements, code),
        benefits=_translate_list(job_details.benefits, code),
    )


translateVacancy = translate_vacancy
