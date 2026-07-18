from __future__ import annotations

import re
from typing import Optional

_VARIATION_SELECTOR_RE = re.compile('[\ufe00-\ufe0f]')
_KEYCAP_RE = re.compile(r'[\u0023-\u0039]\ufe0f?\u20e3')
_FLAG_SEQUENCE_RE = re.compile(r'[\U0001f1e6-\U0001f1ff]{2}')
_ZWJ_SEQUENCE_RE = re.compile(r'(?:[\U0001f3fb-\U0001f3ff]|'
                              r'[\u200d]|'
                              r'[\U0001f9b0-\U0001f9b3]|'
                              r'[\U0001f1e6-\U0001f1ff]|'
                              r'[\U0001f3f4\U000e0061-\U000e007a\U000e0067\U000e0062\U000e0065\U000e006e\U000e007f])')
_SKIN_TONE_RE = re.compile(r'[\U0001f3fb-\U0001f3ff]')

_EMOJI_PATTERN = re.compile(
    r'[\U0001f300-\U0001f9ff]'
    r'|[\U0001fa00-\U0001fa6f]'
    r'|[\U0001fa70-\U0001faff]'
    r'|[\u2600-\u27bf]'
    r'|[\u231a-\u23fe]'
    r'|[\u2b50-\u2b55]'
    r'|[\u25aa-\u25fe]'
    r'|[\u24c2-\U0001f251]'
    r'|[\U0001f200-\U0001f2e0]'
    r'|[\U0001f600-\U0001f64f]'
    r'|[\U0001f680-\U0001f6ff]'
    r'|[\U0001f900-\U0001f9ff]'
)

_SINGLE_EMOJI_RE = re.compile(
    r'('
    r'(?:\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])'
    r')'
)

_EMOJI_DUPLICATE_RE = re.compile(r'((?:[\U0001f300-\U0001faff\u2600-\u27bf])\ufe0f?)\1{2,}')


def remove_variation_selectors(text: str) -> str:
    return _VARIATION_SELECTOR_RE.sub('', text)


def normalize_skin_tones(text: str) -> str:
    return _SKIN_TONE_RE.sub('\U0001f3fd', text)


def deduplicate_emojis(text: str) -> str:
    return _EMOJI_DUPLICATE_RE.sub(r'\1', text)


def normalize_emoji(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = remove_variation_selectors(text)
    result = normalize_skin_tones(result)
    result = deduplicate_emojis(result)
    return result
