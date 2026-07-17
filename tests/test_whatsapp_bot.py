import json
from unittest.mock import MagicMock, patch

import pytest

from whatsapp_bot.webhook import app, _format_salary, _build_result, _load_config
from database.models import Vacancy


class TestFormatSalary:
    def test_both_values(self):
        assert '50,000' in _format_salary(50000.0, 80000.0)
        assert '80,000' in _format_salary(50000.0, 80000.0)

    def test_min_only(self):
        result = _format_salary(75000.0, None)
        assert '75,000' in result
        assert '+' in result

    def test_max_only(self):
        result = _format_salary(None, 100000.0)
        assert '100,000' in result
        assert 'Up to' in result

    def test_none(self):
        assert _format_salary(None, None) == 'Not specified'


class TestBuildResult:
    def test_full_vacancy(self):
        v = Vacancy(
            id=7, title='Backend Dev', company='Server Co',
            location='Lalitpur', salary_min=60000.0, salary_max=90000.0,
            job_type='full_time', experience_level='mid',
            is_duplicate=False, processed=True,
        )
        r = _build_result(v)
        assert r['success'] is True
        assert r['vacancy_id'] == 7
        assert 'Backend Dev' in r['summary']
        assert 'Server Co' in r['summary']
        assert 'No duplicate' in r['summary']
        assert r['is_duplicate'] is False

    def test_duplicate_vacancy(self):
        v = Vacancy(
            id=8, title='Dup', company='Dup Co',
            is_duplicate=True, duplicate_of=3, processed=True,
        )
        r = _build_result(v)
        assert 'Duplicate' in r['summary']
        assert '#3' in r['summary']

    def test_minimal_vacancy(self):
        v = Vacancy(id=9, title='Dev', company='Co', processed=True)
        r = _build_result(v)
        assert r['vacancy_id'] == 9
        assert 'Dev' in r['summary']
        assert 'Co' in r['summary']


class TestLoadConfig:
    def test_returns_dict(self):
        cfg = _load_config()
        assert isinstance(cfg, dict)
        assert 'whatsapp_bot' in cfg

    @patch('whatsapp_bot.webhook.open')
    def test_file_not_found(self, mock_open):
        mock_open.side_effect = FileNotFoundError
        assert _load_config() == {}


class TestWebhookRoutes:
    client = app.test_client()

    def test_health(self):
        resp = self.client.get('/webhook/health')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'ok'

    def test_missing_message(self):
        resp = self.client.post('/webhook/process-vacancy',
                                json={})
        assert resp.status_code == 400
        assert 'message' in resp.get_json()['error']

    def test_empty_message(self):
        resp = self.client.post('/webhook/process-vacancy',
                                json={'message': '   '})
        assert resp.status_code == 400
        assert 'Empty' in resp.get_json()['error']

    @patch('whatsapp_bot.webhook.VacancyParser')
    @patch('whatsapp_bot.webhook.Normalizer')
    @patch('whatsapp_bot.webhook.DuplicateDetector')
    @patch('whatsapp_bot.webhook.PosterGenerator')
    @patch('whatsapp_bot.webhook.get_session')
    @patch('whatsapp_bot.webhook.init_db')
    def test_process_vacancy_success(
        self, mock_db, mock_session, mock_poster_cls,
        mock_detector_cls, mock_normalizer_cls, mock_parser_cls
    ):
        from parser.models import JobDetails

        mock_details = JobDetails(title='Dev', company='Test Co')
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_details
        mock_parser_cls.return_value = mock_parser

        mock_normalizer = MagicMock()
        mock_norm_result = MagicMock()
        mock_norm_result.success = True
        mock_normalizer.normalize.return_value = mock_norm_result
        mock_normalizer_cls.return_value = mock_normalizer

        mock_detector = MagicMock()
        mock_dup_result = MagicMock()
        mock_dup_result.is_duplicate = False
        mock_dup_result.matched_vacancy_id = None
        mock_dup_result.similarity_score = 0.0
        mock_detector.detect.return_value = mock_dup_result
        mock_detector_cls.return_value = mock_detector

        mock_poster = MagicMock()
        mock_poster_cls.return_value = mock_poster

        def _add_side(obj):
            obj.id = 55

        session_instance = MagicMock()
        session_instance.add.side_effect = _add_side

        read_back = Vacancy(
            id=55, title='Dev', company='Test Co',
            salary_min=50000.0, salary_max=80000.0,
            processed=True,
        )
        session_instance.query.return_value.filter.return_value.first.return_value = read_back

        mock_session.side_effect = [session_instance, session_instance]

        resp = self.client.post('/webhook/process-vacancy', json={
            'message': 'We are hiring!',
            'group_name': 'Test Group',
            'sender': '977-9800000000',
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['vacancy_id'] == 55

    @patch('whatsapp_bot.webhook.VacancyParser')
    @patch('whatsapp_bot.webhook.Normalizer')
    @patch('whatsapp_bot.webhook.DuplicateDetector')
    @patch('whatsapp_bot.webhook.PosterGenerator')
    @patch('whatsapp_bot.webhook.get_session')
    @patch('whatsapp_bot.webhook.init_db')
    def test_process_vacancy_duplicate(
        self, mock_db, mock_session, mock_poster_cls,
        mock_detector_cls, mock_normalizer_cls, mock_parser_cls
    ):
        from parser.models import JobDetails

        mock_details = JobDetails(title='Dup Job', company='Dup Co')
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_details
        mock_parser_cls.return_value = mock_parser

        mock_normalizer = MagicMock()
        mock_norm_result = MagicMock()
        mock_norm_result.success = True
        mock_normalizer.normalize.return_value = mock_norm_result
        mock_normalizer_cls.return_value = mock_normalizer

        mock_detector = MagicMock()
        mock_dup_result = MagicMock()
        mock_dup_result.is_duplicate = True
        mock_dup_result.matched_vacancy_id = 3
        mock_dup_result.similarity_score = 0.92
        mock_detector.detect.return_value = mock_dup_result
        mock_detector_cls.return_value = mock_detector

        mock_poster = MagicMock()
        mock_poster_cls.return_value = mock_poster

        def _add_side(obj):
            obj.id = 56

        session_instance = MagicMock()
        session_instance.add.side_effect = _add_side

        read_back = Vacancy(
            id=56, title='Dup Job', company='Dup Co',
            is_duplicate=True, duplicate_of=3,
        )
        session_instance.query.return_value.filter.return_value.first.return_value = read_back

        mock_session.side_effect = [session_instance, session_instance]

        resp = self.client.post('/webhook/process-vacancy', json={
            'message': 'Duplicate job posting',
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'Duplicate' in data['summary']
        assert '#3' in data['summary']

    @patch('whatsapp_bot.webhook._load_config')
    def test_publish_facebook_not_configured(self, mock_cfg):
        mock_cfg.return_value = {'facebook': {'access_token': '', 'group_ids': []}}
        resp = self.client.post('/webhook/publish-faceboard',
                                json={'vacancy_id': 1})
        assert resp.status_code == 404  # wrong endpoint

        resp = self.client.post('/webhook/publish-facebook',
                                json={'vacancy_id': 1})
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'not configured' in data['error'].lower()

    def test_publish_missing_id(self):
        resp = self.client.post('/webhook/publish-facebook', json={})
        assert resp.status_code == 400
        assert 'vacancy_id' in resp.get_json()['error']
