from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database.init import init_db as _init_db
from database.models import SocialAccount
from database.session import get_session
from ghost_module.social_service import get_accounts, update_account

logger = logging.getLogger('ghost.health')

PLATFORM_HEALTH: Dict[str, Dict[str, Any]] = {}
HEALTH_TTL = timedelta(minutes=5)


def _check_facebook(account: SocialAccount) -> Tuple[bool, Optional[str]]:
    token = account.access_token
    if not token:
        return False, 'No access token'
    now = datetime.utcnow()
    if account.token_expires_at and account.token_expires_at < now:
        return False, 'Token expired'
    return True, None


def _check_linkedin(account: SocialAccount) -> Tuple[bool, Optional[str]]:
    token = account.access_token
    if not token:
        return False, 'No access token'
    return True, None


def _check_instagram(account: SocialAccount) -> Tuple[bool, Optional[str]]:
    token = account.access_token
    if not token:
        return False, 'No access token'
    return True, None


def _check_twitter(account: SocialAccount) -> Tuple[bool, Optional[str]]:
    token = account.access_token
    if not token:
        return False, 'No access token'
    return True, None


def _check_telegram(account: SocialAccount) -> Tuple[bool, Optional[str]]:
    token = account.access_token
    if not token:
        return False, 'No access token'
    bot_token = (account.extra_data or {}).get('bot_token', account.access_token)
    if not bot_token:
        return False, 'No bot token'
    return True, None


_CHECKERS = {
    'facebook': _check_facebook,
    'linkedin': _check_linkedin,
    'instagram': _check_instagram,
    'twitter': _check_twitter,
    'telegram': _check_telegram,
}


def check_platform_account(account: SocialAccount) -> Dict[str, Any]:
    platform = account.platform
    check = _CHECKERS.get(platform)
    if not check:
        return {'healthy': False, 'error': f'No health checker for {platform}'}

    try:
        healthy, error = check(account)
        return {
            'healthy': healthy,
            'error': error,
            'checked_at': datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {'healthy': False, 'error': str(e), 'checked_at': datetime.utcnow().isoformat()}


def health_status(platform: Optional[str] = None) -> Dict[str, Any]:
    _init_db()
    accounts = get_accounts(platform=platform, active_only=True)
    results = {}

    for acc in accounts:
        key = f"{acc.platform}/{acc.id}"
        cached = PLATFORM_HEALTH.get(key)
        if cached and datetime.utcnow() - cached.get('_checked_at') < HEALTH_TTL:
            results[key] = dict(cached)
            results[key]['cached'] = True
            continue

        check = check_platform_account(acc)
        PLATFORM_HEALTH[key] = check | {'_checked_at': datetime.utcnow()}
        results[key] = check | {'cached': False}

    overall = all(v.get('healthy') for v in results.values()) if results else False
    return {
        'overall_healthy': overall,
        'accounts': results,
        'total': len(results),
        'healthy': sum(1 for v in results.values() if v.get('healthy')),
        'unhealthy': sum(1 for v in results.values() if not v.get('healthy')),
    }


def is_platform_ready(platform: str) -> bool:
    status = health_status(platform=platform)
    return status['overall_healthy']


def auto_disable_unhealthy() -> int:
    _init_db()
    status = health_status()
    disabled = 0
    for key, info in status['accounts'].items():
        if not info.get('healthy'):
            platform, aid = key.split('/')
            update_account(int(aid), is_active=False)
            logger.warning(f'Auto-disabled {key}: {info.get("error")}')
            disabled += 1
    return disabled
