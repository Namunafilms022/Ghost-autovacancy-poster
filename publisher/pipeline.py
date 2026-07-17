from __future__ import annotations

import json
import os
import time
from typing import List, Optional

from .base import BasePublisher, PublishResult


def _load_publisher_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return cfg.get('publisher', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class PublisherPipeline:
    def __init__(self, publishers: Optional[List[BasePublisher]] = None):
        self.publishers = publishers or []
        config = _load_publisher_config()
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay_seconds', 2)

    def publish(self, vacancy_id: int) -> List[PublishResult]:
        results = []
        for publisher in self.publishers:
            result = self._publish_with_retry(publisher, vacancy_id)
            results.append(result)
        return results

    def _publish_with_retry(self, publisher: BasePublisher,
                            vacancy_id: int) -> PublishResult:
        last_error: Optional[str] = None
        attempts = 0

        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                result = publisher.publish(vacancy_id)
                if result.success:
                    result.attempts = attempt
                    return result
                last_error = result.error or 'Unknown error'
            except Exception as e:
                last_error = str(e)

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)

        return PublishResult(
            platform=getattr(publisher, 'platform', 'unknown'),
            vacancy_id=vacancy_id,
            success=False,
            error=f'Failed after {attempts} attempts: {last_error}',
            attempts=attempts,
        )

    def add_publisher(self, publisher: BasePublisher) -> None:
        self.publishers.append(publisher)
