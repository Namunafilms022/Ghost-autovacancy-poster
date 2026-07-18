from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LayerContext:
    background_svg: str
    background_category: str
    overlay_css: str
    overlay_opacity: str
    surface_opacity: str
    icons_decorative: List[str]
    show_icons_layer: bool


_DECORATIVE_ICONS: Dict[str, List[str]] = {
    'programming': ['</>', '{ }', '()', '[]', '->', '=>', '#', '/* */'],
    'medical': ['+', 'Rx', '<3', '†', '□'],
    'engineering': ['∠', '∆', '∑', 'π', '√', '∫', '≈'],
    'corporate': ['▲', '■', '●', '♦', '↑', '→'],
    'office': ['□', '○', '△', '◇', '☆'],
    'creative': ['✦', '◆', '✿', '♢', '♠', '♥', '●'],
    'construction': ['▲', '◆', '⬛', '■'],
    'education': ['△', '○', '□', '☆', '✎', '†'],
}


def build_layer_context(category: str, bg_svg: str, overlay: str) -> LayerContext:
    icons = _DECORATIVE_ICONS.get(category, _DECORATIVE_ICONS['corporate'])

    is_dark = any(c in bg_svg.lower() for c in ['0a0a1a', '1a1a1a', '1a0a2e', '0a0a0f'])
    surface_opacity = '0.85' if is_dark else '0.92'
    overlay_opacity = '0.6' if is_dark else '0.4'

    return LayerContext(
        background_svg=bg_svg,
        background_category=category,
        overlay_css=overlay,
        overlay_opacity=overlay_opacity,
        surface_opacity=surface_opacity,
        icons_decorative=icons,
        show_icons_layer=True,
    )
