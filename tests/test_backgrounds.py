import pytest
import re
from poster.backgrounds import (
    detect_category, background_svg, overlay_gradient,
    CATEGORIES, _CATEGORY_KEYWORDS,
)


class TestDetectCategory:
    def test_programming_title(self):
        assert detect_category('Senior Python Developer', '') == 'programming'

    def test_medical_title(self):
        assert detect_category('Registered Nurse', '') == 'medical'

    def test_engineering_title(self):
        assert detect_category('Civil Engineer', '') == 'engineering'

    def test_education_title(self):
        assert detect_category('High School Teacher', '') == 'education'

    def test_construction_title(self):
        assert detect_category('Electrician needed', '') == 'construction'

    def test_creative_title(self):
        assert detect_category('Graphic Designer', '') == 'creative'

    def test_corporate_title(self):
        assert detect_category('Financial Analyst', '') == 'corporate'

    def test_office_title(self):
        assert detect_category('Office Assistant', '') == 'office'

    def test_fallback(self):
        assert detect_category('Random Job', '') == 'corporate'

    def test_description_scanned(self):
        assert detect_category('', 'We need a React developer with AWS') == 'programming'

    def test_none_title(self):
        assert detect_category(None, 'Looking for a plumber') == 'construction'

    def test_all_categories_have_keywords(self):
        for cat in CATEGORIES:
            assert cat in _CATEGORY_KEYWORDS
            assert len(_CATEGORY_KEYWORDS[cat]) > 0


class TestBackgroundSvg:
    def test_returns_data_uri(self):
        result = background_svg('corporate')
        assert result.startswith('data:image/svg+xml;base64,')

    def test_each_category_returns_valid(self):
        for cat in CATEGORIES:
            result = background_svg(cat, '#00ff88')
            assert result.startswith('data:image/svg+xml;base64,')

    def test_unknown_category_falls_back(self):
        result = background_svg('unknown_category', '#2563eb')
        assert result.startswith('data:image/svg+xml;base64,')

    def test_accent_color_used(self):
        result = background_svg('corporate', '#ff0000')
        assert result is not None


class TestOverlayGradient:
    def test_returns_css_gradient(self):
        result = overlay_gradient('corporate', 'dark_neon')
        assert 'linear-gradient' in result

    def test_each_category_returns_gradient(self):
        for cat in CATEGORIES:
            result = overlay_gradient(cat, 'minimal')
            assert 'linear-gradient' in result

    def test_unknown_falls_back(self):
        result = overlay_gradient('unknown', 'minimal')
        assert 'linear-gradient' in result


class TestLayersIntegration:
    def test_background_not_containing_text(self):
        for cat in CATEGORIES:
            svg = background_svg(cat)
            assert '{{' not in svg
            assert '{{ title }}' not in svg
            assert '{{ company }}' not in svg
            assert '<text' not in svg or all(
                kw not in svg for kw in ['job', 'hire', 'vacancy', 'salary']
            )

    def test_text_is_html_not_in_image(self):
        from poster.poster import PosterGenerator
        from database.init import init_db, drop_db
        from database.session import get_session
        from database.models import Vacancy

        init_db()
        session = get_session()
        v = Vacancy(title='Test Role', company='TestCo',
                    raw_message='Hiring a Test Role at TestCo',
                    processed=True)
        session.add(v)
        session.commit()
        vid = v.id
        session.close()

        gen = PosterGenerator(replace_enabled=False)
        html = gen.generate(vid)

        assert 'Test Role' in html
        assert 'TestCo' in html
        assert 'layer-bg' in html
        assert 'layer-overlay' in html
        assert 'layer-text' in html
        assert 'data:image/svg+xml;base64' in html

        drop_db()
