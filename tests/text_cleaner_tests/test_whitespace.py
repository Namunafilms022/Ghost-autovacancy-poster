import sys
sys.path.insert(0, '/root/project')

import pytest
from text_cleaner.whitespace import (
    remove_duplicate_spaces,
    convert_smart_quotes,
    convert_typographic_symbols,
    remove_hidden_characters,
    normalize_newlines,
    clean_whitespace,
)


class TestRemoveDuplicateSpaces:
    def test_multiple_spaces(self):
        assert remove_duplicate_spaces('hello   world') == 'hello world'


class TestConvertSmartQuotes:
    def test_double_quotes(self):
        assert convert_smart_quotes('\u201cHello\u201d') == '"Hello"'

    def test_single_quotes(self):
        assert convert_smart_quotes('\u2018Hello\u2019') == "'Hello'"


class TestConvertTypographicSymbols:
    def test_en_dash(self):
        assert convert_typographic_symbols('\u2013') == '-'


class TestRemoveHiddenCharacters:
    def test_zero_width_space(self):
        assert remove_hidden_characters('hello\u200bworld') == 'helloworld'


class TestNormalizeNewlines:
    def test_windows_line_endings(self):
        assert normalize_newlines('hello\r\nworld') == 'hello\nworld'

    def test_multiple_newlines(self):
        assert normalize_newlines('hello\n\n\nworld') == 'hello\n\nworld'


class TestCleanWhitespace:
    def test_full_pipeline(self):
        text = '\n\n  hello\u200b\u201cworld\u201d   \n\n'
        result = clean_whitespace(text)
        assert 'hello' in result
        assert '"world"' in result

    def test_none(self):
        assert clean_whitespace(None) is None

    def test_empty(self):
        assert clean_whitespace('') == ''
