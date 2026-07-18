import sys
sys.path.insert(0, '/root/project')

import pytest
from text_cleaner.emoji import (
    remove_variation_selectors,
    normalize_skin_tones,
    deduplicate_emojis,
    normalize_emoji,
)


class TestRemoveVariationSelectors:
    def test_basic(self):
        assert remove_variation_selectors('a\ufe0fb') == 'ab'

    def test_no_variation_selector(self):
        assert remove_variation_selectors('hello') == 'hello'


class TestNormalizeSkinTones:
    def test_skin_tone_replaced(self):
        result = normalize_skin_tones('\U0001f3fb')
        assert result == '\U0001f3fd'


class TestDeduplicateEmojis:
    def test_dedup(self):
        result = deduplicate_emojis('😂😂😂')
        assert result == '😂'

    def test_no_dedup(self):
        assert deduplicate_emojis('😂😊') == '😂😊'


class TestNormalizeEmoji:
    def test_full_pipeline(self):
        assert normalize_emoji('hello\ufe0f') == 'hello'

    def test_none(self):
        assert normalize_emoji(None) is None

    def test_empty(self):
        assert normalize_emoji('') == ''
