from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests

CACHE_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'data', 'company_cache'))
CACHE_META_FILE = CACHE_DIR / 'cache_meta.json'
PLACEHOLDER_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'data', 'company_logos'))

CACHE_TTL = 86400 * 7

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)
_REQUEST_TIMEOUT = (3, 4)
_MAX_REDIRECTS = 3

_SKIP_COMPANIES = {
    'test', 'testco', 'testcorp', 'test company', 'testcompany',
    'unknown', 'unknown company', 'acme', 'acme corp', 'example',
    'example company', 'demo', 'democo', 'placeholder', 'none',
    'n/a', 'not specified',
}


@dataclass
class CompanyBranding:
    company: str
    website_url: Optional[str]
    logo_data_uri: Optional[str]
    logo_is_placeholder: bool
    brand_color: str
    accent_color: str


def _normalize_company(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+(inc|llc|ltd|corp|corporation|limited|company|co|gmbh|sarl|pty|plc)$', '', s)
    s = re.sub(r'\s+', '', s)
    return s


def _to_domain(name: str) -> str:
    return _normalize_company(name) + '.com'


def _load_cache_meta() -> Dict[str, dict]:
    try:
        if CACHE_META_FILE.exists():
            return json.loads(CACHE_META_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_cache_meta(meta: Dict[str, dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_META_FILE.write_text(json.dumps(meta, indent=2))


def _cache_key(company: str) -> str:
    return hashlib.md5(company.strip().lower().encode()).hexdigest()


def _is_cached(company: str) -> Optional[dict]:
    meta = _load_cache_meta()
    key = _cache_key(company)
    entry = meta.get(key)
    if entry and time.time() - entry.get('ts', 0) < CACHE_TTL:
        return entry
    return None


def _write_cache(company: str, data: dict) -> None:
    meta = _load_cache_meta()
    key = _cache_key(company)
    data['ts'] = int(time.time())
    meta[key] = data
    _save_cache_meta(meta)


def _fetch_url(url: str, timeout: tuple = (3, 4)) -> Optional[requests.Response]:
    try:
        resp = requests.get(
            url, timeout=timeout, allow_redirects=True,
            headers={'User-Agent': _USER_AGENT},
        )
        if resp.status_code == 200:
            return resp
    except requests.RequestException:
        pass
    return None


def _find_website(company: str) -> Optional[str]:
    normalized = company.strip().lower()
    if normalized in _SKIP_COMPANIES or len(normalized) < 3:
        return None
    domain = _to_domain(company)
    for url in [f'https://{domain}', f'https://www.{domain}']:
        try:
            resp = requests.head(
                url, timeout=(2, 3), allow_redirects=True,
                headers={'User-Agent': _USER_AGENT},
            )
            if resp.status_code < 400:
                return resp.url.rstrip('/')
        except requests.RequestException:
            pass
    return None


def _fetch_favicon(website_url: str) -> Optional[bytes]:
    parsed = urlparse(website_url)
    base = f'{parsed.scheme}://{parsed.netloc}'

    html_resp = _fetch_url(website_url)
    favicon_urls = [f'{base}/favicon.ico']

    if html_resp:
        html = html_resp.text
        patterns = [
            r'<link[^>]*rel=["\'](?:shortcut )?icon["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut )?icon["\']',
            r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']apple-touch-icon["\']',
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                href = m.group(1)
                abs_url = urljoin(website_url, href)
                favicon_urls.insert(0, abs_url)

    seen = set()
    for url in favicon_urls:
        if url in seen:
            continue
        seen.add(url)
        resp = _fetch_url(url)
        if resp and len(resp.content) > 50:
            return resp.content

    if html_resp:
        html = html_resp.text
        og_pat = r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']'
        om = re.search(og_pat, html, re.IGNORECASE)
        if not om:
            og_pat = r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']'
            om = re.search(og_pat, html, re.IGNORECASE)
        if om:
            img_url = urljoin(website_url, om.group(1))
            resp = _fetch_url(img_url)
            if resp and len(resp.content) > 100:
                return resp.content

    return None


def _extract_brand_color(website_url: str, html: Optional[str] = None) -> Optional[str]:
    if html is None:
        resp = _fetch_url(website_url)
        if resp:
            html = resp.text
    if html:
        m = re.search(r'<meta\s+[^>]*name=["\']theme-color["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m:
            c = m.group(1).strip()
            if re.match(r'^#[0-9a-fA-F]{3,6}$', c):
                return c
        m = re.search(r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']theme-color["\']', html, re.IGNORECASE)
        if m:
            c = m.group(1).strip()
            if re.match(r'^#[0-9a-fA-F]{3,6}$', c):
                return c
    return None


def _color_from_name(name: str) -> Tuple[str, str]:
    h = int(hashlib.md5(name.strip().lower().encode()).hexdigest()[:6], 16)
    hue = h % 360
    sat = 55 + (h % 30)
    light = 40 + (h % 20)
    alt_light = light + 15
    primary = f'hsl({hue}, {sat}%, {light}%)'
    accent = f'hsl({hue}, {sat}%, {alt_light}%)'
    return primary, accent


def _hsl_to_hex(h: int, s: int, l: int) -> str:
    s /= 100
    l /= 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return f'#{int((r + m) * 255):02x}{int((g + m) * 255):02x}{int((b + m) * 255):02x}'


def _initials_avatar(company: str, bg_color: str, fg_color: str = '#ffffff') -> str:
    name = company.strip()
    if not name:
        name = '?'
    words = name.split()
    if len(words) >= 2:
        init = (words[0][0] + words[1][0]).upper()
    else:
        init = (name[:2] if len(name) >= 2 else name[0]).upper()

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">
  <circle cx="40" cy="40" r="40" fill="{bg_color}"/>
  <text x="40" y="40" text-anchor="middle" dominant-baseline="central"
        font-family="system-ui, sans-serif" font-size="32" font-weight="700"
        fill="{fg_color}">{init}</text>
</svg>'''
    encoded = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
    return f'data:image/svg+xml;base64,{encoded}'


def _image_to_data_uri(data: bytes) -> str:
    ext = _guess_image_ext(data)
    b64 = base64.b64encode(data).decode('utf-8')
    return f'data:image/{ext};base64,{b64}'


def _guess_image_ext(data: bytes) -> str:
    if data.startswith(b'\x89PNG'):
        return 'png'
    if data.startswith(b'\xff\xd8'):
        return 'jpeg'
    if data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return 'gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'webp'
    if data.startswith(b'<svg'):
        return 'svg+xml'
    if data.startswith(b'\x00\x00\x01\x00') or data[:2] == b'\x00\x00':
        return 'x-icon'
    return 'png'


def _save_logo(company: str, data: bytes) -> Path:
    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(company)
    ext = _guess_image_ext(data)
    ext = 'png' if ext == 'x-icon' else ext
    path = PLACEHOLDER_DIR / f'{key}.{ext}'
    path.write_bytes(data)
    return path


def _load_logo_data(company: str) -> Optional[bytes]:
    key = _cache_key(company)
    if PLACEHOLDER_DIR.exists():
        for f in PLACEHOLDER_DIR.iterdir():
            if f.stem == key and f.is_file():
                return f.read_bytes()
    return None


def get_company_branding(company: str, force_refresh: bool = False) -> CompanyBranding:
    if company.strip().lower() in _SKIP_COMPANIES or len(company.strip()) < 3:
        return _make_placeholder(company)

    cached = _is_cached(company) if not force_refresh else None
    if cached and cached.get('status') == 'success':
        logo_data = _load_logo_data(company)
        if logo_data:
            return CompanyBranding(
                company=company,
                website_url=cached.get('website_url'),
                logo_data_uri=_image_to_data_uri(logo_data),
                logo_is_placeholder=False,
                brand_color=cached.get('brand_color', '#2563eb'),
                accent_color=cached.get('accent_color', '#1e40af'),
            )
    if cached and cached.get('status') == 'placeholder':
        return _make_placeholder(company)

    website = _find_website(company)
    brand_color = '#2563eb'
    accent_color = '#1e40af'
    logo_data = None

    if website:
        html_resp = _fetch_url(website)
        html = html_resp.text if html_resp else None
        bc = _extract_brand_color(website, html)
        if bc:
            brand_color = bc
            accent_color = bc

        favicon = _fetch_favicon(website)
        if favicon:
            logo_data = favicon
            saved_path = _save_logo(company, favicon)
            _write_cache(company, {
                'status': 'success',
                'website_url': website,
                'brand_color': brand_color,
                'accent_color': accent_color,
            })
            return CompanyBranding(
                company=company,
                website_url=website,
                logo_data_uri=_image_to_data_uri(favicon),
                logo_is_placeholder=False,
                brand_color=brand_color,
                accent_color=accent_color,
            )

    return _make_placeholder(company, brand_color)


def _make_placeholder(company: str, fallback_color: Optional[str] = None) -> CompanyBranding:
    b_color, a_color = _color_from_name(company) if not fallback_color else (fallback_color, fallback_color)
    hex_bg = _hsl_to_hex(*_parse_hsl(b_color)) if 'hsl' in b_color else b_color
    hex_accent = _hsl_to_hex(*_parse_hsl(a_color)) if 'hsl' in a_color else a_color

    avatar = _initials_avatar(company, hex_bg)
    _write_cache(company, {
        'status': 'placeholder',
        'website_url': None,
        'brand_color': hex_bg,
        'accent_color': hex_accent,
    })
    return CompanyBranding(
        company=company,
        website_url=None,
        logo_data_uri=avatar,
        logo_is_placeholder=True,
        brand_color=hex_bg,
        accent_color=hex_accent,
    )


def _parse_hsl(hsl_str: str) -> Tuple[int, int, int]:
    m = re.match(r'hsl\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)', hsl_str)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 0, 0, 0


def clear_cache(company: Optional[str] = None) -> None:
    if company:
        key = _cache_key(company)
        meta = _load_cache_meta()
        meta.pop(key, None)
        _save_cache_meta(meta)
        if PLACEHOLDER_DIR.exists():
            for f in PLACEHOLDER_DIR.iterdir():
                if f.stem == key:
                    f.unlink()
    else:
        if CACHE_META_FILE.exists():
            CACHE_META_FILE.unlink()
        if PLACEHOLDER_DIR.exists():
            for f in PLACEHOLDER_DIR.iterdir():
                f.unlink()
