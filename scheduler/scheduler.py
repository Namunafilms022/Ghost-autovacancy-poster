from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database.init import init_db
from database.session import get_session
from database.models import Vacancy
from reader import FileReader, ReaderPipeline
from parser import VacancyParser
from normalizer import Normalizer
from duplicate import DuplicateDetector
from poster import PosterGenerator
from publisher import FacebookPublisher, PublisherPipeline

log = logging.getLogger('scheduler')

_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'settings.json'


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            cfg = json.load(f)
        return cfg.get('scheduler', {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.warning('Failed to load scheduler config: %s', e)
        return {}


def _get_facebook_config() -> tuple[str, list[str]]:
    try:
        with open(_CONFIG_PATH) as f:
            cfg = json.load(f)
        fb = cfg.get('facebook', {})
        return fb.get('access_token', ''), fb.get('group_ids', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return '', []


def scheduled_job():
    log.info('Scheduled job started at %s', datetime.now().isoformat())
    init_db()
    pipeline_dir = Path('vacancies')

    if not pipeline_dir.exists():
        log.warning('vacancies/ directory not found, skipping')
        return

    messages = FileReader(pipeline_dir).read_all()
    if not messages:
        log.info('No vacancy files found in vacancies/')
        return

    log.info('Found %d vacancy file(s)', len(messages))

    parser = VacancyParser()
    reader_pipeline = ReaderPipeline()
    normalizer = Normalizer()
    detector = DuplicateDetector()
    poster = PosterGenerator()

    pub_pipeline = PublisherPipeline()
    token, groups = _get_facebook_config()
    if token and groups:
        fb = FacebookPublisher(access_token=token, group_ids=groups)
        pub_pipeline.add_publisher(fb)
        log.info('Facebook publisher configured with %d group(s)', len(groups))

    for idx, raw in enumerate(messages, 1):
        try:
            log.info('[%d/%d] Processing...', idx, len(messages))
            details = parser.parse(raw)
            if not details:
                log.warning('[%d] Parse returned None, skipping', idx)
                continue

            log.info('  Title: %s | Company: %s', details.title, details.company)

            result = reader_pipeline.ingest_message(raw, source=f'scheduler:{idx}')
            if not result.success:
                log.warning('[%d] DB ingest failed: %s', idx, result.error)
                continue

            vid = result.vacancy_id
            log.info('[%d] Saved as vacancy #%d', idx, vid)

            normalizer.normalize(details, vid)
            dup_result = detector.detect(details, vacancy_id=vid)
            if dup_result.is_duplicate:
                log.info('[%d] Duplicate of #%d (score=%.2f)', idx,
                         dup_result.matched_vacancy_id, dup_result.similarity_score)

            poster.generate(vid)
            log.info('[%d] Poster generated', idx)

            if pub_pipeline.publishers:
                pub_results = pub_pipeline.publish(vid)
                for r in pub_results:
                    if r.success:
                        log.info('[%d] Published to %s (id=%s)', idx, r.platform, r.post_id)
                    else:
                        log.warning('[%d] Publish to %s failed: %s', idx, r.platform, r.error)
        except Exception as e:
            log.exception('[%d] Error processing message: %s', idx, e)

    log.info('Scheduled job finished')


class Scheduler:
    def __init__(self):
        self._scheduler: Optional[BackgroundScheduler] = None
        self._config = _load_config()
        self._running = False

    def start(self):
        if self._running:
            log.warning('Scheduler already running')
            return

        if not self._config.get('enabled', True):
            log.info('Scheduler disabled in config')
            return

        self._scheduler = BackgroundScheduler(daemon=True, timezone='UTC')

        time_str = self._config.get('time', '09:00')
        tz = self._config.get('timezone', 'Asia/Kathmandu')

        try:
            hour, minute = map(int, time_str.split(':'))
        except (ValueError, AttributeError):
            log.warning('Invalid scheduler time "%s", using 09:00', time_str)
            hour, minute = 9, 0

        trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
        self._scheduler.add_job(
            scheduled_job,
            trigger=trigger,
            id='daily_vacancy_pipeline',
            name='Daily vacancy pipeline',
            replace_existing=True,
        )
        self._scheduler.start()
        self._running = True
        log.info('Scheduler started — daily at %s %s', time_str, tz)

    def stop(self):
        if not self._running or self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._running = False
        log.info('Scheduler stopped')

    @property
    def running(self) -> bool:
        return self._running

    def get_jobs(self):
        if self._scheduler is None:
            return []
        return self._scheduler.get_jobs()
