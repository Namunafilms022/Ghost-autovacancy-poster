from unittest.mock import MagicMock, patch

import pytest

from scheduler.scheduler import Scheduler, scheduled_job, _load_config


class TestLoadConfig:
    def test_returns_scheduler_section(self):
        cfg = _load_config()
        assert isinstance(cfg, dict)

    @patch('scheduler.scheduler._CONFIG_PATH', 'nonexistent.json')
    def test_file_not_found(self):
        assert _load_config() == {}

    @patch('scheduler.scheduler._CONFIG_PATH', '/dev/null')
    def test_bad_json(self):
        assert _load_config() == {}


class TestScheduler:
    def test_start_disabled(self):
        sched = Scheduler()
        sched._config = {'enabled': False}
        sched.start()
        assert sched.running is False

    def test_start_twice(self):
        sched = Scheduler()
        sched._config = {'enabled': True, 'time': '09:00', 'timezone': 'UTC'}
        sched._running = True
        sched.start()
        assert sched.running is True

    def test_stop_when_not_running(self):
        sched = Scheduler()
        sched.stop()
        assert sched.running is False

    def test_invalid_time_falls_back(self):
        sched = Scheduler()
        sched._config = {'enabled': True, 'time': 'not a time', 'timezone': 'UTC'}
        sched.start()
        assert sched.running is True

    def test_get_jobs_empty(self):
        sched = Scheduler()
        assert sched.get_jobs() == []


class TestScheduledJob:
    @patch('scheduler.scheduler.init_db')
    @patch('scheduler.scheduler.FileReader')
    @patch('scheduler.scheduler.VacancyParser')
    @patch('scheduler.scheduler.ReaderPipeline')
    @patch('scheduler.scheduler.Normalizer')
    @patch('scheduler.scheduler.DuplicateDetector')
    @patch('scheduler.scheduler.PosterGenerator')
    @patch('scheduler.scheduler._get_facebook_config')
    def test_no_vacancies_dir(
        self, mock_fb, mock_poster_cls, mock_dup_cls, mock_norm_cls,
        mock_reader_cls, mock_parser_cls, mock_filer, mock_db
    ):
        mock_fb.return_value = ('', [])
        mock_filer.return_value.exists.return_value = True
        mock_filer.return_value.read_all.return_value = []
        scheduled_job()
        mock_parser_cls.assert_not_called()

    @patch('scheduler.scheduler.init_db')
    @patch('scheduler.scheduler.FileReader')
    @patch('scheduler.scheduler.VacancyParser')
    @patch('scheduler.scheduler.ReaderPipeline')
    @patch('scheduler.scheduler.Normalizer')
    @patch('scheduler.scheduler.DuplicateDetector')
    @patch('scheduler.scheduler.PosterGenerator')
    @patch('scheduler.scheduler._get_facebook_config')
    def test_no_vacancy_files(
        self, mock_fb, mock_poster_cls, mock_dup_cls, mock_norm_cls,
        mock_reader_cls, mock_parser_cls, mock_filer, mock_db
    ):
        mock_fb.return_value = ('', [])
        mock_filer.return_value.exists.return_value = True
        mock_filer.return_value.read_all.return_value = []
        scheduled_job()
        mock_parser_cls.assert_not_called()

    @patch('scheduler.scheduler.init_db')
    @patch('scheduler.scheduler.FileReader')
    @patch('scheduler.scheduler.VacancyParser')
    @patch('scheduler.scheduler.ReaderPipeline')
    @patch('scheduler.scheduler.Normalizer')
    @patch('scheduler.scheduler.DuplicateDetector')
    @patch('scheduler.scheduler.PosterGenerator')
    @patch('scheduler.scheduler._get_facebook_config')
    def test_processes_messages(
        self, mock_fb, mock_poster_cls, mock_dup_cls, mock_norm_cls,
        mock_reader_cls, mock_parser_cls, mock_filer, mock_db
    ):
        from parser.models import JobDetails

        mock_fb.return_value = ('token', ['group1'])

        mock_filer.return_value.exists.return_value = True
        mock_filer.return_value.read_all.return_value = [
            'Job: Dev at Company X',
            'Job: Engineer at Company Y',
        ]

        mock_details = JobDetails(title='Dev', company='Company X')
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_details
        mock_parser_cls.return_value = mock_parser

        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.vacancy_id = 10
        mock_pipeline.ingest_message.return_value = mock_result
        mock_reader_cls.return_value = mock_pipeline

        mock_normalizer = MagicMock()
        mock_norm_result = MagicMock()
        mock_norm_result.success = True
        mock_norm_result.errors = []
        mock_normalizer.normalize.return_value = mock_norm_result
        mock_norm_cls.return_value = mock_normalizer

        mock_detector = MagicMock()
        mock_dup_result = MagicMock()
        mock_dup_result.is_duplicate = False
        mock_detector.detect.return_value = mock_dup_result
        mock_dup_cls.return_value = mock_detector

        mock_poster = MagicMock()
        mock_poster_cls.return_value = mock_poster

        scheduled_job()

        assert mock_parser.parse.call_count == 2
        assert mock_pipeline.ingest_message.call_count == 2
        assert mock_normalizer.normalize.call_count == 2
        assert mock_detector.detect.call_count == 2
        assert mock_poster.generate.call_count == 2

    @patch('scheduler.scheduler.init_db')
    @patch('scheduler.scheduler.FileReader')
    @patch('scheduler.scheduler.VacancyParser')
    @patch('scheduler.scheduler.ReaderPipeline')
    @patch('scheduler.scheduler.Normalizer')
    @patch('scheduler.scheduler.DuplicateDetector')
    @patch('scheduler.scheduler.PosterGenerator')
    @patch('scheduler.scheduler._get_facebook_config')
    def test_handles_parse_failure(
        self, mock_fb, mock_poster_cls, mock_dup_cls, mock_norm_cls,
        mock_reader_cls, mock_parser_cls, mock_filer, mock_db
    ):
        mock_fb.return_value = ('', [])
        mock_filer.return_value.exists.return_value = True
        mock_filer.return_value.read_all.return_value = ['bad message']

        mock_parser = MagicMock()
        mock_parser.parse.return_value = None
        mock_parser_cls.return_value = mock_parser

        mock_pipeline = MagicMock()
        mock_reader_cls.return_value = mock_pipeline

        scheduled_job()

        mock_pipeline.ingest_message.assert_not_called()
