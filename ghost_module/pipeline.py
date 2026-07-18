from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import Vacancy
from database.session import get_session
from reader import FileReader, ReaderPipeline
from text_cleaner import clean_text
from parser import VacancyParser
from validator import validate_extraction as _validate_extraction
from duplicate import DuplicateDetector, DuplicateResult
from poster import PosterGenerator
from poster.themes import auto_select_theme
from poster.backgrounds import detect_category
from captions import generate_captions as _generate_captions


OUTPUT_POSTERS = Path('output/posters')
OUTPUT_CAPTIONS = Path('output/captions')
QUEUE_READY = Path('queue/ready')


@dataclass
class StageResult:
    name: str
    success: bool
    duration: float
    details: Optional[str] = None


@dataclass
class MessageResult:
    raw_message: str
    index: int
    vacancy_id: Optional[int] = None
    company: str = ''
    position: str = ''
    location: str = ''
    salary: str = ''
    is_duplicate: bool = False
    duplicate_score: float = 0.0
    validation_passed: bool = False
    validation_confidence: float = 0.0
    poster_path: Optional[str] = None
    caption_path: Optional[str] = None
    ready_package_path: Optional[str] = None
    skipped: bool = False
    skip_reason: str = ''
    stages: List[StageResult] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PipelineResult:
    total: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    duration: float = 0.0
    messages: List[MessageResult] = field(default_factory=list)


def _fmt_salary(jd) -> str:
    parts = []
    if jd.salary_min is not None:
        parts.append(f'Rs.{jd.salary_min:,.0f}')
    if jd.salary_max is not None and jd.salary_max != jd.salary_min:
        parts.append(f'Rs.{jd.salary_max:,.0f}')
    return ' - '.join(parts) if parts else 'Not specified'


def _save_poster(vacancy_id: int, theme: Optional[str] = None, category: Optional[str] = None) -> Optional[str]:
    OUTPUT_POSTERS.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_POSTERS / f'{vacancy_id}.html'
    gen = PosterGenerator()
    if theme is None:
        with get_session() as session:
            v = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if v:
                theme = auto_select_theme(v.job_type, v.experience_level)
                category = category or detect_category(v.title or '', v.description or '')
    html = gen.generate(vacancy_id, theme=theme, category=category)
    path.write_text(html, encoding='utf-8')
    return str(path)


def _save_caption(jd, vacancy_id: int) -> tuple:
    OUTPUT_CAPTIONS.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_CAPTIONS / f'{vacancy_id}.json'
    cr = _generate_captions(
        title=jd.title or '',
        company=jd.company or '',
        location=jd.location,
        salary_min=jd.salary_min,
        salary_max=jd.salary_max,
        job_type=jd.job_type,
        experience_level=jd.experience_level,
        requirements=jd.requirements,
        benefits=jd.benefits,
        description=jd.description,
    )
    data = {
        'vacancy_id': vacancy_id,
        'title': cr.title,
        'company': cr.company,
        'platforms': {
            p: {
                'caption': cs.caption,
                'hashtags': cs.hashtags,
                'call_to_action': cs.call_to_action,
                'short_version': cs.short_version,
                'long_version': cs.long_version,
            }
            for p, cs in cr.platforms.items()
        },
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(path), list(cr.platforms.keys())


def _create_ready_package(result: MessageResult, platforms: List[str]) -> Optional[str]:
    QUEUE_READY.mkdir(parents=True, exist_ok=True)
    path = QUEUE_READY / f'{result.vacancy_id}.json'

    if result.poster_path and not Path(result.poster_path).exists():
        return None
    if result.caption_path and not Path(result.caption_path).exists():
        return None

    package = {
        'vacancy_id': result.vacancy_id,
        'company': result.company,
        'position': result.position,
        'location': result.location,
        'poster': result.poster_path,
        'caption': result.caption_path,
        'platforms': sorted(platforms),
        'status': 'READY_TO_PUBLISH',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'retry_count': 0,
    }
    path.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(path)


def _print_log(result: MessageResult):
    icon = '✅' if result.validation_passed else '⚠️'
    dup = '⚠️ Yes' if result.is_duplicate else '✅ No'

    print(f'''
{'=' * 50}
📩 New Vacancy Detected
  Message #{result.index}
{'=' * 50}''')
    print(f'🏢 Company:       {result.company or "N/A"}')
    print(f'💼 Position:      {result.position or "N/A"}')
    print(f'📍 Location:      {result.location or "N/A"}')
    print(f'💰 Salary:        {result.salary}')

    if result.validation_passed:
        print(f'{icon} Validation Passed  (confidence: {result.validation_confidence:.0%})')
    else:
        print(f'{icon} Validation Failed  (confidence: {result.validation_confidence:.0%})')

    print(f'🔍 Duplicate:     {dup}')

    if result.is_duplicate and result.duplicate_score > 0:
        print(f'   Score:         {result.duplicate_score:.2f}')

    if result.skipped:
        print(f'⏭️  Skipped:       {result.skip_reason}')
    else:
        print(f'💾 Saved to Database  (ID: {result.vacancy_id})')
        if result.poster_path:
            print(f'🎨 Poster Generated  → {result.poster_path}')
        if result.caption_path:
            print(f'📝 Caption Generated → {result.caption_path}')
        if result.ready_package_path:
            print(f'📦 Enqueued for publishing  (Queue #{result.ready_package_path})')
        print('🚀 READY_TO_PUBLISH')

    print('=' * 50)
    sys.stdout.flush()


def process_message(raw: str, index: int, threshold: float = 0.7) -> MessageResult:
    _init_db()
    result = MessageResult(raw_message=raw, index=index)
    t0 = time.time()

    try:
        # Stage 1: Extract
        t1 = time.time()
        cleaned = clean_text(raw)
        jd = VacancyParser().parse(cleaned)
        result.stages.append(StageResult('Extract', True, time.time() - t1))
        result.company = jd.company or ''
        result.position = jd.title or ''
        result.location = jd.location or ''
        result.salary = _fmt_salary(jd)

        # Stage 2: Validate (advisory — low confidence warns but does not block)
        t2 = time.time()
        vr = _validate_extraction(jd, threshold=threshold)
        result.validation_confidence = vr.overall_confidence
        result.validation_passed = not vr.rejected
        result.stages.append(StageResult(
            'Validate', True, time.time() - t2,
            details=f'confidence={vr.overall_confidence:.2f}',
        ))

        # Stage 3: Save to DB
        t3 = time.time()
        reader_pipeline = ReaderPipeline()
        ingest = reader_pipeline.ingest_message(raw, source=f'pipeline:{index}')
        if not ingest.success:
            result.skipped = True
            result.skip_reason = f'DB save failed: {ingest.error}'
            result.stages.append(StageResult('SaveDB', False, time.time() - t3, details=ingest.error))
            _print_log(result)
            return result
        result.vacancy_id = ingest.vacancy_id
        # Populate structured fields + mark as processed so duplicate detector can find it
        with get_session() as session:
            v = session.query(Vacancy).filter(Vacancy.id == result.vacancy_id).first()
            if v:
                v.title = jd.title or v.title
                v.company = jd.company or v.company
                v.description = jd.description or v.description
                v.location = jd.location
                v.salary_min = jd.salary_min
                v.salary_max = jd.salary_max
                v.job_type = jd.job_type
                v.experience_level = jd.experience_level
                v.processed = True
                session.commit()
        result.stages.append(StageResult('SaveDB', True, time.time() - t3, details=f'id={ingest.vacancy_id}'))

        # Stage 4: Duplicate check
        t4 = time.time()
        detector = DuplicateDetector()
        dup = detector.detect(jd, vacancy_id=result.vacancy_id)
        result.is_duplicate = dup.is_duplicate
        result.duplicate_score = dup.similarity_score
        result.stages.append(StageResult(
            'DuplicateCheck', True, time.time() - t4,
            details=f'is_dup={dup.is_duplicate}, score={dup.similarity_score:.2f}',
        ))
        if dup.is_duplicate:
            result.skipped = True
            result.skip_reason = f'Duplicate detected (score: {dup.similarity_score:.2f})'
            _print_log(result)
            return result

        # Stage 5: Generate poster
        t5 = time.time()
        poster_path = _save_poster(result.vacancy_id)
        result.poster_path = poster_path
        result.stages.append(StageResult('Poster', True, time.time() - t5, details=poster_path))

        # Stage 6: Generate caption
        t6 = time.time()
        caption_path, platforms = _save_caption(jd, result.vacancy_id)
        result.caption_path = caption_path
        result.stages.append(StageResult('Caption', True, time.time() - t6, details=caption_path))

        # Stage 7: Enqueue to database
        t7 = time.time()
        from ghost_module.queue_service import enqueue
        qid = enqueue(
            vacancy_id=result.vacancy_id,
            poster_path=str(result.poster_path),
            caption_path=str(result.caption_path),
            platforms=platforms,
        )
        if qid:
            result.ready_package_path = str(qid)
            result.stages.append(StageResult('Enqueue', True, time.time() - t7, details=f'queue_id={qid}'))
        else:
            result.stages.append(StageResult('Enqueue', False, time.time() - t7, details='Enqueue failed'))

    except Exception as e:
        result.skipped = True
        result.skip_reason = f'Pipeline error: {e}'
        result.error = str(e)

    result.stages.append(StageResult('Total', result.error is None, time.time() - t0))
    _print_log(result)
    return result


def run_pipeline(
    input_path: Optional[str] = None,
    raw_messages: Optional[List[str]] = None,
    threshold: float = 0.7,
) -> PipelineResult:
    messages: List[str] = []

    if raw_messages:
        messages = raw_messages
    elif input_path:
        path = Path(input_path)
        if path.is_file():
            messages = [path.read_text(encoding='utf-8')]
        elif path.is_dir():
            reader = FileReader(path)
            messages = reader.read_all()
        else:
            raise FileNotFoundError(f'Input path not found: {input_path}')
    else:
        raise ValueError('Provide either input_path or raw_messages')

    if not messages:
        print('No messages to process.')
        return PipelineResult()

    t_start = time.time()
    pipeline_result = PipelineResult(total=len(messages))

    for idx, raw in enumerate(messages, 1):
        if not raw.strip():
            pipeline_result.skipped += 1
            continue
        mr = process_message(raw.strip(), idx, threshold=threshold)
        pipeline_result.messages.append(mr)
        if mr.skipped:
            pipeline_result.skipped += 1
        elif mr.error:
            pipeline_result.failed += 1
        else:
            pipeline_result.processed += 1

    pipeline_result.duration = time.time() - t_start

    duration_str = f'{pipeline_result.duration:.2f}s'
    print(f'''
{'=' * 50}
PIPELINE SUMMARY
{'=' * 50}
  Total messages:   {pipeline_result.total}
  Processed:        {pipeline_result.processed}
  Skipped:          {pipeline_result.skipped}
  Failed:           {pipeline_result.failed}
  Duration:         {duration_str}
{'=' * 50}''')
    sys.stdout.flush()
    return pipeline_result


runPipeline = run_pipeline
