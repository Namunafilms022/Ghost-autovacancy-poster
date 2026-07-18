from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List


class ConfidenceLevel(str, Enum):
    EXCELLENT = 'excellent'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    MISSING = 'missing'

    @classmethod
    def from_score(cls, score: float) -> ConfidenceLevel:
        if score >= 0.9:
            return cls.EXCELLENT
        if score >= 0.7:
            return cls.GOOD
        if score >= 0.5:
            return cls.FAIR
        if score > 0:
            return cls.POOR
        return cls.MISSING


@dataclass
class FieldValidation:
    name: str
    value: Optional[str]
    confidence: float
    level: ConfidenceLevel
    issues: List[str] = field(default_factory=list)
    details: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.confidence >= 0.5

    @property
    def is_missing(self) -> bool:
        return self.level == ConfidenceLevel.MISSING


@dataclass
class ExtractionResult:
    vacancy_id: int
    fields: Dict[str, FieldValidation]
    overall_confidence: float
    overall_level: ConfidenceLevel
    threshold: float
    rejected: bool = False
    rejection_reason: Optional[str] = None

    @property
    def missing_fields(self) -> List[str]:
        return [name for name, f in self.fields.items() if f.is_missing]

    @property
    def low_confidence_fields(self) -> List[str]:
        return [name for name, f in self.fields.items() if not f.passed]

    def to_dict(self) -> dict:
        return {
            'vacancy_id': self.vacancy_id,
            'overall_confidence': round(self.overall_confidence, 2),
            'overall_level': self.overall_level.value,
            'threshold': self.threshold,
            'rejected': self.rejected,
            'rejection_reason': self.rejection_reason,
            'fields': {
                name: {
                    'value': fv.value,
                    'confidence': round(fv.confidence, 2),
                    'level': fv.level.value,
                    'issues': fv.issues,
                    'details': fv.details,
                }
                for name, fv in self.fields.items()
            },
            'missing_fields': self.missing_fields,
            'low_confidence_fields': self.low_confidence_fields,
        }
