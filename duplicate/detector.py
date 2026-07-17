from __future__ import annotations

from difflib import SequenceMatcher
from typing import List, Optional

from parser.models import JobDetails
from database.models import Vacancy
from database.session import get_session


WEIGHT_TITLE = 0.40
WEIGHT_COMPANY = 0.30
WEIGHT_LOCATION = 0.20
WEIGHT_SALARY = 0.10


class DuplicateResult:
    def __init__(self, is_duplicate: bool, similarity_score: float = 0.0,
                 matched_vacancy_id: Optional[int] = None,
                 field_scores: Optional[dict] = None):
        self.is_duplicate = is_duplicate
        self.similarity_score = similarity_score
        self.matched_vacancy_id = matched_vacancy_id
        self.field_scores = field_scores or {}

    def __repr__(self) -> str:
        return (
            f"<DuplicateResult(is_duplicate={self.is_duplicate}, "
            f"similarity={self.similarity_score:.2f})>"
        )


def _text_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    norm = lambda s: ' '.join(s.strip().lower().split())
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


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


def _calculate_similarity(
    details: JobDetails, vacancy: Vacancy
) -> tuple[float, dict]:
    title_score = _text_similarity(details.title, vacancy.title)
    company_score = _text_similarity(details.company, vacancy.company)
    location_score = _text_similarity(details.location, vacancy.location)
    salary_score = _salary_overlap(
        details.salary_min, details.salary_max,
        vacancy.salary_min, vacancy.salary_max,
    )

    total = (
        title_score * WEIGHT_TITLE
        + company_score * WEIGHT_COMPANY
        + location_score * WEIGHT_LOCATION
        + salary_score * WEIGHT_SALARY
    )

    field_scores = {
        'title': round(title_score, 4),
        'company': round(company_score, 4),
        'location': round(location_score, 4),
        'salary': round(salary_score, 4),
        'weighted_title': round(title_score * WEIGHT_TITLE, 4),
        'weighted_company': round(company_score * WEIGHT_COMPANY, 4),
        'weighted_location': round(location_score * WEIGHT_LOCATION, 4),
        'weighted_salary': round(salary_score * WEIGHT_SALARY, 4),
    }

    return round(total, 4), field_scores


class DuplicateDetector:
    def __init__(self, similarity_threshold: float = 0.85):
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
            best_field_scores: dict = {}

            for existing in candidates:
                score, field_scores = _calculate_similarity(job_details, existing)
                if score > best_score:
                    best_score = score
                    best_match_id = existing.id
                    best_field_scores = field_scores

            is_dup = best_score >= self.similarity_threshold

            if is_dup and vacancy_id is not None:
                self._mark_duplicate(vacancy_id, best_match_id, session)

            return DuplicateResult(
                is_duplicate=is_dup,
                similarity_score=best_score,
                matched_vacancy_id=best_match_id,
                field_scores=best_field_scores,
            )
        finally:
            session.close()

    def detect_batch(
        self, job_list: List[JobDetails], vacancy_ids: Optional[List[Optional[int]]] = None
    ) -> List[DuplicateResult]:
        results = []
        for i, details in enumerate(job_list):
            vid = vacancy_ids[i] if vacancy_ids and i < len(vacancy_ids) else None
            results.append(self.detect(details, vacancy_id=vid))
        return results

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
