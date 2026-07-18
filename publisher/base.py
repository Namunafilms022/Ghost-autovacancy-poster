from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class PublishResult:
    def __init__(self, platform: str, vacancy_id: int,
                 success: bool, post_id: Optional[str] = None,
                 url: Optional[str] = None, error: Optional[str] = None,
                 attempts: int = 1):
        self.platform = platform
        self.vacancy_id = vacancy_id
        self.success = success
        self.post_id = post_id
        self.url = url
        self.error = error
        self.attempts = attempts

    def __repr__(self) -> str:
        status = 'OK' if self.success else f'FAIL({self.error})'
        return f"<PublishResult(platform={self.platform}, vacancy={self.vacancy_id}, {status})>"


class BasePublisher(ABC):
    platform: str = 'unknown'

    @abstractmethod
    def publish(self, vacancy_id: int) -> PublishResult:
        ...

    def get_status(self, post_id: str) -> str:
        raise NotImplementedError
