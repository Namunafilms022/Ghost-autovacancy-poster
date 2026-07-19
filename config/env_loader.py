from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _load_json_config() -> Dict[str, Any]:
    path = Path(__file__).parent / 'settings.json'
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def get_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg = _load_json_config()
    app_cfg = cfg.get('app', {})

    app_cfg['environment'] = os.getenv('APP_ENVIRONMENT', app_cfg.get('environment', 'development'))
    app_cfg['debug'] = os.getenv('APP_DEBUG', str(app_cfg.get('debug', 'false'))).lower() == 'true'
    app_cfg['log_level'] = os.getenv('APP_LOG_LEVEL', app_cfg.get('log_level', 'INFO'))

    cfg['app'] = app_cfg

    cfg.setdefault('database', {})['path'] = os.getenv('DATABASE_PATH', cfg['database'].get('path', './ghost_vacancies.db'))

    cfg.setdefault('poster_contact', {})['replace_phone'] = os.getenv('POSTER_REPLACE_PHONE', cfg['poster_contact'].get('replace_phone', ''))
    cfg.setdefault('poster_contact', {})['replace_email'] = os.getenv('POSTER_REPLACE_EMAIL', cfg['poster_contact'].get('replace_email', ''))

    fb = cfg.setdefault('facebook', {})
    fb['access_token'] = os.getenv('FACEBOOK_ACCESS_TOKEN', fb.get('access_token', ''))
    fb['api_version'] = os.getenv('FACEBOOK_API_VERSION', fb.get('api_version', 'v18.0'))
    group_ids = os.getenv('FACEBOOK_GROUP_IDS', '')
    if group_ids:
        fb['group_ids'] = [g.strip() for g in group_ids.split(',') if g.strip()]

    cfg.setdefault('dashboard', {})
    cfg['dashboard']['user'] = os.getenv('DASHBOARD_USER', 'admin')
    cfg['dashboard']['password'] = os.getenv('DASHBOARD_PASSWORD', '')

    cfg.setdefault('telegram', {})
    cfg['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN', '')
    cfg['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID', '')

    _CONFIG_CACHE = cfg
    return cfg
