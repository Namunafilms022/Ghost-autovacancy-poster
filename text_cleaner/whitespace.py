from __future__ import annotations

import re
from typing import Optional

_DUPLICATE_SPACES_RE = re.compile(r' {2,}')
_LEADING_TRAILING_SPACES_RE = re.compile(r'^[ \t]+|[ \t]+$', re.MULTILINE)
_SPACE_BEFORE_PUNCTUATION_RE = re.compile(r' +([.,;:!?)}])')
_SPACE_AFTER_OPENING_RE = re.compile(r'([({[]) +')

_SMART_DOUBLE_LEFT = '\u201c'
_SMART_DOUBLE_RIGHT = '\u201d'
_SMART_SINGLE_LEFT = '\u2018'
_SMART_SINGLE_RIGHT = '\u2019'
_SMART_DOUBLE_LOW = '\u201e'
_SMART_SINGLE_LOW = '\u201a'
_SMART_DOUBLE_REVERSED = '\u201f'
_SMART_SINGLE_REVERSED = '\u201b'
_PRIME_DOUBLE = '\u2033'
_PRIME_SINGLE = '\u2032'
_DEGREE = '\u00b0'

_HIDDEN_CHARS = re.compile(
    '[\u0000-\u0008\u000b\u000c\u000e-\u001f'
    '\u007f-\u009f'
    '\u00ad'
    '\u034f'
    '\u061c'
    '\u115f\u1160'
    '\u17b4\u17b5'
    '\u180b-\u180f'
    '\u200b-\u200f'
    '\u2028\u2029'
    '\u202a-\u202f'
    '\u205f-\u2064'
    '\u2066-\u206f'
    '\u2800'
    '\u3164'
    '\ufeff\ufff9\ufffa\ufffb'
    '\U000e0001-\U000e007f]'
)

_MULTIPLE_NEWLINES_RE = re.compile(r'\n{3,}')
_TRAILING_NEWLINES_RE = re.compile(r'\n+$')
_LEADING_NEWLINES_RE = re.compile(r'^\n+')
_NEWLINE_IN_PARENTHESIS_RE = re.compile(r'\([^)]*\n[^)]*\)')
_LINE_START_SPACES_RE = re.compile(r'^[ \t]+', re.MULTILINE)


def remove_duplicate_spaces(text: str) -> str:
    result = _DUPLICATE_SPACES_RE.sub(' ', text)
    result = _SPACE_BEFORE_PUNCTUATION_RE.sub(r'\1', result)
    result = _SPACE_AFTER_OPENING_RE.sub(r'\1', result)
    return result


def trim_line_spaces(text: str) -> str:
    return _LEADING_TRAILING_SPACES_RE.sub('', text)


def convert_smart_quotes(text: str) -> str:
    result = text.replace(_SMART_DOUBLE_LEFT, '"')
    result = result.replace(_SMART_DOUBLE_RIGHT, '"')
    result = result.replace(_SMART_DOUBLE_LOW, '"')
    result = result.replace(_SMART_DOUBLE_REVERSED, '"')
    result = result.replace(_SMART_SINGLE_LEFT, "'")
    result = result.replace(_SMART_SINGLE_RIGHT, "'")
    result = result.replace(_SMART_SINGLE_LOW, "'")
    result = result.replace(_SMART_SINGLE_REVERSED, "'")
    return result


def convert_typographic_symbols(text: str) -> str:
    result = text.replace(_PRIME_DOUBLE, '"')
    result = result.replace(_PRIME_SINGLE, "'")
    result = result.replace(_DEGREE, '')
    result = result.replace('\u2013', '-')
    result = result.replace('\u2014', '-')
    result = result.replace('\u2026', '...')
    result = result.replace('\u00a0', ' ')
    return result


def remove_hidden_characters(text: str) -> str:
    return _HIDDEN_CHARS.sub('', text)


def normalize_newlines(text: str) -> str:
    result = text.replace('\r\n', '\n').replace('\r', '\n')
    result = _MULTIPLE_NEWLINES_RE.sub('\n\n', result)
    result = _LEADING_NEWLINES_RE.sub('', result)
    result = _TRAILING_NEWLINES_RE.sub('', result)
    return result


def remove_line_start_spaces(text: str) -> str:
    return _LINE_START_SPACES_RE.sub('', text)


def clean_whitespace(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = convert_smart_quotes(text)
    result = convert_typographic_symbols(result)
    result = remove_hidden_characters(result)
    result = normalize_newlines(result)
    result = trim_line_spaces(result)
    result = remove_line_start_spaces(result)
    result = remove_duplicate_spaces(result)
    return result.strip()
