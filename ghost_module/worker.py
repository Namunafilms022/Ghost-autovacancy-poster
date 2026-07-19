from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from database.init import init_db as _init_db

logger = logging.getLogger('ghost.worker')

WORKER_STATE = {
    'running': False,
    'thread': None,
    'started_at': None,
    'processed': 0,
    'failed': 0,
    'last_run': None,
    'poll_interval': 30,
}

STATE_FILE = Path('data/worker_state.json')


def _save_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'running': WORKER_STATE['running'],
        'started_at': WORKER_STATE['started_at'],
        'processed': WORKER_STATE['processed'],
        'failed': WORKER_STATE['failed'],
        'last_run': WORKER_STATE['last_run'],
        'poll_interval': WORKER_STATE['poll_interval'],
    }
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


def _load_state():
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
            WORKER_STATE.update(data)
        except (json.JSONDecodeError, OSError):
            pass


def _publish_loop():
    from ghost_module.alert import send_alert
    from ghost_module.automation import process_pending_scheduled, apply_rules_to_queue
    from ghost_module.queue_service import get_queue
    from ghost_module.publish_manager import publish_queue_item

    while WORKER_STATE['running']:
        loop_failures = 0
        try:
            ready_ids = process_pending_scheduled()
            if ready_ids:
                logger.info(f'Worker released {len(ready_ids)} scheduled item(s)')

            items = get_queue({'status': 'queued'})
            if items:
                logger.info(f'Worker picked {len(items)} queued item(s)')
                for qi in items:
                    if not WORKER_STATE['running']:
                        break
                    if qi.scheduled_at:
                        continue
                    try:
                        apply_rules_to_queue(qi.id)
                    except Exception:
                        pass
                    try:
                        result = publish_queue_item(qi.id)
                        if result.get('success'):
                            WORKER_STATE['processed'] += 1
                        else:
                            WORKER_STATE['failed'] += 1
                            loop_failures += 1
                    except Exception as e:
                        logger.error(f'Worker error on item {qi.id}: {e}')
                        WORKER_STATE['failed'] += 1
                        loop_failures += 1

            if loop_failures >= 3:
                send_alert(
                    f'Worker failed {loop_failures} items in last cycle.\n'
                    f'Total processed: {WORKER_STATE["processed"]}\n'
                    f'Total failed: {WORKER_STATE["failed"]}'
                )

            WORKER_STATE['last_run'] = datetime.utcnow().isoformat()
            _save_state()
        except Exception as e:
            logger.error(f'Worker loop error: {e}')
            send_alert(f'Worker loop crashed: {e}')

        for _ in range(WORKER_STATE['poll_interval']):
            if not WORKER_STATE['running']:
                break
            time.sleep(1)


def start_worker(poll_interval: int = 30) -> bool:
    _load_state()
    if WORKER_STATE['running']:
        logger.warning('Worker already running')
        return False

    _init_db()
    WORKER_STATE['running'] = True
    WORKER_STATE['started_at'] = datetime.utcnow().isoformat()
    WORKER_STATE['processed'] = 0
    WORKER_STATE['failed'] = 0
    WORKER_STATE['poll_interval'] = poll_interval
    WORKER_STATE['last_run'] = None

    thread = threading.Thread(target=_publish_loop, daemon=True)
    thread.start()
    WORKER_STATE['thread'] = thread
    _save_state()
    logger.info(f'Worker started (poll every {poll_interval}s)')
    return True


def stop_worker() -> bool:
    if not WORKER_STATE['running']:
        return False
    WORKER_STATE['running'] = False
    if WORKER_STATE['thread']:
        WORKER_STATE['thread'].join(timeout=10)
    WORKER_STATE['thread'] = None
    WORKER_STATE['started_at'] = None
    _save_state()
    logger.info('Worker stopped')
    return True


def worker_status() -> dict:
    _load_state()
    return {
        'running': WORKER_STATE['running'],
        'started_at': WORKER_STATE['started_at'],
        'processed': WORKER_STATE['processed'],
        'failed': WORKER_STATE['failed'],
        'last_run': WORKER_STATE['last_run'],
        'poll_interval': WORKER_STATE['poll_interval'],
    }


def run_worker_forever(poll_interval: int = 30):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    )

    def _signal_handler(sig, frame):
        logger.info('Shutdown signal received, stopping worker...')
        stop_worker()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    start_worker(poll_interval=poll_interval)

    try:
        while WORKER_STATE['running']:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_worker()
