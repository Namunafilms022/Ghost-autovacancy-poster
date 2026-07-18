from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

PLATFORMS = ['facebook', 'instagram', 'linkedin', 'telegram', 'twitter']


@dataclass
class CaptionSet:
    caption: str
    hashtags: str
    call_to_action: str
    short_version: str
    long_version: str

    def full_text(self) -> str:
        parts = [self.caption]
        if self.hashtags:
            parts.append('')
            parts.append(self.hashtags)
        if self.call_to_action:
            parts.append('')
            parts.append(self.call_to_action)
        return '\n'.join(parts)


@dataclass
class CaptionResult:
    vacancy_id: int
    title: str
    company: str
    platforms: Dict[str, CaptionSet] = field(default_factory=dict)

    def for_platform(self, platform: str) -> Optional[CaptionSet]:
        return self.platforms.get(platform)


_hashtag_sets: Dict[str, List[str]] = {
    'general': [
        '#hiring', '#job', '#career', '#jobs', '#recruiting',
        '#nowhiring', '#jobsearch', '#employment', '#work',
    ],
    'tech': [
        '#techjobs', '#softwareengineer', '#developer', '#coding',
        '#programming', '#techcareer', '#ITjobs',
    ],
    'medical': [
        '#healthcare', '#medicaljobs', '#nurse', '#doctor',
        '#healthcareers', '#medjobs',
    ],
    'engineering': [
        '#engineering', '#engineer', '#engineeringjobs',
        '#mechanicalengineering', '#civilengineering',
    ],
    'finance': [
        '#finance', '#financejobs', '#accounting', '#business',
        '#corporate', '#management',
    ],
    'creative': [
        '#creativejobs', '#designer', '#creative', '#marketing',
        '#design', '#uidesign',
    ],
    'construction': [
        '#construction', '#constructionjobs', '#trades',
        '#skilledtrades', '#bluecollar',
    ],
    'education': [
        '#education', '#teaching', '#teacher', '#educator',
        '#educationjobs', '#edjobs',
    ],
    'instagram_generic': [
        '#hiring', '#jobsearch', '#careergoals', '#dreamjob',
        '#jobopportunity', '#vacancy', '#applynow',
    ],
}

_cta_templates: Dict[str, List[str]] = {
    'facebook': [
        'Apply now and join our team!',
        'Interested? Send your CV today.',
        'Tag someone who would be perfect for this role!',
        'Drop your application in the comments below.',
    ],
    'instagram': [
        'Tap the link in bio to apply! 💫',
        'Tag a friend who needs to see this! 👇',
        'Swipe up to apply! ✨',
        'Comment "interested" for more details! 💬',
    ],
    'linkedin': [
        'Apply now or share with your network.',
        'Interested candidates can apply through the link below.',
        'I look forward to reviewing your application.',
        'Please share this opportunity with qualified professionals.',
    ],
    'telegram': [
        'Apply now — link below 👇',
        'Send your CV to the contact above.',
        'Hurry — positions fill quickly!',
        'Contact us today to apply.',
    ],
    'twitter': [
        'Apply now!',
        'DM for details.',
        'Check the link to apply.',
        'Retweet to help spread the word!',
    ],
}


def _select_hashtag_set(title: str = '', description: str = '') -> str:
    text = f'{title} {description}'.lower()
    if any(kw in text for kw in ['developer', 'software', 'engineer', 'programmer',
                                   'coding', 'devops', 'data', 'python', 'java',
                                   'react', 'javascript', 'full stack', 'it ']):
        return 'tech'
    if any(kw in text for kw in ['nurse', 'doctor', 'medical', 'health', 'clinical',
                                   'pharma', 'hospital', 'patient', 'care']):
        return 'medical'
    if any(kw in text for kw in ['mechanical', 'electrical', 'civil', 'structural',
                                   'architect', 'chemical', 'manufacturing']):
        return 'engineering'
    if any(kw in text for kw in ['finance', 'accounting', 'audit', 'legal',
                                   'business', 'analyst', 'corporate', 'hr']):
        return 'finance'
    if any(kw in text for kw in ['designer', 'creative', 'artist', 'graphic',
                                   'marketing', 'content', 'writer', 'social media']):
        return 'creative'
    if any(kw in text for kw in ['construction', 'electrician', 'plumber',
                                   'welder', 'carpenter', 'warehouse']):
        return 'construction'
    if any(kw in text for kw in ['teacher', 'professor', 'instructor',
                                   'educator', 'school', 'university']):
        return 'education'
    return 'general'


def _format_salary(min_sal: Optional[float], max_sal: Optional[float],
                   prefix: str = 'Rs.') -> str:
    def fmt(v):
        if v is None:
            return None
        if v >= 10000000:
            return f'{prefix} {v / 10000000:.1f}Cr'
        if v >= 100000:
            return f'{prefix} {v / 100000:.1f}L'
        if v >= 1000:
            return f'{prefix} {v:,.0f}'
        return f'{prefix} {v:.0f}'
    if min_sal and max_sal:
        return f'{fmt(min_sal)} - {fmt(max_sal)}'
    if min_sal:
        return f'{fmt(min_sal)}+'
    if max_sal:
        return f'Up to {fmt(max_sal)}'
    return ''


def _build_hashtags(platform: str, category: str, count: int = 5) -> str:
    tag_set = list(_hashtag_sets.get('general', []))
    cat_set = list(_hashtag_sets.get(category, []))
    insta_set = list(_hashtag_sets.get('instagram_generic', []))
    if platform == 'instagram':
        tag_set = insta_set + cat_set + ['#jobalert', '#hiringnow']
    elif platform in ('telegram', 'twitter'):
        tag_set = tag_set[:2] + cat_set[:2]
    else:
        tag_set = tag_set[:3] + cat_set[:3]
    return ' '.join(tag_set[:count])


def _pick_cta(platform: str) -> str:
    ctas = _cta_templates.get(platform, _cta_templates['facebook'])
    return random.choice(ctas)


def _if(val: str, prefix: str = '', suffix: str = '') -> str:
    return f'{prefix}{val}{suffix}' if val else ''


def _bullets(items: List[str], limit: int = 5, label: str = '') -> str:
    lines = [f'• {r}' for r in items[:limit]]
    if not lines:
        return ''
    result = '\n'.join(lines)
    if label:
        result = f'{label}\n{result}'
    return result


def generate_captions(
    title: str,
    company: str,
    location: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    job_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    benefits: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> CaptionResult:
    salary_str = _format_salary(salary_min, salary_max)
    loc_str = location or ''
    jt_str = (job_type or '').replace('_', ' ').title() if job_type else ''
    exp_str = (experience_level or '').replace('_', ' ').title() if experience_level else ''

    meta_parts = [p for p in [loc_str, jt_str, exp_str, salary_str] if p]
    meta_line = ' | '.join(meta_parts) if meta_parts else ''

    req_lines = requirements or []
    ben_lines = benefits or []
    req_bullets = _bullets(req_lines, label='Requirements:')
    ben_bullets = _bullets(ben_lines, label='Benefits:')

    category = _select_hashtag_set(title, description)

    platforms: Dict[str, CaptionSet] = {}

    for platform in PLATFORMS:
        hashtags = _build_hashtags(platform, category)
        cta = _pick_cta(platform)

        if platform == 'facebook':
            caption = f"We're hiring a {title} at {company}!" + _if(meta_line, ' — ')
            long_version = (
                f"We're hiring a {title} at {company}!\n\n"
                + _if(loc_str, '📍 ', '\n')
                + _if(salary_str, '💰 ', '\n')
                + _if(jt_str, '💼 ', '\n')
                + _if(exp_str, '📊 ', '\n')
                + _if(req_bullets, '', '\n')
                + _if(ben_bullets, '', '\n')
                + "Join our team and take the next step in your career!"
            )
            short_version = f"Hiring {title} at {company}!" + _if(meta_line, ' ')

        elif platform == 'instagram':
            caption = (
                "🚀 WE'RE HIRING! 🚀\n\n"
                f"{title}\n📍 {company}"
                + _if(loc_str, ' · ')
            )
            long_version = (
                "🚀 WE'RE HIRING! 🚀\n\n"
                f"{title}\n📍 {company}"
                + _if(loc_str, ' · ')
                + '\n\n' + _if(meta_line, '', '')
                + _if(meta_line, meta_line + '\n\n')
                + _if(req_bullets, '', '\n')
                + _if(ben_bullets, '', '\n')
                + "Don't miss this opportunity to join an amazing team! 🙌"
            )
            short_version = f"🚀 WE'RE HIRING!\n{title}\n{company}\n{meta_line}"

        elif platform == 'linkedin':
            caption = (
                f"I'm excited to announce that we are looking for a "
                f"{title} to join {company}!\n\n"
                + _if(meta_line, '', '\n\n')
                + _if(meta_line, meta_line + '\n\n')
                + _if(req_bullets, '', '\n')
                + _if(ben_bullets, '', '\n')
                + "\nIf you or someone in your network is interested, "
                "please reach out. Let's grow together!"
            )
            long_version = (
                f"I'm thrilled to share that {company} is hiring a "
                f"{title}!\n\nAbout the role:\n"
                + _if(meta_line, '', '\n\n')
                + _if(meta_line, meta_line + '\n\n')
                + _if(req_bullets, '', '\n')
                + _if(ben_bullets, '', '\n')
                + f"\nAt {company}, we value growth, collaboration, and excellence. "
                "This is an excellent opportunity for someone looking to make "
                "a meaningful impact.\n\n"
                "I'd appreciate it if you could share this with your network "
                "or tag someone who might be a great fit."
            )
            short_version = f"We're hiring a {title} at {company}! {meta_line}"

        elif platform == 'telegram':
            caption = (
                "📢 JOB ALERT\n\n"
                f"{title}\n🏢 {company}\n"
                + _if(loc_str, '📍 ', '\n')
                + _if(salary_str, '💰 ', '\n')
                + _if(jt_str, '💼 ', '\n')
                + _if(exp_str, '📊 ', '\n')
            )
            long_version = (
                "📢 JOB ALERT\n\n"
                f"Position: {title}\nCompany: {company}\n"
                + _if(loc_str, 'Location: ', '\n')
                + _if(salary_str, 'Salary: ', '\n')
                + _if(jt_str, 'Type: ', '\n')
                + _if(exp_str, 'Experience: ', '\n\n')
                + _if(req_bullets, '', '\n')
                + _if(ben_bullets, '', '\n')
                + "\nContact us for more details!"
            )
            short_version = (
                f"📢 JOB: {title} at {company}"
                + _if(loc_str, ' — ')
            )

        elif platform == 'twitter':
            caption = (
                f"We're hiring! {title} at {company}"
                + _if(loc_str, ' — ')
                + _if(salary_str, ' — ')
            )
            if len(caption) > 270:
                caption = caption[:267] + '...'
            long_version = (
                f"We're hiring a {title} at {company}!\n"
                + _if(meta_line, '', '\n')
                + _if(meta_line, meta_line + '\n')
                + _if(', '.join(req_lines[:3]), 'Req: ', '\n')
                + _if(', '.join(ben_lines[:3]), 'Benefits: ')
            )
            short_version = (
                f"Hiring: {title} @ {company}"
                + _if(loc_str[:20], ' · ')
            )

        platforms[platform] = CaptionSet(
            caption=caption,
            hashtags=hashtags,
            call_to_action=cta,
            short_version=short_version,
            long_version=long_version,
        )

    return CaptionResult(
        vacancy_id=0,
        title=title,
        company=company,
        platforms=platforms,
    )


def get_platform_caption(result: CaptionResult, platform: str) -> Optional[CaptionSet]:
    return result.platforms.get(platform)
