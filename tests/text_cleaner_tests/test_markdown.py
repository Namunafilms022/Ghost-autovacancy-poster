import sys
sys.path.insert(0, '/root/project')

import pytest
from text_cleaner.markdown import (
    strip_html_tags,
    strip_images,
    strip_links,
    strip_code_blocks,
    strip_invalid_markdown,
)


class TestStripHtmlTags:
    def test_basic(self):
        assert strip_html_tags('<b>hello</b>') == 'hello'


class TestStripImages:
    def test_basic(self):
        assert strip_images('![alt](img.png)') == 'alt'


class TestStripLinks:
    def test_basic(self):
        assert strip_links('[text](http://example.com)') == 'text'


class TestStripCodeBlocks:
    def test_inline_code(self):
        result = strip_code_blocks('text `code` here')
        assert result == 'text  here'


class TestStripInvalidMarkdown:
    def test_full_pipeline(self):
        text = '# Hello\n\nThis is **bold** [link](http://example.com)\n\n```\ncode\n```\n\n---\n\n> quote'
        result = strip_invalid_markdown(text)
        assert '**bold**' in result
        assert 'link' in result
        assert 'code' not in result
        assert 'Hello' in result

    def test_none(self):
        assert strip_invalid_markdown(None) is None

    def test_empty(self):
        assert strip_invalid_markdown('') == ''
