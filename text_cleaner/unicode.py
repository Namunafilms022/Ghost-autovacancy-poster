from __future__ import annotations

import re
from typing import Optional

_UNICODE_ESCAPE_RE = re.compile(r'\\u([0-9a-fA-F]{4})')
_BROKEN_ESCAPE_RE = re.compile(r'(?<!\\)\\(?![nrt\\\'\"0])')
_PARTIAL_SURROGATE_RE = re.compile(r'\\u[Dd][89aAbBcCdDeEfF][0-9a-fA-F]{2}|\\u[Dd][cCdDeEfF][0-9a-fA-F]{2}', re.IGNORECASE)
_MALFORMED_CONTINUATION_RE = re.compile(
    b'[\xc0-\xdf](?=[^\x80-\xbf])'
    b'|[\xe0-\xef](?=[^\x80-\xbf]{2})'
    b'|[\xf0-\xf4](?=[^\x80-\xbf]{3})'
)
_REPLACEMENT_CHAR = '\ufffd'


def decode_unicode_escapes(text: str) -> str:
    if '\\u' not in text:
        return text
    return _UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def remove_broken_escapes(text: str) -> str:
    return _BROKEN_ESCAPE_RE.sub('', text)


def remove_partial_surrogates(text: str) -> str:
    return _PARTIAL_SURROGATE_RE.sub('', text)


def fix_malformed_utf8(text: str) -> str:
    raw = text.encode('utf-8', errors='replace')
    fixed = _MALFORMED_CONTINUATION_RE.sub(_REPLACEMENT_CHAR.encode('utf-8'), raw)
    return fixed.decode('utf-8', errors='replace')


def clean_unicode(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = decode_unicode_escapes(text)
    result = remove_partial_surrogates(result)
    result = fix_malformed_utf8(result)
    result = remove_broken_escapes(result)
    return result
