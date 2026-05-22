"""Tests for omics.viz.style."""

from omics.viz.style import StyleManager, THEMES


class TestStyleManager:
    def test_themes_loaded(self):
        assert "nature" in THEMES
        assert "cell" in THEMES
        assert "science" in THEMES

    def test_nature_theme_has_attrs(self):
        theme = THEMES["nature"]
        assert theme.font_family is not None
        assert theme.font_size > 0
        assert theme.dpi > 0

    def test_set_global_does_not_raise(self):
        StyleManager.set_global("nature")
