from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger('ghost.alert')


def send_alert(message: str) -> bool:
    try:
        from config.env_loader import get_config
        cfg = get_config().get('telegram', {})
        bot_token = cfg.get('bot_token', '')
        chat_id = cfg.get('chat_id', '')

        if not bot_token or not chat_id:
            return False

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': f'🚨 Ghost AutoVacancy Alert\n\n{message}',
            'parse_mode': 'Markdown',
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f'Failed to send Telegram alert: {e}')
        return False
