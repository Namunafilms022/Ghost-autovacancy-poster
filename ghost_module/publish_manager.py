from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import QueueItem, Vacancy
from database.session import get_session
from ghost_module.queue_service import (
    update_platform_state, update_status, increment_retry,
)
from ghost_module.social_service import get_accounts


def _load_poster_html(poster_path: str) -> Optional[str]:
    p = Path(poster_path)
    if p.exists():
        return p.read_text(encoding='utf-8')
    return None


def _load_caption_data(caption_path: str) -> Optional[Dict]:
    p = Path(caption_path)
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return None


def _dispatch_facebook(
    vacancy_id: int,
    account: Dict[str, Any],
    poster_html: Optional[str],
    caption_data: Optional[Dict],
) -> Dict[str, Any]:
    from publisher.facebook import FacebookPublisher
    from poster.poster import PosterGenerator

    group_ids = (account.get('extra_data') or {}).get('group_ids', [])
    if not group_ids:
        return {'status': 'failed', 'error': 'No Facebook group IDs configured'}

    gen = PosterGenerator()
    fb = FacebookPublisher(
        access_token=account['token'],
        group_ids=group_ids,
        poster_generator=gen,
    )
    result = fb.publish(vacancy_id)
    return {
        'status': 'published' if result.success else 'failed',
        'error': result.error,
        'platform_post_id': result.post_id,
    }


def _dispatch_linkedin(
    vacancy_id: int,
    account: Dict[str, Any],
    poster_html: Optional[str],
    caption_data: Optional[Dict],
) -> Dict[str, Any]:
    return {'status': 'failed', 'error': 'LinkedIn publisher not yet implemented'}


def _dispatch_instagram(
    vacancy_id: int,
    account: Dict[str, Any],
    poster_html: Optional[str],
    caption_data: Optional[Dict],
) -> Dict[str, Any]:
    return {'status': 'failed', 'error': 'Instagram publisher not yet implemented'}


def _dispatch_twitter(
    vacancy_id: int,
    account: Dict[str, Any],
    poster_html: Optional[str],
    caption_data: Optional[Dict],
) -> Dict[str, Any]:
    return {'status': 'failed', 'error': 'Twitter publisher not yet implemented'}


def _dispatch_telegram(
    vacancy_id: int,
    account: Dict[str, Any],
    poster_html: Optional[str],
    caption_data: Optional[Dict],
) -> Dict[str, Any]:
    return {'status': 'failed', 'error': 'Telegram publisher not yet implemented'}


_DISPATCHERS = {
    'facebook': _dispatch_facebook,
    'linkedin': _dispatch_linkedin,
    'instagram': _dispatch_instagram,
    'twitter': _dispatch_twitter,
    'telegram': _dispatch_telegram,
}


def publish_queue_item(queue_id: int) -> Dict[str, Any]:
    _init_db()

    with get_session() as session:
        qi = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if not qi:
            return {'success': False, 'error': 'Queue item not found'}

        if qi.status not in ('queued', 'failed', 'partially_published'):
            return {'success': False, 'error': f"Item status is '{qi.status}', cannot publish"}

        qi.status = 'publishing'
        session.commit()

        vacancy_id = qi.vacancy_id
        target_platforms = list(qi.platforms or [])
        poster_path = qi.poster_path
        caption_path = qi.caption_path
        retry_count = qi.retry_count or 0
        max_retries = qi.max_retries or 3

    poster_html = _load_poster_html(poster_path) if poster_path else None
    caption_data = _load_caption_data(caption_path) if caption_path else None
    results: Dict[str, Dict[str, Any]] = {}

    for platform in target_platforms:
        accounts = get_accounts(platform=platform, active_only=True)
        if not accounts:
            results[platform] = {'status': 'failed', 'error': f'No active {platform} account configured'}
            update_platform_state(queue_id, platform, 'failed', error=f'No active {platform} account')
            continue

        account_dict = {
            'id': accounts[0].id,
            'name': accounts[0].account_name,
            'account_id': accounts[0].account_id,
            'token': accounts[0].access_token,
            'extra_data': accounts[0].extra_data or {},
        }

        dispatcher = _DISPATCHERS.get(platform)
        if not dispatcher:
            results[platform] = {'status': 'failed', 'error': f'No dispatcher for {platform}'}
            update_platform_state(queue_id, platform, 'failed', error=f'No dispatcher')
            continue

        from ghost_module.health import is_platform_ready
        if not is_platform_ready(platform):
            err = f'{platform} health check failed, skipping'
            results[platform] = {'status': 'failed', 'error': err}
            update_platform_state(queue_id, platform, 'failed', error=err)
            continue

        try:
            start = time.time()
            result = dispatcher(vacancy_id, account_dict, poster_html, caption_data)
            duration_ms = int((time.time() - start) * 1000)
            results[platform] = result
            update_platform_state(
                queue_id, platform,
                status=result.get('status', 'failed'),
                error=result.get('error'),
                platform_post_id=result.get('platform_post_id'),
            )
            from ghost_module.analytics import log_publish
            log_publish(
                vacancy_id=vacancy_id,
                platform=platform,
                status=result.get('status', 'failed'),
                error=result.get('error'),
                platform_post_id=result.get('platform_post_id'),
                duration_ms=duration_ms,
            )
        except Exception as e:
            results[platform] = {'status': 'failed', 'error': str(e)}
            update_platform_state(queue_id, platform, 'failed', error=str(e))
            from ghost_module.analytics import log_publish
            log_publish(
                vacancy_id=vacancy_id,
                platform=platform,
                status='failed',
                error=str(e),
            )

    with get_session() as session:
        qi2 = session.query(QueueItem).filter(QueueItem.id == queue_id).first()
        if qi2:
            all_statuses = [
                s.get('status') for s in (qi2.platform_states or {}).values()
            ]
            if all(s == 'published' for s in all_statuses):
                qi2.status = 'published'
                qi2.published_at = datetime.utcnow()
                qi2.scheduled_at = None
                qi2.retry_count = 0
            elif any(s == 'published' for s in all_statuses):
                qi2.status = 'partially_published'
                qi2.scheduled_at = None
            elif all(s == 'failed' for s in all_statuses):
                qi2.error_message = '; '.join(
                    r.get('error', '') for r in results.values() if r.get('error')
                )
                if retry_count < max_retries:
                    backoff = min(30 * (2 ** retry_count), 300)
                    qi2.scheduled_at = datetime.utcnow() + timedelta(seconds=backoff)
                    qi2.status = 'queued'
                    qi2.retry_count = retry_count + 1
                else:
                    qi2.status = 'failed'
            session.commit()

    success = any(
        r.get('status') == 'published' for r in results.values()
    )
    return {
        'success': success,
        'results': results,
    }


def publish_pending() -> Dict[str, Any]:
    _init_db()
    with get_session() as session:
        items = session.query(QueueItem).filter(
            QueueItem.status == 'queued'
        ).order_by(QueueItem.created_at.asc()).all()
        ids = [i.id for i in items]

    results = {}
    for qid in ids:
        results[qid] = publish_queue_item(qid)
    return {
        'total': len(ids),
        'published': sum(1 for r in results.values() if r.get('success')),
        'results': {str(k): v for k, v in results.items()},
    }
