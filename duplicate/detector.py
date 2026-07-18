from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from parser.models import JobDetails
from database.models import Vacancy
from database.session import get_session

WEIGHT_TITLE = 0.25
WEIGHT_COMPANY = 0.25
WEIGHT_LOCATION = 0.12
WEIGHT_SALARY = 0.12
WEIGHT_DESCRIPTION = 0.10
WEIGHT_REQUIREMENTS = 0.10
WEIGHT_BENEFITS = 0.06

_WEIGHT_MAP = {
    'title': WEIGHT_TITLE,
    'company': WEIGHT_COMPANY,
    'location': WEIGHT_LOCATION,
    'salary': WEIGHT_SALARY,
    'description': WEIGHT_DESCRIPTION,
    'requirements': WEIGHT_REQUIREMENTS,
    'benefits': WEIGHT_BENEFITS,
}

_THRESHOLD_DEFAULT = 0.75


def _normalize(text: Optional[str]) -> str:
    if not text:
        return ''
    return ' '.join(text.strip().lower().split())


def _text_similarity(a: Optional[str], b: Optional[str]) -> float:
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _list_similarity(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    na = set(_normalize(x) for x in a if x)
    nb = set(_normalize(x) for x in b if x)
    if not na or not nb:
        return 0.0
    return len(na & nb) / len(na | nb)


def _salary_overlap(
    min_a: Optional[float], max_a: Optional[float],
    min_b: Optional[float], max_b: Optional[float],
) -> float:
    if min_a is None or max_a is None or min_b is None or max_b is None:
        return 0.0
    if max_a < min_a or max_b < min_b:
        return 0.0
    overlap_start = max(min_a, min_b)
    overlap_end = min(max_a, max_b)
    if overlap_start >= overlap_end:
        return 0.0
    union_start = min(min_a, min_b)
    union_end = max(max_a, max_b)
    if union_end <= union_start:
        return 0.0
    return (overlap_end - overlap_start) / (union_end - union_start)


def _extract_section_items(text: str, headers: List[str]) -> List[str]:
    if not text:
        return []
    lower = text.lower()
    for h in headers:
        idx = lower.find(h.lower().rstrip('?'))
        if idx == -1:
            continue
        remainder = text[idx + len(h):].lstrip(' *:–\n\t')
        items = []
        for line in remainder.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^[-*•]\s+', stripped):
                items.append(re.sub(r'^[-*•]\s+', '', stripped))
                continue
            next_heading = False
            for other_h in _EXTRACT_HEADERS_ALL:
                if other_h.lower() != h.lower() and stripped.lower().startswith(other_h.lower().rstrip('?')):
                    next_heading = True
                    break
            if next_heading:
                break
            if items and not re.match(r'^[-*•]\s+', stripped):
                break
        return items
    return []


_EXTRACT_HEADERS_REQ = [
    'requirements', 'requirement', 'qualifications', 'qualification',
    'what we need', 'you have', 'skills', 'skills required',
    'must have', 'key skills', 'experience required',
]
_EXTRACT_HEADERS_BEN = [
    'benefits', 'benefit', 'what we offer', 'perks', 'perks',
    'we offer', 'you get', 'compensation', 'extras',
]
_EXTRACT_HEADERS_ALL = list(set(_EXTRACT_HEADERS_REQ + _EXTRACT_HEADERS_BEN))


def _get_req_benefits(raw: Optional[str]) -> Tuple[List[str], List[str]]:
    if not raw:
        return [], []
    reqs = _extract_section_items(raw, _EXTRACT_HEADERS_REQ)
    ben = _extract_section_items(raw, _EXTRACT_HEADERS_BEN)
    return reqs, ben


def _generate_reason(title_score: float, company_score: float,
                     location_score: float, salary_score: float,
                     description_score: float, req_score: float,
                     ben_score: float, total: float) -> str:
    parts = []
    if title_score >= 0.8 and company_score >= 0.8:
        parts.append('Same company and position')
    elif title_score >= 0.8:
        parts.append('Matching job title')
    elif company_score >= 0.8:
        parts.append('Same company')

    if description_score >= 0.7:
        parts.append('Similar description')
    if req_score >= 0.6:
        parts.append('Overlapping requirements')
    if ben_score >= 0.6:
        parts.append('Same benefits')
    if salary_score >= 0.6:
        parts.append('Salary overlap')
    if location_score >= 0.8:
        parts.append('Same location')

    if not parts:
        best_pairs = [
            ('title', title_score), ('company', company_score),
            ('location', location_score), ('salary', salary_score),
            ('description', description_score),
            ('requirements', req_score), ('benefits', ben_score),
        ]
        best_name, best_val = max(best_pairs, key=lambda x: x[1])
        parts.append(f'{best_name.title()} similarity ({best_val:.0%})')

    return '; '.join(parts) + f' (score: {total:.2f})'


def _field_comparable(a_val, b_val, field: str) -> bool:
    if field == 'salary':
        return (a_val[0] is not None and a_val[1] is not None
                and b_val[0] is not None and b_val[1] is not None)
    if field in ('requirements', 'benefits'):
        return bool(a_val) or bool(b_val)
    return bool(a_val) and bool(b_val)


def _calculate_similarity(
    details: JobDetails, vacancy: Vacancy
) -> Tuple[float, Dict[str, float]]:
    title_score = _text_similarity(details.title, vacancy.title)
    company_score = _text_similarity(details.company, vacancy.company)
    location_score = _text_similarity(details.location, vacancy.location)
    salary_score = _salary_overlap(
        details.salary_min, details.salary_max,
        vacancy.salary_min, vacancy.salary_max,
    )

    desc_text = vacancy.description or vacancy.raw_message or ''
    description_score = _text_similarity(details.description, desc_text)

    req_a = details.requirements or []
    req_b, ben_b = _get_req_benefits(vacancy.raw_message)
    req_score = _list_similarity(req_a, req_b)

    ben_a = details.benefits or []
    ben_score = _list_similarity(ben_a, ben_b)

    raw_scores = {
        'title': title_score,
        'company': company_score,
        'location': location_score,
        'salary': salary_score,
        'description': description_score,
        'requirements': req_score,
        'benefits': ben_score,
    }

    active_weight = 0.0
    weighted_sum = 0.0
    for field, weight in _WEIGHT_MAP.items():
        score = raw_scores[field]
        if field == 'salary':
            comparable = _field_comparable(
                (details.salary_min, details.salary_max),
                (vacancy.salary_min, vacancy.salary_max), field)
        elif field in ('requirements', 'benefits'):
            val_a = getattr(details, field, [])
            val_b = req_b if field == 'requirements' else ben_b
            comparable = bool(val_a) or bool(val_b)
        else:
            val_a = getattr(details, field, None)
            val_b = getattr(vacancy, field, None)
            comparable = bool(val_a) and bool(val_b)

        if comparable:
            active_weight += weight
            weighted_sum += score * weight

    total = round(weighted_sum / active_weight, 4) if active_weight > 0 else 0.0

    field_scores = {
        'title': round(title_score, 4),
        'company': round(company_score, 4),
        'location': round(location_score, 4),
        'salary': round(salary_score, 4),
        'description': round(description_score, 4),
        'requirements': round(req_score, 4),
        'benefits': round(ben_score, 4),
    }
    for field, weight in _WEIGHT_MAP.items():
        field_scores[f'weighted_{field}'] = round(raw_scores[field] * weight, 4)

    return total, field_scores


def _build_merge_suggestion(
    details: JobDetails, vacancy: Vacancy,
    field_scores: Dict[str, float],
) -> Dict[str, dict]:
    suggestions = {}

    if not details.salary_min and vacancy.salary_min:
        suggestions['salary'] = {
            'source': {'min': vacancy.salary_min, 'max': vacancy.salary_max},
            'reason': 'Salary available from existing vacancy',
            'action': 'merge_from_existing',
        }
    elif details.salary_min and not vacancy.salary_min:
        suggestions['salary'] = {
            'source': {'min': details.salary_min, 'max': details.salary_max},
            'reason': 'Salary available from new details',
            'action': 'merge_from_new',
        }

    req_b, ben_b = _get_req_benefits(vacancy.raw_message)
    if not details.requirements and req_b:
        suggestions['requirements'] = {
            'source': req_b,
            'reason': 'Requirements available from existing vacancy',
            'action': 'merge_from_existing',
        }
    elif details.requirements and not req_b:
        suggestions['requirements'] = {
            'source': details.requirements,
            'reason': 'Requirements available from new details',
            'action': 'merge_from_new',
        }

    if not details.benefits and ben_b:
        suggestions['benefits'] = {
            'source': ben_b,
            'reason': 'Benefits available from existing vacancy',
            'action': 'merge_from_existing',
        }
    elif details.benefits and not ben_b:
        suggestions['benefits'] = {
            'source': details.benefits,
            'reason': 'Benefits available from new details',
            'action': 'merge_from_new',
        }

    if not details.location and vacancy.location:
        suggestions['location'] = {
            'source': vacancy.location,
            'reason': 'Location available from existing vacancy',
            'action': 'merge_from_existing',
        }

    return suggestions


class DuplicateResult:
    def __init__(self, is_duplicate: bool, similarity_score: float = 0.0,
                 matched_vacancy_id: Optional[int] = None,
                 field_scores: Optional[Dict[str, float]] = None,
                 reason: Optional[str] = None,
                 merge_suggestion: Optional[Dict[str, dict]] = None):
        self.is_duplicate = is_duplicate
        self.similarity_score = similarity_score
        self.matched_vacancy_id = matched_vacancy_id
        self.field_scores = field_scores or {}
        self.reason = reason
        self.merge_suggestion = merge_suggestion

    def __repr__(self) -> str:
        return (
            f'<DuplicateResult(is_duplicate={self.is_duplicate}, '
            f'score={self.similarity_score:.2f}, '
            f'matched_id={self.matched_vacancy_id})>'
        )


class DuplicateDetector:
    def __init__(self, similarity_threshold: float = _THRESHOLD_DEFAULT):
        self.similarity_threshold = similarity_threshold

    def detect(
        self, job_details: JobDetails, vacancy_id: Optional[int] = None
    ) -> DuplicateResult:
        session = get_session()
        try:
            candidates = session.query(Vacancy).filter(
                Vacancy.is_duplicate == False,  # noqa: E712
                Vacancy.processed == True,       # noqa: E712
            )
            if vacancy_id is not None:
                candidates = candidates.filter(Vacancy.id != vacancy_id)

            best_score = 0.0
            best_match_id = None
            best_field_scores: Dict[str, float] = {}
            best_vacancy = None

            for existing in candidates:
                score, field_scores = _calculate_similarity(job_details, existing)
                if score > best_score:
                    best_score = score
                    best_match_id = existing.id
                    best_field_scores = field_scores
                    best_vacancy = existing

            is_dup = best_score >= self.similarity_threshold

            if is_dup and vacancy_id is not None:
                self._mark_duplicate(vacancy_id, best_match_id, session)

            reason = None
            merge_suggestion = None
            if best_score > 0:
                reason = _generate_reason(
                    best_field_scores.get('title', 0),
                    best_field_scores.get('company', 0),
                    best_field_scores.get('location', 0),
                    best_field_scores.get('salary', 0),
                    best_field_scores.get('description', 0),
                    best_field_scores.get('requirements', 0),
                    best_field_scores.get('benefits', 0),
                    best_score,
                )
                if best_vacancy and is_dup:
                    merge_suggestion = _build_merge_suggestion(
                        job_details, best_vacancy, best_field_scores,
                    )

            return DuplicateResult(
                is_duplicate=is_dup,
                similarity_score=best_score,
                matched_vacancy_id=best_match_id,
                field_scores=best_field_scores,
                reason=reason,
                merge_suggestion=merge_suggestion,
            )
        finally:
            session.close()

    def detect_batch(
        self, job_list: List[JobDetails],
        vacancy_ids: Optional[List[Optional[int]]] = None
    ) -> List[DuplicateResult]:
        results = []
        for i, details in enumerate(job_list):
            vid = vacancy_ids[i] if vacancy_ids and i < len(vacancy_ids) else None
            results.append(self.detect(details, vacancy_id=vid))
        return results

    def suggest_merge(
        self, source_id: int, target_id: int
    ) -> Dict[str, dict]:
        session = get_session()
        try:
            source = session.query(Vacancy).filter(Vacancy.id == source_id).first()
            target = session.query(Vacancy).filter(Vacancy.id == target_id).first()
            if not source or not target:
                return {}

            sd = JobDetails(
                title=source.title, company=source.company,
                location=source.location, description=source.description,
                salary_min=source.salary_min, salary_max=source.salary_max,
            )
            _, field_scores = _calculate_similarity(sd, target)
            return _build_merge_suggestion(sd, target, field_scores)
        finally:
            session.close()

    def _mark_duplicate(self, vacancy_id: int, original_id: int,
                        session=None) -> None:
        own_session = session is None
        if own_session:
            session = get_session()
        try:
            vacancy = session.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
            if vacancy:
                vacancy.is_duplicate = True
                vacancy.duplicate_of = original_id
                session.commit()
        except Exception:
            if own_session:
                session.rollback()
            raise
        finally:
            if own_session:
                session.close()
