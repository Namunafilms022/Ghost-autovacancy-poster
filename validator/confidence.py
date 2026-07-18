from __future__ import annotations

from typing import Dict, Optional, List

from .models import FieldValidation, ExtractionResult, ConfidenceLevel

FIELD_WEIGHTS = {
    'company': 1.5,
    'position': 1.5,
    'salary': 1.0,
    'location': 1.0,
    'requirements': 0.8,
    'benefits': 0.5,
    'deadline': 0.5,
    'contact': 0.7,
    'email': 0.7,
    'phone': 0.5,
    'website': 0.3,
}

DEFAULT_THRESHOLD = 0.7


def calculate_overall(fields: Dict[str, FieldValidation],
                      threshold: float = DEFAULT_THRESHOLD) -> ExtractionResult:
    total_weight = 0.0
    weighted_sum = 0.0

    for name, fv in fields.items():
        weight = FIELD_WEIGHTS.get(name, 1.0)
        total_weight += weight
        weighted_sum += fv.confidence * weight

    overall = weighted_sum / total_weight if total_weight > 0 else 0.0
    level = ConfidenceLevel.from_score(overall)
    rejected = overall < threshold

    result = ExtractionResult(
        vacancy_id=0,
        fields=fields,
        overall_confidence=overall,
        overall_level=level,
        threshold=threshold,
        rejected=rejected,
    )

    if rejected:
        missing = result.missing_fields
        low_conf = result.low_confidence_fields
        parts = []
        if missing:
            parts.append(f'missing: {", ".join(missing)}')
        if low_conf:
            parts.append(f'low confidence: {", ".join(low_conf)}')
        result.rejection_reason = (
            f'Overall confidence {overall:.2f} < threshold {threshold}. '
            + ('Issues: ' + '; '.join(parts) if parts else '')
        )

    return result
