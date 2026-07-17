import pytest
import os
import json
import tempfile
from pathlib import Path

from reader import FileReader, WebhookReader, ReaderPipeline, IngestResult
from database.init import init_db, drop_db, reset_db
from database.session import get_session
from database.models import Vacancy


SAMPLE_MESSAGE_1 = """We are hiring a Senior Python Developer!

Company: Tech Company Inc.
Location: San Francisco, CA
Salary: $120k - $180k
Job Type: Full-time

Contact: careers@techcompany.com"""

SAMPLE_MESSAGE_2 = """Hiring a Junior Frontend Engineer

Company: Web Startup
Location: New York, NY
Salary: $70k - $90k
Job Type: Full-time"""


@pytest.fixture(autouse=True)
def db_setup():
    init_db()
    yield
    drop_db()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def pipeline():
    return ReaderPipeline()


def create_message_file(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(content, encoding='utf-8')
    return path


class TestFileReader:
    def test_read_single_file(self, temp_dir):
        path = create_message_file(temp_dir, 'msg1.txt', SAMPLE_MESSAGE_1)
        reader = FileReader(temp_dir)
        assert reader.read_file(path) == SAMPLE_MESSAGE_1

    def test_read_all_files(self, temp_dir):
        create_message_file(temp_dir, 'msg1.txt', SAMPLE_MESSAGE_1)
        create_message_file(temp_dir, 'msg2.txt', SAMPLE_MESSAGE_2)
        reader = FileReader(temp_dir)
        messages = reader.read_all()
        assert len(messages) == 2
        assert SAMPLE_MESSAGE_1 in messages
        assert SAMPLE_MESSAGE_2 in messages

    def test_list_files_only_txt(self, temp_dir):
        create_message_file(temp_dir, 'msg1.txt', SAMPLE_MESSAGE_1)
        create_message_file(temp_dir, 'note.md', '# not a message')
        create_message_file(temp_dir, 'data.json', '{}')
        reader = FileReader(temp_dir)
        files = reader.list_files()
        assert len(files) == 1
        assert files[0].suffix == '.txt'

    def test_empty_directory(self, temp_dir):
        reader = FileReader(temp_dir)
        assert reader.list_files() == []
        assert reader.read_all() == []

    def test_nonexistent_directory(self):
        reader = FileReader('/nonexistent/path')
        assert reader.list_files() == []

    def test_skip_empty_files(self, temp_dir):
        create_message_file(temp_dir, 'empty.txt', '   ')
        create_message_file(temp_dir, 'msg.txt', SAMPLE_MESSAGE_1)
        reader = FileReader(temp_dir)
        messages = reader.read_all()
        assert len(messages) == 1


class TestWebhookReader:
    def test_webhook_app_exists(self):
        reader = WebhookReader()
        assert reader.app is not None

    def test_webhook_health_endpoint(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            resp = client.get('/health')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['status'] == 'ok'

    def test_webhook_receive_json_message(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            resp = client.post(
                '/webhook/vacancy',
                data=json.dumps({'message': SAMPLE_MESSAGE_1}),
                content_type='application/json',
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['status'] == 'ok'

    def test_webhook_receive_raw_text(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            resp = client.post(
                '/webhook/vacancy',
                data=SAMPLE_MESSAGE_1,
                content_type='text/plain',
            )
            assert resp.status_code == 200

    def test_webhook_empty_message_rejected(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            resp = client.post(
                '/webhook/vacancy',
                data=json.dumps({'message': ''}),
                content_type='application/json',
            )
            assert resp.status_code == 400

    def test_webhook_collect_messages(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            client.post(
                '/webhook/vacancy',
                data=json.dumps({'message': SAMPLE_MESSAGE_1}),
                content_type='application/json',
            )
            client.post(
                '/webhook/vacancy',
                data=json.dumps({'message': SAMPLE_MESSAGE_2}),
                content_type='application/json',
            )
        messages = reader.collect_messages()
        assert len(messages) == 2
        assert SAMPLE_MESSAGE_1 in messages
        assert SAMPLE_MESSAGE_2 in messages

    def test_webhook_collect_clears_buffer(self):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            client.post('/webhook/vacancy',
                        data=json.dumps({'message': SAMPLE_MESSAGE_1}),
                        content_type='application/json')
        assert len(reader.collect_messages()) == 1
        assert len(reader.collect_messages()) == 0


class TestReaderPipeline:
    def test_ingest_message_saves_to_db(self, pipeline):
        result = pipeline.ingest_message(SAMPLE_MESSAGE_1, source='test')
        assert result.success is True
        assert result.vacancy_id is not None
        assert result.source == 'test'

        session = get_session()
        vacancy = session.query(Vacancy).filter(Vacancy.id == result.vacancy_id).first()
        assert vacancy is not None
        assert vacancy.raw_message == SAMPLE_MESSAGE_1
        assert vacancy.processed is False
        session.close()

    def test_ingest_file(self, pipeline, temp_dir):
        path = create_message_file(temp_dir, 'vacancy.txt', SAMPLE_MESSAGE_1)
        result = pipeline.ingest_file(path)
        assert result.success is True
        assert result.vacancy_id is not None

        session = get_session()
        vacancy = session.query(Vacancy).filter(Vacancy.id == result.vacancy_id).first()
        assert vacancy.raw_message == SAMPLE_MESSAGE_1
        session.close()

    def test_ingest_directory(self, pipeline, temp_dir):
        create_message_file(temp_dir, 'msg1.txt', SAMPLE_MESSAGE_1)
        create_message_file(temp_dir, 'msg2.txt', SAMPLE_MESSAGE_2)

        results = pipeline.ingest_directory(temp_dir)
        assert len(results) == 2
        assert all(r.success for r in results)

        session = get_session()
        count = session.query(Vacancy).count()
        assert count == 2
        session.close()

    def test_ingest_webhook_messages(self, pipeline):
        reader = WebhookReader()
        with reader.app.test_client() as client:
            client.post('/webhook/vacancy',
                        data=json.dumps({'message': SAMPLE_MESSAGE_1}),
                        content_type='application/json')
            client.post('/webhook/vacancy',
                        data=json.dumps({'message': SAMPLE_MESSAGE_2}),
                        content_type='application/json')

        results = pipeline.ingest_webhook_messages(reader)
        assert len(results) == 2
        assert all(r.success for r in results)

        session = get_session()
        count = session.query(Vacancy).count()
        assert count == 2
        session.close()

    def test_ingest_empty_file(self, pipeline, temp_dir):
        path = create_message_file(temp_dir, 'empty.txt', '')
        result = pipeline.ingest_file(path)
        assert result.success is False

    def test_ingest_nonexistent_file(self, pipeline):
        result = pipeline.ingest_file('/nonexistent/file.txt')
        assert result.success is False

    def test_ingest_empty_message(self, pipeline):
        result = pipeline.ingest_message('', source='test')
        session = get_session()
        vacancy = session.query(Vacancy).filter(Vacancy.id == result.vacancy_id).first()
        assert vacancy.raw_message == ''
        session.close()
