from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from database.models import Vacancy
from database.session import get_session


class IngestResult:
    """Result of ingesting a single message."""

    def __init__(self, raw_message: str, source: str, vacancy_id: Optional[int] = None,
                 success: bool = True, error: Optional[str] = None):
        self.raw_message = raw_message
        self.source = source
        self.vacancy_id = vacancy_id
        self.success = success
        self.error = error

    def __repr__(self) -> str:
        return (
            f"<IngestResult(source={self.source}, success={self.success}, "
            f"vacancy_id={self.vacancy_id})>"
        )


class FileReader:
    """Reads vacancy messages from plain text files."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def list_files(self) -> List[Path]:
        if not self.directory.exists():
            return []
        return sorted(
            f for f in self.directory.iterdir()
            if f.is_file() and f.suffix.lower() in ('.txt', '.text')
        )

    def read_file(self, filepath: str | Path) -> str:
        path = Path(filepath)
        return path.read_text(encoding='utf-8')

    def read_all(self) -> List[str]:
        messages = []
        for f in self.list_files():
            msg = self.read_file(f)
            if msg.strip():
                messages.append(msg)
        return messages


class WebhookReader:
    """HTTP webhook endpoint for receiving vacancy messages via Flask."""

    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.host = host
        self.port = port
        self._app = None
        self._received_messages: List[str] = []

    @property
    def app(self):
        if self._app is None:
            from flask import Flask, request, jsonify
            app = Flask('webhook_reader')

            @app.route('/webhook/vacancy', methods=['POST'])
            def handle_vacancy():
                data = request.get_json(silent=True)
                if data and 'message' in data:
                    raw = data['message']
                else:
                    raw = request.get_data(as_text=True)

                if not raw or not raw.strip():
                    return jsonify({'status': 'error', 'message': 'Empty message'}), 400

                self._received_messages.append(raw)
                return jsonify({'status': 'ok', 'message': 'Message received'}), 200

            @app.route('/health', methods=['GET'])
            def health():
                return jsonify({'status': 'ok', 'service': 'webhook_reader'}), 200

            self._app = app
        return self._app

    def start(self, debug: bool = False) -> None:
        self.app.run(host=self.host, port=self.port, debug=debug)

    def collect_messages(self) -> List[str]:
        msgs = list(self._received_messages)
        self._received_messages.clear()
        return msgs


class ReaderPipeline:
    """Orchestrates reader sources and persists messages to the database."""

    def __init__(self):
        pass

    def ingest_message(self, raw_message: str, source: str = 'unknown') -> IngestResult:
        session = get_session()
        try:
            vacancy = Vacancy(
                title='Untitled',
                company='Unknown',
                description=raw_message[:500],
                raw_message=raw_message,
                processed=False,
            )
            session.add(vacancy)
            session.commit()
            return IngestResult(
                raw_message=raw_message,
                source=source,
                vacancy_id=vacancy.id,
                success=True,
            )
        except Exception as e:
            session.rollback()
            return IngestResult(
                raw_message=raw_message,
                source=source,
                success=False,
                error=str(e),
            )
        finally:
            session.close()

    def ingest_file(self, filepath: str | Path, source: str = 'file') -> IngestResult:
        try:
            with open(filepath, encoding='utf-8') as f:
                raw_message = f.read()
            if not raw_message.strip():
                return IngestResult(raw_message='', source=source, success=False,
                                    error='Empty file')
            return self.ingest_message(raw_message, source=f'{source}:{Path(filepath).name}')
        except Exception as e:
            return IngestResult(raw_message='', source=source, success=False, error=str(e))

    def ingest_directory(self, directory: str | Path, source: str = 'file') -> List[IngestResult]:
        reader = FileReader(directory)
        results = []
        for f in reader.list_files():
            result = self.ingest_file(f, source)
            results.append(result)
        return results

    def ingest_webhook_messages(self, reader: WebhookReader, source: str = 'webhook') -> List[IngestResult]:
        messages = reader.collect_messages()
        results = []
        for msg in messages:
            result = self.ingest_message(msg, source)
            results.append(result)
        return results
