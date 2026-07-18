from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TemplatePreset:
    name: str
    label: str
    description: str
    theme: str
    category: str
    font: str
    accent: str
    bg: str
    text_color: str
    surface: str
    show_icons: bool
    icon_style: str


TEMPLATES: List[TemplatePreset] = [
    TemplatePreset(
        name='ghost',
        label='Ghost',
        description='Dark purple theme with subtle icons — perfect for tech & startup hiring',
        theme='ghost',
        category='corporate',
        font='Inter',
        accent='#8b5cf6',
        bg='#0f172a',
        text_color='#e2e8f0',
        surface='#1e293b',
        show_icons=True,
        icon_style='subtle',
    ),
    TemplatePreset(
        name='theme',
        label='Theme',
        description='Versatile dark neon with code-style background — great for developer roles',
        theme='dark_neon',
        category='programming',
        font='Space Grotesk',
        accent='#00ff88',
        bg='#0a0a0f',
        text_color='#e0e0e0',
        surface='#12121a',
        show_icons=True,
        icon_style='neon',
    ),
    TemplatePreset(
        name='corporate',
        label='Corporate',
        description='Clean blue professional — standard corporate hiring template',
        theme='blue_professional',
        category='corporate',
        font='Plus Jakarta Sans',
        accent='#2563eb',
        bg='#f0f4f8',
        text_color='#0f172a',
        surface='#ffffff',
        show_icons=True,
        icon_style='professional',
    ),
    TemplatePreset(
        name='minimal',
        label='Minimal',
        description='Clean white/black with office background — no distractions',
        theme='minimal',
        category='office',
        font='Inter',
        accent='#000000',
        bg='#fafafa',
        text_color='#000000',
        surface='#ffffff',
        show_icons=False,
        icon_style='text',
    ),
    TemplatePreset(
        name='medical',
        label='Medical',
        description='Clean light theme with medical cross pattern — for healthcare roles',
        theme='blue_professional',
        category='medical',
        font='Inter',
        accent='#0891b2',
        bg='#f0fdfa',
        text_color='#0f172a',
        surface='#ffffff',
        show_icons=True,
        icon_style='subtle',
    ),
    TemplatePreset(
        name='hiring',
        label='Hiring',
        description='Bold red accent with urgent feel — classic hiring poster',
        theme='corporate_hiring_red',
        category='corporate',
        font='Merriweather',
        accent='#dc2626',
        bg='#f8f6f4',
        text_color='#1a1a2e',
        surface='#ffffff',
        show_icons=True,
        icon_style='bold',
    ),
    TemplatePreset(
        name='construction',
        label='Construction',
        description='Dark industrial with hazard pattern — for trades & labor roles',
        theme='dark_neon',
        category='construction',
        font='Inter',
        accent='#ea580c',
        bg='#1a1a1a',
        text_color='#e2e8f0',
        surface='#262626',
        show_icons=True,
        icon_style='subtle',
    ),
    TemplatePreset(
        name='tech',
        label='Tech',
        description='Cyberpunk neon with code grid — for developer & IT positions',
        theme='cyberpunk',
        category='programming',
        font='Orbitron',
        accent='#f0e100',
        bg='#0c0c1d',
        text_color='#ffffff',
        surface='#1a1a2e',
        show_icons=True,
        icon_style='cyber',
    ),
    TemplatePreset(
        name='education',
        label='Education',
        description='Warm light theme with book pattern — for teaching & academic roles',
        theme='minimal',
        category='education',
        font='Merriweather',
        accent='#b45309',
        bg='#fef9ef',
        text_color='#1c1917',
        surface='#ffffff',
        show_icons=True,
        icon_style='subtle',
    ),
    TemplatePreset(
        name='startup',
        label='Startup',
        description='Glass-morphism with vibrant creative background — modern & fresh',
        theme='glass',
        category='creative',
        font='Outfit',
        accent='#a855f7',
        bg='#0f0c29',
        text_color='#ffffff',
        surface='rgba(255,255,255,0.08)',
        show_icons=True,
        icon_style='neon',
    ),
]

TEMPLATE_MAP: Dict[str, TemplatePreset] = {t.name: t for t in TEMPLATES}


def get_template(name: str) -> TemplatePreset:
    if name not in TEMPLATE_MAP:
        raise ValueError(f"Unknown template '{name}'. Available: {list(TEMPLATE_MAP.keys())}")
    return TEMPLATE_MAP[name]


def list_templates() -> List[TemplatePreset]:
    return TEMPLATES
