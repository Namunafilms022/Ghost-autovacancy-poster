from __future__ import annotations

from typing import Optional

from .unicode import clean_unicode
from .emoji import normalize_emoji
from .markdown import strip_invalid_markdown
from .whitespace import clean_whitespace


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = clean_unicode(text)
    result = normalize_emoji(result)
    result = strip_invalid_markdown(result)
    result = clean_whitespace(result)
    return result


class TextCleaner:
    def clean(self, text: Optional[str]) -> Optional[str]:
        return clean_text(text)
