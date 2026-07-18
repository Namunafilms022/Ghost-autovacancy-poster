import pytest
import re
import time
from poster.company import (
    CompanyBranding,
    get_company_branding,
    clear_cache,
    _initials_avatar,
    _color_from_name,
    _hsl_to_hex,
    _to_domain,
    _normalize_company,
    _guess_image_ext,
    _image_to_data_uri,
    _cache_key,
    _make_placeholder,
)


class TestNormalizeCompany:
    def test_strips_suffix(self):
        assert _normalize_company('Acme Corp') == 'acme'

    def test_strips_inc(self):
        assert _normalize_company('Tech Solutions Inc') == 'techsolutions'

    def test_strips_llc(self):
        assert _normalize_company('BuildCo LLC') == 'buildco'

    def test_strips_ltd(self):
        assert _normalize_company('Foo Ltd') == 'foo'

    def test_removes_special_chars(self):
        assert _normalize_company("O'Brien & Sons") == 'obriensons'

    def test_lowercases(self):
        assert _normalize_company('GLOBAL ENTERPRISES') == 'globalenterprises'


class TestToDomain:
    def test_simple(self):
        assert _to_domain('Acme') == 'acme.com'

    def test_with_suffix(self):
        assert _to_domain('Acme Corp') == 'acme.com'


class TestInitialsAvatar:
    def test_two_words(self):
        result = _initials_avatar('Acme Corp', '#2563eb')
        assert 'data:image/svg+xml;base64' in result
        assert 'AC' in str(base64_decode(result))

    def test_single_word(self):
        result = _initials_avatar('Google', '#ff0000')
        decoded = str(base64_decode(result))
        assert 'GO' in decoded

    def test_single_char(self):
        result = _initials_avatar('X', '#000')
        decoded = str(base64_decode(result))
        assert 'X' in decoded

    def test_three_words(self):
        result = _initials_avatar('International Business Machines', '#333')
        decoded = str(base64_decode(result))
        assert 'IB' in decoded

    def test_empty(self):
        result = _initials_avatar('', '#000')
        assert result is not None


class TestColorFromName:
    def test_returns_tuple(self):
        p, a = _color_from_name('Acme Corp')
        assert p.startswith('hsl(')
        assert a.startswith('hsl(')

    def test_deterministic(self):
        assert _color_from_name('Acme') == _color_from_name('Acme')
        assert _color_from_name('Google') != _color_from_name('Facebook')


class TestHslToHex:
    def test_red(self):
        assert _hsl_to_hex(0, 100, 50).lower() == '#ff0000'

    def test_green(self):
        assert _hsl_to_hex(120, 100, 50).lower() == '#00ff00'

    def test_blue(self):
        assert _hsl_to_hex(240, 100, 50).lower() == '#0000ff'

    def test_black(self):
        assert _hsl_to_hex(0, 0, 0).lower() == '#000000'

    def test_white(self):
        assert _hsl_to_hex(0, 0, 100).lower() == '#ffffff'


class TestGuessImageExt:
    def test_png(self):
        assert _guess_image_ext(b'\x89PNG\r\n\x1a\n...') == 'png'

    def test_jpeg(self):
        assert _guess_image_ext(b'\xff\xd8\xff\xe0...') == 'jpeg'

    def test_gif(self):
        assert _guess_image_ext(b'GIF89a...') == 'gif'

    def test_svg(self):
        assert _guess_image_ext(b'<svg xmlns="...">') == 'svg+xml'

    def test_unknown(self):
        assert _guess_image_ext(b'\x00\x01\x02\x03') == 'png'


class TestCacheKey:
    def test_consistent(self):
        assert _cache_key('Acme Corp') == _cache_key('Acme Corp')

    def test_different(self):
        assert _cache_key('Acme') != _cache_key('Google')

    def test_case_insensitive(self):
        assert _cache_key('ACME') == _cache_key('acme')


class TestCompanyBranding:
    def test_returns_branding_object(self):
        result = get_company_branding('Test')
        assert isinstance(result, CompanyBranding)

    def test_test_company_name_returns_placeholder(self):
        result = get_company_branding('TestCo')
        assert result.logo_is_placeholder is True
        assert result.website_url is None

    def test_unknown_short_name_returns_placeholder(self):
        result = get_company_branding('Acme')
        assert result.logo_is_placeholder is True

    def test_logo_data_uri_valid(self):
        result = get_company_branding('Acme')
        assert result.logo_data_uri.startswith('data:image/svg+xml;base64,')

    def test_brand_color_is_hex(self):
        result = get_company_branding('Acme')
        assert re.match(r'^#[0-9a-fA-F]{6}$', result.brand_color)

    def test_accent_color_is_hex(self):
        result = get_company_branding('Acme')
        assert re.match(r'^#[0-9a-fA-F]{6}$', result.accent_color)

    def test_company_name_preserved(self):
        result = get_company_branding('MyCompany')
        assert result.company == 'MyCompany'

    def test_cache_returns_same(self):
        clear_cache('Example')
        a = get_company_branding('Example')
        b = get_company_branding('Example')
        assert a.brand_color == b.brand_color


class TestClearCache:
    def test_clear_specific(self):
        clear_cache('Demo')
        get_company_branding('Demo')
        clear_cache('Demo')
        result = get_company_branding('Demo')
        assert result.logo_is_placeholder is True

    def test_clear_all(self):
        get_company_branding('Placeholder')
        clear_cache()
        result = get_company_branding('Placeholder')
        assert result is not None


def base64_decode(data_uri: str) -> bytes:
    import base64 as b64
    b64part = data_uri.split(',', 1)[1]
    return b64.b64decode(b64part)
