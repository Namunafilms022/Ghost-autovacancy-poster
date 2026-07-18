import pytest
from captions import generate_captions, get_platform_caption, CaptionResult, CaptionSet, PLATFORMS


class TestCaptionGeneration:
    def test_returns_caption_result(self):
        r = generate_captions(title='Dev', company='Co')
        assert isinstance(r, CaptionResult)
        assert r.title == 'Dev'
        assert r.company == 'Co'

    def test_all_platforms_present(self):
        r = generate_captions(title='Dev', company='Co')
        for p in PLATFORMS:
            cs = r.for_platform(p)
            assert cs is not None, f'Missing platform: {p}'
            assert isinstance(cs, CaptionSet)

    def test_each_platform_has_all_fields(self):
        r = generate_captions(title='Dev', company='Co')
        for p in PLATFORMS:
            cs = r.for_platform(p)
            assert cs.caption, f'{p} caption empty'
            assert cs.hashtags, f'{p} hashtags empty'
            assert cs.call_to_action, f'{p} cta empty'
            assert cs.short_version, f'{p} short empty'
            assert cs.long_version, f'{p} long empty'

    def test_full_text_includes_all(self):
        r = generate_captions(title='Dev', company='Co')
        cs = r.for_platform('facebook')
        ft = cs.full_text()
        assert cs.caption in ft
        assert cs.hashtags in ft
        assert cs.call_to_action in ft


class TestPlatformSpecific:
    def test_facebook_has_friendly_tone(self):
        r = generate_captions(title='Dev', company='Co')
        cs = r.for_platform('facebook')
        assert "we're" in cs.caption.lower() or "hiring" in cs.caption.lower()

    def test_instagram_has_emojis(self):
        r = generate_captions(title='Dev', company='Co')
        cs = r.for_platform('instagram')
        assert '🚀' in cs.caption or '📸' in cs.caption or '💼' in cs.caption

    def test_linkedin_has_professional_tone(self):
        r = generate_captions(title='Dev', company='Co')
        cs = r.for_platform('linkedin')
        assert 'announce' in cs.caption.lower() or 'excited' in cs.caption.lower()

    def test_telegram_has_job_alert(self):
        r = generate_captions(title='Dev', company='Co')
        cs = r.for_platform('telegram')
        assert 'job alert' in cs.caption.lower() or 'job' in cs.caption.lower()

    def test_twitter_is_short(self):
        r = generate_captions(title='Senior Python Developer with extensive experience', company='Very Long Company Name That Keeps Going')
        cs = r.for_platform('twitter')
        assert len(cs.caption) <= 280

    def test_salary_in_caption(self):
        r = generate_captions(title='Dev', company='Co', salary_min=50000, salary_max=80000)
        text = r.for_platform('facebook').caption
        assert '80,000' in text or '50,000' in text

    def test_location_in_caption(self):
        r = generate_captions(title='Dev', company='Co', location='Kathmandu')
        text = r.for_platform('facebook').caption
        assert 'Kathmandu' in text

    def test_requirements_in_long_version(self):
        r = generate_captions(title='Dev', company='Co', requirements=['Python', 'Django'])
        text = r.for_platform('linkedin').long_version
        assert 'Python' in text


class TestHashtags:
    def test_tech_category_tags(self):
        r = generate_captions(title='Python Developer', company='Co')
        cs = r.for_platform('facebook')
        assert '#techjobs' in cs.hashtags or '#softwareengineer' in cs.hashtags

    def test_medical_category_tags(self):
        r = generate_captions(title='Registered Nurse', company='Hospital')
        cs = r.for_platform('facebook')
        assert '#healthcare' in cs.hashtags

    def test_instagram_has_more_tags(self):
        r = generate_captions(title='Dev', company='Co')
        fb_tags = r.for_platform('facebook').hashtags.count('#')
        ig_tags = r.for_platform('instagram').hashtags.count('#')
        assert ig_tags >= fb_tags

    def test_twitter_has_few_tags(self):
        r = generate_captions(title='Dev', company='Co')
        tw_tags = r.for_platform('twitter').hashtags.count('#')
        assert tw_tags <= 6


class TestCallToAction:
    def test_cta_not_empty(self):
        r = generate_captions(title='Dev', company='Co')
        for p in PLATFORMS:
            assert r.for_platform(p).call_to_action.strip()


class TestGetPlatformCaption:
    def test_valid_platform(self):
        r = generate_captions(title='Dev', company='Co')
        cs = get_platform_caption(r, 'facebook')
        assert cs is not None

    def test_invalid_platform(self):
        r = generate_captions(title='Dev', company='Co')
        cs = get_platform_caption(r, 'tiktok')
        assert cs is None
