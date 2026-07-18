import pytest
from poster.templates_marketplace import (
    get_template, list_templates, TemplatePreset, TEMPLATE_MAP,
)


class TestTemplatePresets:
    def test_all_templates_loaded(self):
        templates = list_templates()
        assert len(templates) == 10

    def test_expected_names(self):
        names = [t.name for t in list_templates()]
        expected = ['ghost', 'theme', 'corporate', 'minimal', 'medical',
                    'hiring', 'construction', 'tech', 'education', 'startup']
        for name in expected:
            assert name in names

    def test_get_template(self):
        t = get_template('tech')
        assert t.label == 'Tech'
        assert t.theme == 'cyberpunk'
        assert t.category == 'programming'

    def test_get_template_invalid(self):
        with pytest.raises(ValueError):
            get_template('nonexistent')

    def test_each_template_has_required_fields(self):
        for t in list_templates():
            assert isinstance(t, TemplatePreset)
            assert t.name
            assert t.label
            assert t.description
            assert t.theme
            assert t.category
            assert t.font
            assert t.accent
            assert t.bg
            assert t.text_color
            assert t.surface

    def test_template_map_consistency(self):
        assert len(TEMPLATE_MAP) == len(list_templates())
        for t in list_templates():
            assert t.name in TEMPLATE_MAP
            assert TEMPLATE_MAP[t.name] is t

    def test_ghost_template(self):
        t = get_template('ghost')
        assert t.theme == 'ghost'
        assert t.accent == '#8b5cf6'
        assert t.show_icons is True

    def test_minimal_template(self):
        t = get_template('minimal')
        assert t.theme == 'minimal'
        assert t.show_icons is False
        assert t.accent == '#000000'

    def test_medical_template(self):
        t = get_template('medical')
        assert t.category == 'medical'
        assert t.accent == '#0891b2'

    def test_startup_template(self):
        t = get_template('startup')
        assert t.theme == 'glass'
        assert t.category == 'creative'
        assert t.font == 'Outfit'
