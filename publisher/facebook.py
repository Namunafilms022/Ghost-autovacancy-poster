from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

from database.models import PublishedPost, Vacancy
from database.session import get_session
from poster.poster import PosterGenerator
from .base import BasePublisher, PublishResult


def _load_facebook_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('facebook', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _generate_poster_text(vacancy) -> str:
    lines = []
    if vacancy.title:
        lines.append(f"📌 *{vacancy.title}*")
    if vacancy.company:
        lines.append(f"🏢 {vacancy.company}")
    if vacancy.location:
        lines.append(f"📍 {vacancy.location}")
    if vacancy.salary_min is not None and vacancy.salary_max is not None:
        lines.append(f"💰 Rs. {vacancy.salary_min:,.0f} - Rs. {vacancy.salary_max:,.0f}/month")
    elif vacancy.salary_min is not None:
        lines.append(f"💰 Rs. {vacancy.salary_min:,.0f}+/month")
    if vacancy.job_type:
        jt = vacancy.job_type.replace('_', ' ').title()
        lines.append(f"💼 {jt}")
    if vacancy.experience_level:
        el = vacancy.experience_level.replace('_', ' ').title()
        lines.append(f"📊 {el}")
    lines.append(f"\n🔗 Poster: generated")
    return '\n'.join(lines)


class FacebookPublisher(BasePublisher):
    platform = 'facebook'

    def __init__(self, access_token: Optional[str] = None,
                 group_ids: Optional[List[str]] = None,
                 api_version: str = 'v18.0',
                 poster_generator: Optional[PosterGenerator] = None):
        config = _load_facebook_config()
        self.access_token = access_token or config.get('access_token', '')
        self.group_ids = group_ids or config.get('group_ids', [])
        self.api_version = api_version or config.get('api_version', 'v18.0')
        self._poster = poster_generator or PosterGenerator()

    def publish(self, vacancy_id: int) -> PublishResult:
        if not self.access_token:
            return PublishResult(
                platform=self.platform, vacancy_id=vacancy_id,
                success=False, error='Facebook access token not configured'
            )
        if not self.group_ids:
            return PublishResult(
                platform=self.platform, vacancy_id=vacancy_id,
                success=False, error='No Facebook group IDs configured'
            )

        session = get_session()
        try:
            vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if not vacancy:
                return PublishResult(
                    platform=self.platform, vacancy_id=vacancy_id,
                    success=False, error=f'Vacancy {vacancy_id} not found'
                )

            html = self._poster.generate(vacancy_id)
            message = _generate_poster_text(vacancy)
            last_error = None
            first_post_id = None
            first_url = None

            for group_id in self.group_ids:
                try:
                    resp = requests.post(
                        f'https://graph.facebook.com/{self.api_version}/{group_id}/feed',
                        params={
                            'access_token': self.access_token,
                            'message': message,
                            'link': '',  # placeholder for hosted poster URL
                        },
                        timeout=30,
                    )
                    data = resp.json()

                    if resp.status_code == 200 and 'id' in data:
                        post_id = str(data['id'])
                        if first_post_id is None:
                            first_post_id = post_id
                            first_url = f'https://facebook.com/groups/{group_id}/posts/{post_id}'

                        self._save_post_record(vacancy_id, group_id, post_id, 'published', first_url)
                    else:
                        error_msg = data.get('error', {}).get('message', str(data))
                        self._save_post_record(vacancy_id, group_id, None, 'failed')
                        last_error = error_msg
                except requests.RequestException as e:
                    self._save_post_record(vacancy_id, group_id, None, 'failed')
                    last_error = str(e)

            if first_post_id:
                return PublishResult(
                    platform=self.platform, vacancy_id=vacancy_id,
                    success=True, post_id=first_post_id,
                    url=first_url,
                )
            return PublishResult(
                platform=self.platform, vacancy_id=vacancy_id,
                success=False, error=last_error or 'All groups failed',
            )
        finally:
            session.close()

    def get_status(self, post_id: str) -> str:
        if not self.access_token:
            return 'unknown'
        try:
            resp = requests.get(
                f'https://graph.facebook.com/{self.api_version}/{post_id}',
                params={'access_token': self.access_token, 'fields': 'id,status'},
                timeout=15,
            )
            data = resp.json()
            if resp.status_code == 200:
                return data.get('status', 'published')
            return 'unknown'
        except requests.RequestException:
            return 'unknown'

    def _save_post_record(self, vacancy_id: int, group_id: str,
                          post_id: Optional[str], status: str,
                          url: Optional[str] = None) -> None:
        session = get_session()
        try:
            record = PublishedPost(
                vacancy_id=vacancy_id,
                platform=f'facebook:group:{group_id}',
                external_id=post_id,
                status=status,
                url=url,
                published_at=datetime.utcnow() if status == 'published' else None,
            )
            session.add(record)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
