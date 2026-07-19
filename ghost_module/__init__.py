from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from database.init import init_db
from database.models import Vacancy
from database.session import get_session

from text_cleaner import clean_text
from parser import VacancyParser, JobDetails
from validator import validate_extraction as _validate_extraction
from validator.models import ExtractionResult
from duplicate import DuplicateDetector, DuplicateResult
from poster import PosterGenerator
from poster.themes import auto_select_theme
from poster.backgrounds import detect_category
from captions import generate_captions as _generate_captions
from captions import CaptionResult
from publisher import FacebookPublisher, PublisherPipeline


def _load_config() -> dict:
    from config.env_loader import get_config
    return get_config()


def _ensure_db():
    init_db()


def _get_poster_generator():
    cfg = _load_config()
    contact = cfg.get('poster_contact', {})
    return PosterGenerator(
        replace_phone=contact.get('replace_phone'),
        replace_email=contact.get('replace_email'),
        replace_enabled=contact.get('replace_enabled', True),
    )


def _get_publisher_pipeline():
    cfg = _load_config()
    fb_cfg = cfg.get('facebook', {})
    poster_gen = _get_poster_generator()
    fb = FacebookPublisher(
        access_token=fb_cfg.get('access_token') or None,
        group_ids=fb_cfg.get('group_ids', []),
        api_version=fb_cfg.get('api_version', 'v18.0'),
        poster_generator=poster_gen,
    )
    return PublisherPipeline(publishers=[fb])


def create_poster(
    vacancy_id: int,
    theme: Optional[str] = None,
    category: Optional[str] = None,
    auto_theme: bool = True,
) -> str:
    _ensure_db()
    gen = _get_poster_generator()
    if auto_theme and theme is None:
        with get_session() as session:
            v = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if v:
                theme = auto_select_theme(v.job_type, v.experience_level)
                category = category or detect_category(v.title or '', v.description or '')
    return gen.generate(vacancy_id, theme=theme, category=category)


createPoster = create_poster


def generate_caption(
    title: str,
    company: str,
    location: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    job_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    benefits: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> CaptionResult:
    return _generate_captions(
        title=title,
        company=company,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        job_type=job_type,
        experience_level=experience_level,
        requirements=requirements or [],
        benefits=benefits or [],
        description=description,
    )


generateCaption = generate_caption


def extract_vacancy(raw_text: str) -> JobDetails:
    cleaned = clean_text(raw_text)
    parser = VacancyParser()
    return parser.parse(cleaned)


extractVacancy = extract_vacancy


def validate_vacancy(
    job_details: JobDetails,
    threshold: float = 0.7,
) -> ExtractionResult:
    return _validate_extraction(job_details, threshold=threshold)


validateVacancy = validate_vacancy


def check_duplicate(
    job_details: JobDetails,
    vacancy_id: Optional[int] = None,
    threshold: float = 0.75,
) -> DuplicateResult:
    _ensure_db()
    detector = DuplicateDetector(similarity_threshold=threshold)
    return detector.detect(job_details, vacancy_id=vacancy_id)


checkDuplicate = check_duplicate


def publish(vacancy_id: int) -> List[Dict[str, Any]]:
    _ensure_db()
    pipeline = _get_publisher_pipeline()
    results = pipeline.publish(vacancy_id)
    return [
        {
            'platform': r.platform,
            'success': r.success,
            'post_id': r.post_id,
            'url': r.url,
            'error': r.error,
            'attempts': r.attempts,
        }
        for r in results
    ]


publish_ = publish


# ---- New APIs -----------------------------------------------------------

from ghost_module.summarizer import summarize_vacancy, SummaryResult
from ghost_module.translator import translate_vacancy, TranslationResult

summarizeVacancy = summarize_vacancy
translateVacancy = translate_vacancy
