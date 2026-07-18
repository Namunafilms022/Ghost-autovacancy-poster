from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import PublishLog, QueueItem, SocialAccount, Vacancy
from database.session import get_session


def log_publish(
    vacancy_id: int,
    platform: str,
    status: str,
    error: Optional[str] = None,
    platform_post_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> int:
    _init_db()
    with get_session() as session:
        log = PublishLog(
            vacancy_id=vacancy_id,
            platform=platform,
            status=status,
            error=error,
            platform_post_id=platform_post_id,
            duration_ms=duration_ms,
        )
        session.add(log)
        session.commit()
        return log.id


def get_overview(days: int = 30) -> Dict[str, Any]:
    _init_db()
    cutoff = datetime.utcnow() - timedelta(days=days)

    with get_session() as session:
        logs = session.query(PublishLog).filter(
            PublishLog.created_at >= cutoff
        ).all()

        queue_items = session.query(QueueItem).filter(
            QueueItem.created_at >= cutoff
        ).all()

        total_logs = len(logs)
        published = sum(1 for l in logs if l.status == 'published')
        failed = sum(1 for l in logs if l.status == 'failed')
        success_rate = (published / total_logs * 100) if total_logs else 0.0

        platform_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'published': 0, 'failed': 0, 'total': 0}
        )
        for l in logs:
            ps = platform_stats[l.platform]
            ps['total'] += 1
            if l.status == 'published':
                ps['published'] += 1
            elif l.status == 'failed':
                ps['failed'] += 1

        daily: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'published': 0, 'failed': 0, 'total': 0}
        )
        for l in logs:
            day = l.created_at.strftime('%Y-%m-%d')
            d = daily[day]
            d['total'] += 1
            if l.status == 'published':
                d['published'] += 1
            elif l.status == 'failed':
                d['failed'] += 1

        avg_duration = 0.0
        durations = [l.duration_ms for l in logs if l.duration_ms]
        if durations:
            avg_duration = sum(durations) / len(durations)

        now = datetime.utcnow()

        already_posted = session.query(Vacancy.id).filter(
            Vacancy.id.in_([l.vacancy_id for l in logs])
        ).count()

    return {
        'period_days': days,
        'total_publish_attempts': total_logs,
        'total_published': published,
        'total_failed': failed,
        'success_rate': round(success_rate, 1),
        'avg_duration_ms': round(avg_duration, 0),
        'unique_vacancies_posted': already_posted,
        'platform_breakdown': dict(platform_stats),
        'daily_trend': dict(sorted(daily.items())),
        'total_queue_items': len(queue_items),
        'queue_health': {
            'queued': sum(1 for q in queue_items if q.status == 'queued'),
            'published': sum(1 for q in queue_items if q.status == 'published'),
            'failed': sum(1 for q in queue_items if q.status == 'failed'),
            'partial': sum(1 for q in queue_items if q.status == 'partially_published'),
        },
    }


def get_recent_activity(limit: int = 20) -> List[Dict[str, Any]]:
    _init_db()
    with get_session() as session:
        logs = session.query(PublishLog).order_by(
            PublishLog.created_at.desc()
        ).limit(limit).all()
        return [{
            'id': l.id,
            'vacancy_id': l.vacancy_id,
            'platform': l.platform,
            'status': l.status,
            'error': l.error,
            'duration_ms': l.duration_ms,
            'created_at': l.created_at.isoformat() if l.created_at else None,
        } for l in logs]


def get_platform_failure_rate(days: int = 30) -> Dict[str, float]:
    _init_db()
    cutoff = datetime.utcnow() - timedelta(days=days)
    with get_session() as session:
        logs = session.query(PublishLog).filter(
            PublishLog.created_at >= cutoff
        ).all()
        platform_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'total': 0, 'failed': 0}
        )
        for l in logs:
            platform_counts[l.platform]['total'] += 1
            if l.status == 'failed':
                platform_counts[l.platform]['failed'] += 1
        return {
            p: round(c['failed'] / c['total'] * 100, 1) if c['total'] else 0.0
            for p, c in platform_counts.items()
        }
