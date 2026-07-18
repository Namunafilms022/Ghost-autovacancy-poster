import sys
sys.path.insert(0, '/root/project')

import pytest
from validator.models import FieldValidation, ConfidenceLevel
from validator.confidence import calculate_overall, FIELD_WEIGHTS


def _field(name: str, confidence: float) -> FieldValidation:
    return FieldValidation(
        name=name,
        value='test',
        confidence=confidence,
        level=ConfidenceLevel.from_score(confidence),
    )


class TestCalculateOverall:
    def test_all_high_confidence(self):
        fields = {name: _field(name, 0.95) for name in FIELD_WEIGHTS}
        result = calculate_overall(fields, threshold=0.7)
        assert result.overall_confidence >= 0.9
        assert not result.rejected
        assert result.overall_level == ConfidenceLevel.EXCELLENT

    def test_all_low_confidence(self):
        fields = {name: _field(name, 0.1) for name in FIELD_WEIGHTS}
        result = calculate_overall(fields, threshold=0.7)
        assert result.overall_confidence < 0.3
        assert result.rejected
        assert result.rejection_reason is not None

    def test_mixed_confidence(self):
        fields = {
            'company': _field('company', 0.95),
            'position': _field('position', 0.9),
            'salary': _field('salary', 0.3),
            'location': _field('location', 0.8),
            'requirements': _field('requirements', 0.0),
            'benefits': _field('benefits', 0.0),
            'deadline': _field('deadline', 0.0),
            'contact': _field('contact', 0.0),
            'email': _field('email', 0.0),
            'phone': _field('phone', 0.0),
            'website': _field('website', 0.0),
        }
        result = calculate_overall(fields, threshold=0.7)
        assert result.rejected
        assert 'low_confidence_fields' in result.to_dict()

    def test_empty_fields(self):
        result = calculate_overall({}, threshold=0.7)
        assert result.overall_confidence == 0.0
        assert result.rejected

    def test_custom_threshold(self):
        fields = {name: _field(name, 0.6) for name in FIELD_WEIGHTS}
        result = calculate_overall(fields, threshold=0.5)
        assert not result.rejected

        result2 = calculate_overall(fields, threshold=0.7)
        assert result2.rejected

    def test_to_dict(self):
        fields = {'company': _field('company', 0.95)}
        result = calculate_overall(fields, threshold=0.7)
        d = result.to_dict()
        assert 'overall_confidence' in d
        assert 'fields' in d
        assert d['rejected'] is False
