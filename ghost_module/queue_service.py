from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import QueueItem
from database.session import get_session
from captions import PLATFORMS

PLATFORM_NAMES: List[str] = sorted(PLATFORMS)


@dataclass
class QueueStats:
    total: int = 0
    queued: int = 0
    publishing: int = 0
    published: int = 0
    failed: int = 0
    partially_published: int = 0
    draft: int = 0
    retry_count: int = 0
    avg_publish_time: Optional[float] = None


def enqueue(
    vacancy_id: int,
    poster_path: str,
    caption_path: str,
    platforms: Optional[List[str]] = None,
) -> Optional[int]:
    _init_db()
    platforms = platforms or PLATFORM_NAMES
    platform_states = {p: {'status': 'queued', 'retry_count': 0} for p in platforms}
    with get_session() as session:
        item = QueueItem(
            vacancy_id=vacancy_id,
            status='queued',
            platforms=platforms,
            platform_states=platform_states,
            poster_path=poster_path,
            caption_path=caption_path,
            retry_count=0,
            max_retries=3,
        )
        session.add(item)
        session.commit()
        qid = item.id
    return qid


def get_queue(filters: Optional[Dict[str, Any]] = None) -> List[QueueItem]:
    _init_db()
    filters = filters or {}
    with get_session() as session:
        q = session.query(QueueItem)
        if 'status' in filters and filters['status']:
            q = q.filter(QueueItem.status == filters['status'])
        if 'vacancy_id' in filters:
            q = q.filter(QueueItem.vacancy_id == filters['vacancy_id'])
        q = q.order_by(QueueItem.created_at.desc())
        if 'limit' in filters:
            q = q.limit(filters['limit'])
        items = q.all()
    return items


def get_queue_item(queue_id: int) -> Optional[QueueItem]:
    _init_db()
    with get_session() as session:
        return session.query(QueueItem).filter(QueueItem.id == queue_id).first()


def get_queue_item_by_vacancy(vacancy_id: int) -> Optional[QueueItem]:
    _init_db()
    with get_session() as session:
        return session.query(QueueItem).filter(
            QueueItem.vacancy_id == vacancy_id
        ).order_by(QueueItem.created_at.desc()).first()


def update_status(queue_id: int, status: str, **extra) -> bool:
    _init_db()
    with get_session() as session:
        item = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not item:
            return False
        item.status = status
        if status == 'published':
            item.published_at = datetime.utcnow()
        if 'error_message' in extra:
            item.error_message = extra['error_message']
        if 'platform_states' in extra:
            item.platform_states = extra['platform_states']
        if 'retry_count' in extra:
            item.retry_count = extra['retry_count']
        session.commit()
        return True


def update_platform_state(
    queue_id: int,
    platform: str,
    status: str,
    error: Optional[str] = None,
    platform_post_id: Optional[str] = None,
) -> bool:
    _init_db()
    with get_session() as session:
        item = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not item:
            return False
        states = dict(item.platform_states or {})
        state = dict(states.get(platform, {}))
        state['status'] = status
        if error:
            state['error'] = error
        if platform_post_id:
            state['platform_post_id'] = platform_post_id
            state['published_at'] = datetime.utcnow().isoformat()
        states[platform] = state
        item.platform_states = states
        # Derive overall status from per-platform states
        all_statuses = [s.get('status') for s in states.values()]
        if all(s == 'published' for s in all_statuses):
            item.status = 'published'
            item.published_at = datetime.utcnow()
        elif any(s == 'failed' for s in all_statuses) and any(s == 'published' for s in all_statuses):
            item.status = 'partially_published'
        elif all(s == 'failed' for s in all_statuses):
            item.status = 'failed'
        session.commit()
        return True


def increment_retry(queue_id: int) -> bool:
    _init_db()
    with get_session() as session:
        item = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not item:
            return False
        item.retry_count = (item.retry_count or 0) + 1
        item.status = 'queued'
        session.commit()
        return True


def retry_failed(queue_id: int) -> bool:
    return increment_retry(queue_id)


def retry_failed_all() -> int:
    _init_db()
    count = 0
    with get_session() as session:
        items = session.query(QueueItem).filter(
            QueueItem.status.in_(['failed', 'partially_published'])
        ).all()
        for item in items:
            item.status = 'queued'
            item.retry_count = (item.retry_count or 0) + 1
            item.error_message = None
            states = dict(item.platform_states or {})
            for p in states:
                if states[p].get('status') == 'failed':
                    states[p]['status'] = 'queued'
            item.platform_states = states
            count += 1
        session.commit()
    return count


def delete_queue_item(queue_id: int) -> bool:
    _init_db()
    with get_session() as session:
        item = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not item:
            return False
        session.delete(item)
        session.commit()
        return True


def get_stats() -> QueueStats:
    _init_db()
    stats = QueueStats()
    with get_session() as session:
        items = session.query(QueueItem).all()
        stats.total = len(items)
        for item in items:
            if item.status == 'queued':
                stats.queued += 1
            elif item.status == 'publishing':
                stats.publishing += 1
            elif item.status == 'published':
                stats.published += 1
            elif item.status == 'failed':
                stats.failed += 1
            elif item.status == 'partially_published':
                stats.partially_published += 1
            elif item.status == 'draft':
                stats.draft += 1
            if item.retry_count and item.retry_count > 0:
                stats.retry_count += item.retry_count
        # Calculate average publish time for published items
        published = [i for i in items if i.status == 'published' and i.published_at and i.created_at]
        if published:
            diffs = [
                (i.published_at - i.created_at).total_seconds()
                for i in published
            ]
            stats.avg_publish_time = sum(diffs) / len(diffs)
    return stats


def require_migration():
    _init_db()
