import sys
sys.path.insert(0, '/root/project')

import pytest
from text_cleaner import TextCleaner, clean_text


class TestTextCleaner:
    def test_full_pipeline(self):
        text = '# Hello\n\n\u2713 Requirements:\n- \u2022 Item 1 \u200b \n\n```\ncode\n```\n\n> quote'
        result = clean_text(text)
        assert result is not None
        assert 'Hello' in result
        assert '✓' in result
        assert '•' in result
        assert 'code' not in result
        assert 'quote' in result

    def test_none_input(self):
        assert clean_text(None) is None

    def test_empty_string(self):
        assert clean_text('') == ''

    def test_class_api(self):
        cleaner = TextCleaner()
        result = cleaner.clean('hello  world')
        assert result == 'hello world'

    def test_smart_quotes_and_unicode(self):
        text = '\u201cEngineer\u201d needed at \u20b950000'
        result = clean_text(text)
        assert '"Engineer"' in result
        assert '₹' in result

    def test_hidden_chars_removed(self):
        text = 'hello\u200bworld\u200b'
        result = clean_text(text)
        assert result == 'helloworld'
