"""Tests for text processing functions."""

import pytest
from organize.classification.text_processing import (
    normalize,
    remove_article,
    normalize_accents,
)


class TestNormalize:
    """Tests for the normalize() function."""

    def test_normalize_empty_string(self):
        """Empty string returns empty string."""
        assert normalize("") == ""

    def test_normalize_replaces_oe_ligature(self):
        """French oe ligature is replaced with 'o' (single character replacement)."""
        # Note: normalize() replaces œ with 'o', not 'oe'
        # For 'oe' expansion, use normalize_accents()
        assert normalize("cœur") == "cour"
        assert normalize("œuvre") == "ouvre"

    def test_normalize_replaces_ae_ligature(self):
        """French ae ligature is replaced with 'a'."""
        assert normalize("Cæsar") == "Casar"

    def test_normalize_removes_space_before_period(self):
        """Removes space before period."""
        assert normalize("test .txt") == "test.txt"

    def test_normalize_replaces_colon_with_comma(self):
        """Colon is replaced with comma-space."""
        assert normalize("Title: Subtitle") == "Title, Subtitle"

    def test_normalize_replaces_question_mark_with_ellipsis(self):
        """Question mark is replaced with ellipsis."""
        assert normalize("What?") == "What..."

    def test_normalize_replaces_slash_with_dash(self):
        """Slash is replaced with space-dash-space."""
        assert normalize("Action/Adventure") == "Action - Adventure"

    def test_normalize_removes_double_spaces(self):
        """Double spaces are reduced to single space."""
        assert normalize("test  double") == "test double"

    def test_normalize_removes_double_comma_space(self):
        """Double comma-space is reduced to single."""
        assert normalize("test ,  test") == "test, test"

    def test_normalize_strips_whitespace(self):
        """Leading and trailing whitespace is removed."""
        assert normalize("  test  ") == "test"

    def test_normalize_complex_case(self):
        """Complex string with multiple transformations."""
        # normalize() handles ligatures and special chars but NOT accents
        result = normalize("L'œuvre : du cinéma?")
        assert result == "L'ouvre, du cinéma..."


class TestRemoveArticle:
    """Tests for the remove_article() function."""

    def test_remove_article_empty_string(self):
        """Empty string returns empty string."""
        assert remove_article("") == ""

    def test_remove_article_french_le(self):
        """Removes French 'Le ' article (preserves case)."""
        assert remove_article("Le Film") == "Film"

    def test_remove_article_french_la(self):
        """Removes French 'La ' article (preserves case)."""
        assert remove_article("La Vie") == "Vie"

    def test_remove_article_french_les(self):
        """Removes French 'Les ' article."""
        result = remove_article("Les Misérables")
        assert result.startswith("Miser")

    def test_remove_article_french_l_apostrophe(self):
        """Removes French L' article (preserves case)."""
        assert remove_article("L'Amour") == "Amour"

    def test_remove_article_french_un(self):
        """Removes French 'Un ' article (preserves case)."""
        assert remove_article("Un Homme") == "Homme"

    def test_remove_article_french_une(self):
        """Removes French 'Une ' article (preserves case)."""
        assert remove_article("Une Femme") == "Femme"

    def test_remove_article_english_the(self):
        """Removes English 'The ' article (preserves case)."""
        assert remove_article("The Matrix") == "Matrix"

    def test_remove_article_english_a(self):
        """Removes English 'A ' article (preserves case)."""
        assert remove_article("A Film") == "Film"

    def test_remove_article_no_article(self):
        """Title without article is normalized but kept."""
        result = remove_article("Avatar")
        assert "avatar" in result.lower()

    def test_remove_article_normalizes_accents(self):
        """Result has accents normalized."""
        result = remove_article("Éléphant")
        assert result.lower() == "elephant"


class TestNormalizeAccents:
    """Tests for the normalize_accents() function."""

    def test_normalize_accents_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_accents("") == ""

    def test_normalize_accents_a_variants(self):
        """All 'a' accent variants are normalized."""
        assert normalize_accents("àáâãäå") == "aaaaaa"

    def test_normalize_accents_e_variants(self):
        """All 'e' accent variants are normalized."""
        assert normalize_accents("èéêë") == "eeee"

    def test_normalize_accents_i_variants(self):
        """All 'i' accent variants are normalized."""
        assert normalize_accents("ìíîï") == "iiii"

    def test_normalize_accents_o_variants(self):
        """All 'o' accent variants are normalized."""
        assert normalize_accents("òóôõö") == "ooooo"

    def test_normalize_accents_u_variants(self):
        """All 'u' accent variants are normalized."""
        assert normalize_accents("ùúûü") == "uuuu"

    def test_normalize_accents_cedilla(self):
        """French cedilla is normalized."""
        assert normalize_accents("ça") == "ca"
        assert normalize_accents("Ça") == "Ca"

    def test_normalize_accents_oe_ligature(self):
        """French oe ligature is expanded."""
        assert normalize_accents("cœur") == "coeur"

    def test_normalize_accents_ae_ligature(self):
        """French ae ligature is expanded."""
        assert normalize_accents("Cæsar") == "Caesar"

    def test_normalize_accents_uppercase(self):
        """Uppercase accented characters are normalized."""
        assert normalize_accents("ÉLÉPHANT") == "ELEPHANT"

    def test_normalize_accents_mixed_text(self):
        """Complex text with various accents."""
        result = normalize_accents("Café résumé naïve")
        assert result == "Cafe resume naive"

    def test_normalize_accents_preserves_non_accented(self):
        """Non-accented characters are preserved."""
        assert normalize_accents("Hello World 123") == "Hello World 123"
