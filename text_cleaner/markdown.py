from __future__ import annotations

import re
from typing import Optional

_HTML_TAG_RE = re.compile(r'<[^>]*>')
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
_LINK_RE = re.compile(r'\[([^\]]*)\]\([^)]+\)')
_CODE_BLOCK_RE = re.compile(r'```[\s\S]*?```|`[^`]+`')
_BLOCKQUOTE_RE = re.compile(r'^>{1,6}\s?', re.MULTILINE)
_HORIZONTAL_RULE_RE = re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE)
_SETEXT_HEADING_RE = re.compile(r'^[=-]+\s*$', re.MULTILINE)
_ATX_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_TABLE_SEPARATOR_RE = re.compile(r'^\|?[-:| ]+\|?[-:| ]*$', re.MULTILINE)
_FENCED_CODE_START_RE = re.compile(r'^```\w*\s*$', re.MULTILINE)
_FENCED_CODE_END_RE = re.compile(r'^```\s*$', re.MULTILINE)
_STRIKETHROUGH_RE = re.compile(r'~~([^~]+)~~')
_MULTILINE_BLOCKQUOTE_RE = re.compile(r'^>(?:>|\s)+', re.MULTILINE)
_REFERENCE_LINK_RE = re.compile(r'^\[([^\]]+)\]:\s+\S+.*$', re.MULTILINE)


def strip_html_tags(text: str) -> str:
    return _HTML_TAG_RE.sub('', text)


def strip_images(text: str) -> str:
    return _IMAGE_RE.sub(r'\1', text)


def strip_links(text: str) -> str:
    return _LINK_RE.sub(r'\1', text)


def strip_code_blocks(text: str) -> str:
    return _CODE_BLOCK_RE.sub('', text)


def strip_blockquotes(text: str) -> str:
    return _BLOCKQUOTE_RE.sub('', text)


def strip_horizontal_rules(text: str) -> str:
    return _HORIZONTAL_RULE_RE.sub('', text)


def strip_setext_headings(text: str) -> str:
    return _SETEXT_HEADING_RE.sub('', text)


def strip_atx_headings(text: str) -> str:
    return _ATX_HEADING_RE.sub('', text)


def strip_table_separators(text: str) -> str:
    return _TABLE_SEPARATOR_RE.sub('', text)


def strip_strikethrough(text: str) -> str:
    return _STRIKETHROUGH_RE.sub(r'\1', text)


def strip_reference_links(text: str) -> str:
    return _REFERENCE_LINK_RE.sub('', text)


def strip_invalid_markdown(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = strip_code_blocks(text)
    result = strip_html_tags(result)
    result = strip_images(result)
    result = strip_links(result)
    result = strip_blockquotes(result)
    result = strip_horizontal_rules(result)
    result = strip_setext_headings(result)
    result = strip_atx_headings(result)
    result = strip_table_separators(result)
    result = strip_strikethrough(result)
    result = strip_reference_links(result)
    return result.strip()
