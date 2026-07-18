import sys
sys.path.insert(0, '/root/project')

import pytest
from text_cleaner.unicode import (
    decode_unicode_escapes,
    remove_broken_escapes,
    remove_partial_surrogates,
    fix_malformed_utf8,
    clean_unicode,
)


class TestDecodeUnicodeEscapes:
    def test_basic_escape(self):
        assert decode_unicode_escapes('hello \\u2713 world') == 'hello ✓ world'

    def test_multiple_escapes(self):
        assert decode_unicode_escapes('\\u0048\\u0065\\u006c\\u006c\\u006f') == 'Hello'

    def test_bullet_point(self):
        assert decode_unicode_escapes('\\u2022 item') == '• item'

    def test_no_escape(self):
        assert decode_unicode_escapes('hello world') == 'hello world'

    def test_mixed_text(self):
        assert decode_unicode_escapes('Price: \\u20b9500') == 'Price: ₹500'


class TestRemoveBrokenEscapes:
    def test_broken_backslash(self):
        assert remove_broken_escapes('hello \\x world') == 'hello x world'

    def test_valid_escapes_preserved(self):
        assert remove_broken_escapes('hello\\nworld') == 'hello\\nworld'

    def test_double_backslash(self):
        assert remove_broken_escapes('hello\\\\world') == 'hello\\\\world'

    def test_mixed_valid_and_broken(self):
        assert remove_broken_escapes('line1\\nline2\\xline3') == 'line1\\nline2xline3'


class TestRemovePartialSurrogates:
    def test_high_surrogate(self):
        assert remove_partial_surrogates('\\uD800') == ''

    def test_low_surrogate(self):
        assert remove_partial_surrogates('\\uDC00') == ''

    def test_no_surrogate(self):
        assert remove_partial_surrogates('\\u0048') == '\\u0048'

    def test_mixed(self):
        text = 'valid\\u0048\\uD800invalid'
        result = remove_partial_surrogates(text)
        assert '\\u0048' in result
        assert '\\uD800' not in result


class TestFixMalformedUtf8:
    def test_valid_utf8(self):
        assert fix_malformed_utf8('hello') == 'hello'


class TestCleanUnicode:
    def test_full_pipeline(self):
        result = clean_unicode('hello \\u2713 world\\xbroken')
        assert '✓' in result

    def test_none(self):
        assert clean_unicode(None) is None

    def test_empty_string(self):
        assert clean_unicode('') == ''
