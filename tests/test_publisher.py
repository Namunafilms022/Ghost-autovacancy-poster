import pytest
import json
import os
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime

from publisher import BasePublisher, PublishResult, FacebookPublisher, PublisherPipeline
from database.init import init_db, drop_db
from database.session import get_session
from database.models import Vacancy, PublishedPost


def create_vacancy(title='Software Engineer', company='Tech Corp',
                    processed=True) -> int:
    session = get_session()
    v = Vacancy(
        title=title, company=company, processed=processed,
        location='Kathmandu', salary_min=50000.0, salary_max=80000.0,
        job_type='full_time', experience_level='mid',
    )
    session.add(v)
    session.commit()
    vid = v.id
    session.close()
    return vid


@pytest.fixture(autouse=True)
def db():
    init_db()
    yield
    drop_db()


def mock_facebook_response(status_code=200, post_id='123_456', error=None):
    data = {}
    if error:
        data['error'] = {'message': error}
    else:
        data['id'] = post_id
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    return resp


class TestBasePublisher:
    def test_publish_result_creation(self):
        r = PublishResult(platform='test', vacancy_id=1, success=True,
                          post_id='abc123', url='https://example.com/post/1')
        assert r.platform == 'test'
        assert r.vacancy_id == 1
        assert r.success is True
        assert r.post_id == 'abc123'
        assert r.url == 'https://example.com/post/1'
        assert r.error is None
        assert r.attempts == 1

    def test_publish_result_failure(self):
        r = PublishResult(platform='test', vacancy_id=1, success=False,
                          error='API error')
        assert r.success is False
        assert r.error == 'API error'

    def test_base_publisher_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BasePublisher()  # abstract


class TestFacebookPublisher:
    def test_no_token_returns_error(self):
        pub = FacebookPublisher(access_token='', group_ids=['123'])
        vid = create_vacancy()
        result = pub.publish(vid)
        assert result.success is False
        assert 'access token' in result.error.lower()

    def test_no_groups_returns_error(self):
        pub = FacebookPublisher(access_token='tok', group_ids=[])
        vid = create_vacancy()
        result = pub.publish(vid)
        assert result.success is False
        assert 'group' in result.error.lower()

    def test_vacancy_not_found(self):
        pub = FacebookPublisher(access_token='tok', group_ids=['123'])
        result = pub.publish(99999)
        assert result.success is False

    @patch('publisher.facebook.requests.post')
    def test_successful_publish(self, mock_post):
        mock_post.return_value = mock_facebook_response(post_id='987_654')

        pub = FacebookPublisher(access_token='valid_token', group_ids=['123456'])
        vid = create_vacancy()
        result = pub.publish(vid)

        assert result.success is True
        assert result.post_id == '987_654'
        assert result.platform == 'facebook'

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'graph.facebook.com' in args[0]
        assert kwargs['params']['access_token'] == 'valid_token'
        assert 'Software Engineer' in kwargs['params']['message']

    @patch('publisher.facebook.requests.post')
    def test_publishes_to_multiple_groups(self, mock_post):
        mock_post.return_value = mock_facebook_response(post_id='group_post')

        pub = FacebookPublisher(access_token='tok', group_ids=['g1', 'g2'])
        vid = create_vacancy()
        result = pub.publish(vid)

        assert result.success is True
        assert mock_post.call_count == 2

    @patch('publisher.facebook.requests.post')
    def test_api_error_returns_failure(self, mock_post):
        mock_post.return_value = mock_facebook_response(
            status_code=400, error='Invalid token'
        )

        pub = FacebookPublisher(access_token='bad_token', group_ids=['g1'])
        vid = create_vacancy()
        result = pub.publish(vid)

        assert result.success is False
        assert 'Invalid token' in result.error

    @patch('publisher.facebook.requests.post')
    def test_saves_published_post_record(self, mock_post):
        mock_post.return_value = mock_facebook_response(post_id='777_888')

        pub = FacebookPublisher(access_token='tok', group_ids=['g1'])
        vid = create_vacancy()
        pub.publish(vid)

        session = get_session()
        records = session.query(PublishedPost).all()
        assert len(records) == 1
        assert records[0].vacancy_id == vid
        assert records[0].platform == 'facebook:group:g1'
        assert records[0].external_id == '777_888'
        assert records[0].status == 'published'
        session.close()

    @patch('publisher.facebook.requests.post')
    def test_saves_failed_post_record(self, mock_post):
        mock_post.return_value = mock_facebook_response(
            status_code=400, error='Group not found'
        )

        pub = FacebookPublisher(access_token='tok', group_ids=['g1'])
        vid = create_vacancy()
        pub.publish(vid)

        session = get_session()
        records = session.query(PublishedPost).all()
        assert len(records) == 1
        assert records[0].status == 'failed'
        session.close()

    @patch('publisher.facebook.requests.post')
    def test_request_exception_handled(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError('Connection timeout')

        pub = FacebookPublisher(access_token='tok', group_ids=['g1'])
        vid = create_vacancy()
        result = pub.publish(vid)

        assert result.success is False
        assert 'Connection timeout' in result.error

    @patch('publisher.facebook.requests.get')
    def test_get_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'id': '123', 'status': 'published'}
        mock_get.return_value = mock_resp

        pub = FacebookPublisher(access_token='tok', group_ids=['g1'])
        status = pub.get_status('123')
        assert status == 'published'

    @patch('publisher.facebook.requests.get')
    def test_get_status_no_token(self, mock_get):
        pub = FacebookPublisher(access_token='', group_ids=['g1'])
        status = pub.get_status('123')
        assert status == 'unknown'
        mock_get.assert_not_called()


class FakePublisher(BasePublisher):
    platform = 'fake'

    def __init__(self, should_succeed=True, fail_count=0):
        self.should_succeed = should_succeed
        self.fail_count = fail_count
        self.call_count = 0

    def publish(self, vacancy_id: int) -> PublishResult:
        self.call_count += 1
        if not self.should_succeed and self.call_count <= self.fail_count:
            raise Exception('Simulated failure')
        if not self.should_succeed:
            return PublishResult(
                platform=self.platform, vacancy_id=vacancy_id,
                success=False, error='Simulated persistent failure'
            )
        return PublishResult(
            platform=self.platform, vacancy_id=vacancy_id,
            success=True, post_id='fake_post'
        )


class TestPublisherPipeline:
    def test_publish_with_single_publisher(self):
        fake = FakePublisher(should_succeed=True)
        pipeline = PublisherPipeline(publishers=[fake])
        vid = create_vacancy()
        results = pipeline.publish(vid)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].platform == 'fake'
        assert fake.call_count == 1

    def test_publish_with_multiple_publishers(self):
        f1 = FakePublisher(should_succeed=True)
        f2 = FakePublisher(should_succeed=True)
        pipeline = PublisherPipeline(publishers=[f1, f2])
        vid = create_vacancy()
        results = pipeline.publish(vid)

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_one_failure_does_not_stop_others(self):
        f1 = FakePublisher(should_succeed=False)
        f2 = FakePublisher(should_succeed=True)
        pipeline = PublisherPipeline(publishers=[f1, f2])
        vid = create_vacancy()
        results = pipeline.publish(vid)

        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True

    def test_retry_on_failure(self):
        fake = FakePublisher(should_succeed=False)
        pipeline = PublisherPipeline(publishers=[fake])
        pipeline.max_retries = 3
        pipeline.retry_delay = 0.01

        vid = create_vacancy()
        results = pipeline.publish(vid)

        assert len(results) == 1
        assert results[0].success is False
        assert fake.call_count == 3
        assert '3 attempts' in results[0].error

    def test_retry_then_succeed(self):
        fake = FakePublisher(should_succeed=True, fail_count=1)
        pipeline = PublisherPipeline(publishers=[fake])
        pipeline.max_retries = 3
        pipeline.retry_delay = 0.01

        class RetryPublisher(FakePublisher):
            def __init__(self):
                super().__init__(should_succeed=True)
                self._attempts = 0

            def publish(self, vacancy_id):
                self._attempts += 1
                if self._attempts == 1:
                    raise Exception('First attempt failed')
                return PublishResult(
                    platform=self.platform, vacancy_id=vacancy_id,
                    success=True, post_id='retry_post'
                )

        rp = RetryPublisher()
        pipeline = PublisherPipeline(publishers=[rp])
        pipeline.max_retries = 3
        pipeline.retry_delay = 0.01

        vid = create_vacancy()
        results = pipeline.publish(vid)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].post_id == 'retry_post'

    def test_add_publisher(self):
        pipeline = PublisherPipeline()
        assert len(pipeline.publishers) == 0

        pipeline.add_publisher(FakePublisher(should_succeed=True))
        assert len(pipeline.publishers) == 1
