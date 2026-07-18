from __future__ import annotations

import base64
import re
from typing import Dict, List, Optional, Tuple


CATEGORIES = [
    'office', 'programming', 'medical', 'engineering',
    'corporate', 'creative', 'construction', 'education',
]

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    'office': ['admin', 'administrative', 'assistant', 'coordinator', 'executive',
               'management', 'manager', 'office', 'operations', 'receptionist',
               'secretary', 'supervisor', 'team lead'],
    'programming': ['developer', 'engineer', 'software', 'programmer', 'coding',
                    'full stack', 'frontend', 'backend', 'devops', 'data',
                    'algorithm', 'api', 'database', 'cloud', 'ai', 'ml',
                    'python', 'java', 'javascript', 'react', 'node', 'php'],
    'medical': ['doctor', 'nurse', 'medical', 'health', 'clinical', 'pharma',
                'dentist', 'surgeon', 'therapist', 'radiologist', 'lab',
                'hospital', 'patient', 'care', 'pharmacist', 'biotech'],
    'engineering': ['engineer', 'mechanical', 'electrical', 'civil', 'structural',
                    'architect', 'drafting', 'cad', 'project engineer',
                    'chemical', 'industrial', 'quality', 'manufacturing'],
    'corporate': ['director', 'vp', 'vice president', 'ceo', 'cfo', 'cto',
                  'finance', 'accounting', 'audit', 'legal', 'hr', 'human resources',
                  'business', 'strategy', 'consultant', 'analyst', 'corporate'],
    'creative': ['designer', 'creative', 'artist', 'graphic', 'ui', 'ux',
                 'photographer', 'video', 'editor', 'content', 'writer',
                 'copywriter', 'social media', 'marketing', 'brand', 'animator'],
    'construction': ['construction', 'laborer', 'electrician', 'plumber', 'welder',
                     'carpenter', 'mason', 'foreman', 'site', 'contractor',
                     'heavy equipment', 'driver', 'warehouse', 'logistics'],
    'education': ['teacher', 'professor', 'instructor', 'trainer', 'educator',
                  'academic', 'lecturer', 'principal', 'school', 'university',
                  'curriculum', 'tutor', 'mentor', 'coach', 'faculty'],
}


def detect_category(title: Optional[str], description: Optional[str]) -> str:
    text = f'{title or ""} {description or ""}'.lower()
    scores: Dict[str, int] = {}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text))
        if score > 0:
            scores[cat] = score
    if not scores:
        return 'corporate'
    return max(scores, key=scores.get)


def _svg_bg(svg: str) -> str:
    encoded = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f'data:image/svg+xml;base64,{encoded}'


def background_svg(category: str, theme_accent: str = '#2563eb') -> str:
    cat = category.lower()
    accent = theme_accent

    if cat == 'programming':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a0a1a"/>
      <stop offset="100%" stop-color="#1a1a2e"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{accent}" stroke-width="0.3" opacity="0.15"/>
    </pattern>
    <pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="10" cy="10" r="1.2" fill="{accent}" opacity="0.08"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#grid)"/>
  <rect width="800" height="1000" fill="url(#dots)"/>
  <text x="30" y="80" font-family="monospace" font-size="10" fill="{accent}" opacity="0.06">const vacancy = {{ title: &#34;{accent}&#34; }};</text>
  <text x="30" y="100" font-family="monospace" font-size="10" fill="{accent}" opacity="0.05">function hire(candidate) {{ return true; }}</text>
  <text x="30" y="120" font-family="monospace" font-size="10" fill="{accent}" opacity="0.04">class JobPosting extends Vacancy {{ ... }}</text>
</svg>'''

    elif cat == 'medical':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e8f4f8"/>
      <stop offset="100%" stop-color="#d4edf2"/>
    </linearGradient>
    <pattern id="cross" width="60" height="60" patternUnits="userSpaceOnUse">
      <path d="M25 10h10v15h15v10H35v15H25V35H10V25h15z" fill="{accent}" opacity="0.04"/>
    </pattern>
    <pattern id="lines" width="100" height="20" patternUnits="userSpaceOnUse">
      <line x1="0" y1="10" x2="100" y2="10" stroke="{accent}" stroke-width="0.5" opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#cross)"/>
  <rect width="800" height="1000" fill="url(#lines)"/>
</svg>'''

    elif cat == 'engineering':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f5f0e8"/>
      <stop offset="100%" stop-color="#e8e0d0"/>
    </linearGradient>
    <pattern id="blueprint" width="80" height="80" patternUnits="userSpaceOnUse">
      <rect width="80" height="80" fill="none" stroke="{accent}" stroke-width="0.4" opacity="0.1"/>
      <line x1="0" y1="0" x2="80" y2="80" stroke="{accent}" stroke-width="0.2" opacity="0.08"/>
    </pattern>
    <pattern id="circle" width="100" height="100" patternUnits="userSpaceOnUse">
      <circle cx="50" cy="50" r="30" fill="none" stroke="{accent}" stroke-width="0.5" opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#blueprint)"/>
  <rect width="800" height="1000" fill="url(#circle)"/>
  <line x1="0" y1="500" x2="800" y2="500" stroke="{accent}" stroke-width="0.5" opacity="0.08"/>
  <circle cx="400" cy="500" r="200" fill="none" stroke="{accent}" stroke-width="0.3" opacity="0.05"/>
</svg>'''

    elif cat == 'corporate' or cat == 'office':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f8f9fc"/>
      <stop offset="100%" stop-color="#eef1f6"/>
    </linearGradient>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="{accent}" stroke-width="0.3" opacity="0.06"/>
    </pattern>
    <pattern id="dash" width="60" height="4" patternUnits="userSpaceOnUse">
      <line x1="0" y1="2" x2="30" y2="2" stroke="{accent}" stroke-width="1" opacity="0.04"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#grid)"/>
  <rect x="0" y="0" width="800" height="4" fill="{accent}" opacity="0.08"/>
</svg>'''

    elif cat == 'creative':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1a0a2e"/>
      <stop offset="50%" stop-color="#2d1b69"/>
      <stop offset="100%" stop-color="#1a0a2e"/>
    </linearGradient>
    <pattern id="circle" width="80" height="80" patternUnits="userSpaceOnUse">
      <circle cx="40" cy="40" r="15" fill="none" stroke="#ff6b6b" stroke-width="0.5" opacity="0.08"/>
    </pattern>
    <pattern id="dots" width="30" height="30" patternUnits="userSpaceOnUse">
      <circle cx="15" cy="15" r="1" fill="#ffd93d" opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#circle)"/>
  <rect width="800" height="1000" fill="url(#dots)"/>
  <circle cx="100" cy="100" r="120" fill="#ff6b6b" opacity="0.03"/>
  <circle cx="700" cy="800" r="180" fill="#6bcbff" opacity="0.03"/>
  <circle cx="600" cy="200" r="80" fill="#ffd93d" opacity="0.04"/>
</svg>'''

    elif cat == 'construction':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1a1a1a"/>
      <stop offset="100%" stop-color="#2a2a2a"/>
    </linearGradient>
    <pattern id="hazard" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect width="20" height="20" fill="#ff6b00" opacity="0.04"/>
      <rect x="20" y="20" width="20" height="20" fill="#ff6b00" opacity="0.04"/>
    </pattern>
    <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
      <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#ff6b00" stroke-width="0.5" opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#hazard)"/>
  <rect width="800" height="1000" fill="url(#grid)"/>
  <line x1="0" y1="300" x2="800" y2="300" stroke="#ff6b00" stroke-width="2" opacity="0.05"/>
  <line x1="0" y1="700" x2="800" y2="700" stroke="#ff6b00" stroke-width="1" opacity="0.04"/>
</svg>'''

    elif cat == 'education':
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fef9ef"/>
      <stop offset="100%" stop-color="#f5f0e1"/>
    </linearGradient>
    <pattern id="book" width="60" height="60" patternUnits="userSpaceOnUse">
      <rect x="20" y="15" width="20" height="30" rx="2" fill="none" stroke="#8b6914" stroke-width="0.5" opacity="0.06"/>
      <line x1="30" y1="20" x2="30" y2="40" stroke="#8b6914" stroke-width="0.3" opacity="0.06"/>
    </pattern>
    <pattern id="lines" width="80" height="15" patternUnits="userSpaceOnUse">
      <line x1="0" y1="5" x2="60" y2="5" stroke="#8b6914" stroke-width="0.5" opacity="0.04"/>
      <line x1="0" y1="10" x2="40" y2="10" stroke="#8b6914" stroke-width="0.5" opacity="0.03"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#book)"/>
  <rect width="800" height="1000" fill="url(#lines)"/>
</svg>'''

    else:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f8f9fc"/>
      <stop offset="100%" stop-color="#eef1f6"/>
    </linearGradient>
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="{accent}" stroke-width="0.3" opacity="0.06"/>
    </pattern>
  </defs>
  <rect width="800" height="1000" fill="url(#bg)"/>
  <rect width="800" height="1000" fill="url(#grid)"/>
</svg>'''

    return _svg_bg(svg)


def overlay_gradient(category: str, theme: str) -> str:
    overlays = {
        'programming': 'linear-gradient(180deg, rgba(10,10,30,0.3) 0%, rgba(10,10,30,0.85) 50%, rgba(10,10,30,0.95) 100%)',
        'medical': 'linear-gradient(180deg, rgba(232,244,248,0.1) 0%, rgba(232,244,248,0.6) 60%, rgba(232,244,248,0.9) 100%)',
        'engineering': 'linear-gradient(180deg, rgba(245,240,232,0.1) 0%, rgba(245,240,232,0.5) 50%, rgba(245,240,232,0.9) 100%)',
        'corporate': 'linear-gradient(180deg, rgba(248,249,252,0) 0%, rgba(248,249,252,0.5) 40%, rgba(248,249,252,0.95) 100%)',
        'office': 'linear-gradient(180deg, rgba(248,249,252,0) 0%, rgba(248,249,252,0.5) 40%, rgba(248,249,252,0.95) 100%)',
        'creative': 'linear-gradient(180deg, rgba(26,10,46,0.2) 0%, rgba(26,10,46,0.7) 40%, rgba(26,10,46,0.95) 100%)',
        'construction': 'linear-gradient(180deg, rgba(26,26,26,0.3) 0%, rgba(26,26,26,0.8) 50%, rgba(26,26,26,0.95) 100%)',
        'education': 'linear-gradient(180deg, rgba(254,249,239,0.1) 0%, rgba(254,249,239,0.5) 50%, rgba(254,249,239,0.9) 100%)',
    }
    return overlays.get(category, overlays['corporate'])
