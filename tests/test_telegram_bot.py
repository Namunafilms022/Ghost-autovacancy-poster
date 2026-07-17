import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from telegram_bot.bot import _build_summary, _format_salary, _load_config, main


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

    def test_zero_values(self):
        result = _format_salary(0.0, 0.0)
        assert '0' in result


class TestBuildSummary:
    def test_full_vacancy(self):
        from database.models import Vacancy
        v = Vacancy(
            id=5, title='Software Engineer', company='Tech Co',
            location='Kathmandu', salary_min=50000.0, salary_max=80000.0,
            job_type='full_time', experience_level='mid',
            is_duplicate=False, processed=True,
        )
        summary = _build_summary(v)
        assert 'Vacancy #5' in summary
        assert 'Software Engineer' in summary
        assert 'Tech Co' in summary
        assert 'Kathmandu' in summary
        assert 'No duplicate' in summary

    def test_duplicate_vacancy(self):
        from database.models import Vacancy
        v = Vacancy(
            id=10, title='Duplicate Job', company='Copy Co',
            is_duplicate=True, duplicate_of=3, processed=True,
            salary_min=None, salary_max=None,
        )
        summary = _build_summary(v)
        assert 'duplicate' in summary.lower()
        assert '#3' in summary

    def test_minimal_vacancy(self):
        from database.models import Vacancy
        v = Vacancy(id=1, title='Dev', company='Co', processed=True)
        summary = _build_summary(v)
        assert 'Dev' in summary
        assert 'Co' in summary


class TestLoadConfig:
    def test_returns_dict(self):
        cfg = _load_config()
        assert isinstance(cfg, dict)
        assert 'telegram_bot' in cfg
        assert 'token' in cfg['telegram_bot']

    @patch('telegram_bot.bot.open')
    def test_file_not_found(self, mock_open):
        mock_open.side_effect = FileNotFoundError
        cfg = _load_config()
        assert cfg == {}


class TestMain:
    def test_no_token(self):
        with patch('telegram_bot.bot._load_token', return_value=''):
            result = main()
            assert result is None

    @patch('telegram_bot.bot._load_token', return_value='test_token')
    @patch('telegram_bot.bot.Application')
    def test_with_token(self, mock_app_class, mock_token):
        mock_app = MagicMock()
        mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app

        main()

        mock_app.add_handler.assert_called()
        mock_app.run_polling.assert_called_once()


@pytest.mark.asyncio
class TestHandlers:
    @patch('telegram_bot.bot._process_vacancy', new_callable=AsyncMock)
    async def test_handle_message(self, mock_process):
        from telegram_bot.bot import handle_message

        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.full_name = 'Test User'

        message = MagicMock()
        message.text = '  We are hiring a Developer!  '
        message.reply_text = AsyncMock()
        update.message = message

        context = MagicMock()

        mock_process.return_value = 42

        await handle_message(update, context)
        mock_process.assert_called_once()
        args = mock_process.call_args[0]
        assert args[1] == update
        assert args[0] == 'We are hiring a Developer!'

    @patch('telegram_bot.bot._process_vacancy', new_callable=AsyncMock)
    async def test_handle_empty_message(self, mock_process):
        from telegram_bot.bot import handle_message

        update = MagicMock()
        update.effective_user.id = 1
        update.effective_user.full_name = 'T'

        message = MagicMock()
        message.text = '   '
        message.reply_text = AsyncMock()
        update.message = message

        await handle_message(update, MagicMock())
        mock_process.assert_not_called()
        message.reply_text.assert_awaited_once()

    async def test_callback_publish_no_config(self):
        from telegram_bot.bot import handle_callback

        query = MagicMock()
        query.data = 'publish:1'
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        with patch('telegram_bot.bot._load_config', return_value={'facebook': {'access_token': '', 'group_ids': []}}):
            await handle_callback(update, MagicMock())

        query.answer.assert_awaited_once()

    @patch('publisher.facebook.requests.post')
    async def test_callback_publish_success(self, mock_fb_post):
        from telegram_bot.bot import handle_callback

        mock_fb_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {'id': '123_456'},
        )

        query = MagicMock()
        query.data = 'publish:42'
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        with patch('telegram_bot.bot._load_config', return_value={
            'facebook': {'access_token': 'tok', 'group_ids': ['g1']},
        }):
            await handle_callback(update, MagicMock())

        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()

    async def test_callback_invalid_data(self):
        from telegram_bot.bot import handle_callback

        query = MagicMock()
        query.data = 'invalid'
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        await handle_callback(update, MagicMock())
        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
class TestProcessVacancy:
    @patch('telegram_bot.bot.VacancyParser')
    @patch('telegram_bot.bot.Normalizer')
    @patch('telegram_bot.bot.DuplicateDetector')
    @patch('telegram_bot.bot.PosterGenerator')
    @patch('telegram_bot.bot.get_session')
    @patch('telegram_bot.bot.init_db')
    async def test_process_success(
        self, mock_init_db, mock_get_session,
        mock_poster_cls, mock_detector_cls, mock_normalizer_cls, mock_parser_cls
    ):
        from telegram_bot.bot import _process_vacancy
        from database.models import Vacancy
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
        mock_detector.detect.return_value = mock_dup_result
        mock_detector_cls.return_value = mock_detector

        mock_poster = MagicMock()
        mock_poster_cls.return_value = mock_poster

        real_vacancy = Vacancy(
            title='Dev', company='Test Co',
            salary_min=50000.0, salary_max=80000.0,
        )

        def _add_side_effect(obj):
            obj.id = 99

        mock_session = MagicMock()
        mock_session.add.side_effect = _add_side_effect
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock()

        read_back = Vacancy(
            id=99, title='Dev', company='Test Co',
            salary_min=50000.0, salary_max=80000.0,
            processed=True,
        )
        mock_vacancy_query = MagicMock()
        mock_vacancy_query.first.return_value = read_back
        mock_session.query.return_value.filter.return_value = mock_vacancy_query

        mock_get_session.side_effect = [mock_session, mock_session]

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        result = await _process_vacancy('Test vacancy message', update, context)

        assert result == 99
        mock_parser.parse.assert_called_once_with('Test vacancy message')
        mock_normalizer.normalize.assert_called_once()
        mock_detector.detect.assert_called_once()
        mock_poster.generate.assert_called_once_with(99)
