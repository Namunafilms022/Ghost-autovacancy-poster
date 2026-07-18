from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FontPair:
    heading: str
    body: str
    url: Optional[str] = None


@dataclass
class Theme:
    name: str
    label: str
    background: str
    accent: str
    accent_secondary: str
    text_primary: str
    text_secondary: str
    surface: str
    surface_alt: str
    border: str
    font: FontPair
    card_style: str
    spacing: str
    icons: str
    header_gradient: str
    success: str = '#22c55e'
    warning: str = '#eab308'
    error: str = '#ef4444'
    radius: str = '16px'

    @property
    def css_vars(self) -> str:
        return f'''
  --bg: {self.background};
  --accent: {self.accent};
  --accent-secondary: {self.accent_secondary};
  --text-primary: {self.text_primary};
  --text-secondary: {self.text_secondary};
  --surface: {self.surface};
  --surface-alt: {self.surface_alt};
  --border: {self.border};
  --success: {self.success};
  --warning: {self.warning};
  --error: {self.error};
  --radius: {self.radius};
  --spacing: {self.spacing};
  --card-style: {self.card_style};
  --icons-style: {self.icons};
  --header-gradient: {self.header_gradient};
'''

    @property
    def font_link(self) -> str:
        if self.font.url:
            return f'<link href="{self.font.url}" rel="stylesheet">'
        return ''

    @property
    def font_stack(self) -> str:
        return f'"{self.font.heading}", "{self.font.body}", system-ui, -apple-system, sans-serif'


MINIMAL = Theme(
    name='minimal',
    label='Minimal',
    background='#fafafa',
    accent='#000000',
    accent_secondary='#888888',
    text_primary='#000000',
    text_secondary='#666666',
    surface='#ffffff',
    surface_alt='#f5f5f5',
    border='#eeeeee',
    font=FontPair('Inter', 'Inter', 'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap'),
    card_style='none',
    spacing='loose',
    icons='text',
    header_gradient='none',
    radius='0px',
)

GLASS = Theme(
    name='glass',
    label='Glass',
    background='linear-gradient(135deg, #0f0c29, #302b63, #24243e)',
    accent='rgba(255,255,255,0.15)',
    accent_secondary='rgba(255,255,255,0.08)',
    text_primary='#ffffff',
    text_secondary='rgba(255,255,255,0.7)',
    surface='rgba(255,255,255,0.08)',
    surface_alt='rgba(255,255,255,0.05)',
    border='rgba(255,255,255,0.12)',
    font=FontPair('Outfit', 'Outfit', 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap'),
    card_style='backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid var(--border);',
    spacing='cozy',
    icons='minimal',
    header_gradient='rgba(255,255,255,0.05)',
    radius='20px',
)

DARK_NEON = Theme(
    name='dark_neon',
    label='Dark Neon',
    background='#0a0a0f',
    accent='#00ff88',
    accent_secondary='#ff00ff',
    text_primary='#e0e0e0',
    text_secondary='#888899',
    surface='#12121a',
    surface_alt='#1a1a24',
    border='#2a2a3a',
    font=FontPair('Space Grotesk', 'Space Grotesk', 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap'),
    card_style='border: 1px solid var(--border); box-shadow: 0 0 30px rgba(0,255,136,0.05);',
    spacing='standard',
    icons='neon',
    header_gradient='linear-gradient(135deg, #00ff88 0%, #ff00ff 100%)',
    radius='12px',
)

CORPORATE_HIRING_RED = Theme(
    name='corporate_hiring_red',
    label='Corporate Hiring Red',
    background='#f8f6f4',
    accent='#dc2626',
    accent_secondary='#991b1b',
    text_primary='#1a1a2e',
    text_secondary='#6b7280',
    surface='#ffffff',
    surface_alt='#fef2f2',
    border='#e5e7eb',
    font=FontPair('Merriweather', 'Merriweather', 'https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700;900&display=swap'),
    card_style='border-left: 4px solid var(--accent); box-shadow: 0 2px 12px rgba(220,38,38,0.08);',
    spacing='standard',
    icons='bold',
    header_gradient='linear-gradient(135deg, #dc2626, #991b1b)',
    radius='8px',
)

GHOST = Theme(
    name='ghost',
    label='Ghost',
    background='#0d1117',
    accent='#8b5cf6',
    accent_secondary='#6d28d9',
    text_primary='#e2e8f0',
    text_secondary='#94a3b8',
    surface='#1e293b',
    surface_alt='#0f172a',
    border='#334155',
    font=FontPair('Inter', 'Inter', 'https://fonts.googleapis.com/css2?family=Inter:wght@300;500;700&display=swap'),
    card_style='border: 1px solid var(--border); opacity: 0.92;',
    spacing='airy',
    icons='subtle',
    header_gradient='linear-gradient(135deg, #8b5cf6, #1e293b)',
    radius='10px',
)

CYBERPUNK = Theme(
    name='cyberpunk',
    label='Cyberpunk',
    background='#0c0c1d',
    accent='#f0e100',
    accent_secondary='#ff006e',
    text_primary='#ffffff',
    text_secondary='#c0c0d0',
    surface='#1a1a2e',
    surface_alt='#16213e',
    border='#2a2a4a',
    font=FontPair('Orbitron', 'Orbitron', 'https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap'),
    card_style='border: 2px solid var(--accent); box-shadow: 0 0 25px rgba(240,225,0,0.1), inset 0 0 25px rgba(240,225,0,0.02);',
    spacing='tight',
    icons='cyber',
    header_gradient='linear-gradient(135deg, #f0e100, #ff006e)',
    radius='4px',
)

BLUE_PROFESSIONAL = Theme(
    name='blue_professional',
    label='Blue Professional',
    background='#f0f4f8',
    accent='#2563eb',
    accent_secondary='#1e40af',
    text_primary='#0f172a',
    text_secondary='#475569',
    surface='#ffffff',
    surface_alt='#eff6ff',
    border='#cbd5e1',
    font=FontPair('Plus Jakarta Sans', 'Plus Jakarta Sans', 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap'),
    card_style='box-shadow: 0 4px 24px rgba(37,99,235,0.08);',
    spacing='standard',
    icons='professional',
    header_gradient='linear-gradient(135deg, #2563eb, #1e40af)',
    radius='12px',
)


ALL_THEMES: List[Theme] = [
    MINIMAL,
    GLASS,
    DARK_NEON,
    CORPORATE_HIRING_RED,
    GHOST,
    CYBERPUNK,
    BLUE_PROFESSIONAL,
]

THEME_MAP: Dict[str, Theme] = {t.name: t for t in ALL_THEMES}
AVAILABLE_THEMES: List[str] = list(THEME_MAP.keys())


def get_theme(name: str) -> Theme:
    if name not in THEME_MAP:
        raise ValueError(
            f"Unknown theme '{name}'. Available: {AVAILABLE_THEMES}"
        )
    return THEME_MAP[name]


def auto_select_theme(confidence: Optional[float] = None,
                      job_type: Optional[str] = None,
                      experience: Optional[str] = None) -> str:
    if confidence is not None:
        if confidence >= 0.9:
            return 'blue_professional'
        if confidence >= 0.7:
            return 'dark_neon'
        if confidence < 0.5:
            return 'ghost'
    if job_type:
        jt = job_type.lower().replace('_', ' ')
        if 'freelance' in jt:
            return 'cyberpunk'
        if 'intern' in jt:
            return 'glass'
        if 'contract' in jt:
            return 'corporate_hiring_red'
    if experience:
        ex = experience.lower().replace('_', ' ')
        if 'senior' in ex or 'lead' in ex:
            return 'blue_professional'
        if 'entry' in ex or 'junior' in ex:
            return 'minimal'
    return 'dark_neon'
