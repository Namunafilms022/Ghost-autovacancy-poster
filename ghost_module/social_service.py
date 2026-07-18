from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from database.init import init_db as _init_db
from database.models import SocialAccount
from database.session import get_session

PLATFORM_ICONS = {
    'facebook': '📘', 'linkedin': '💼', 'instagram': '📸',
    'twitter': '🐦', 'telegram': '✈️',
}
PLATFORM_COLORS = {
    'facebook': '#1877F2', 'linkedin': '#0A66C2', 'instagram': '#E4405F',
    'twitter': '#1DA1F2', 'telegram': '#0088CC',
}


def get_accounts(platform: Optional[str] = None, active_only: bool = True) -> List[SocialAccount]:
    _init_db()
    with get_session() as session:
        q = session.query(SocialAccount)
        if platform:
            q = q.filter(SocialAccount.platform == platform)
        if active_only:
            q = q.filter(SocialAccount.is_active == True)
        return q.order_by(SocialAccount.created_at.desc()).all()


def get_account(account_id: int) -> Optional[SocialAccount]:
    _init_db()
    with get_session() as session:
        return session.query(SocialAccount).filter(SocialAccount.id == account_id).first()


def add_account(
    platform: str,
    account_name: str,
    account_id: Optional[str] = None,
    access_token: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    _init_db()
    platform = platform.lower().strip()
    if platform not in SocialAccount.PLATFORMS:
        raise ValueError(f"Unsupported platform '{platform}'. Supported: {SocialAccount.PLATFORMS}")
    with get_session() as session:
        acct = SocialAccount(
            platform=platform,
            account_name=account_name.strip(),
            account_id=account_id,
            access_token=access_token,
            is_active=True,
            extra_data=extra_data or {},
        )
        session.add(acct)
        session.commit()
        return acct.id


def update_account(
    account_id: int,
    **kwargs,
) -> bool:
    _init_db()
    allowed = {'account_name', 'account_id', 'access_token', 'token_expires_at',
               'refresh_token', 'is_active', 'extra_data'}
    with get_session() as session:
        acct = session.query(SocialAccount).filter(SocialAccount.id == account_id).first()
        if not acct:
            return False
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(acct, k, v)
        session.commit()
        return True


def delete_account(account_id: int) -> bool:
    _init_db()
    with get_session() as session:
        acct = session.query(SocialAccount).filter(SocialAccount.id == account_id).first()
        if not acct:
            return False
        session.delete(acct)
        session.commit()
        return True


def get_active_publishers() -> Dict[str, List[Dict[str, Any]]]:
    accounts = get_accounts(active_only=True)
    publishers = {}
    for acct in accounts:
        p = acct.platform
        if p not in publishers:
            publishers[p] = []
        publishers[p].append({
            'id': acct.id,
            'name': acct.account_name,
            'account_id': acct.account_id,
            'token': acct.access_token,
            'extra_data': acct.extra_data or {},
        })
    return publishers
