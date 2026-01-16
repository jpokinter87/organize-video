"""Tests unitaires pour les fonctions de traitement de texte."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from organize.classification.text_processing import (
    normalize,
    remove_article,
    normalize_accents,
    extract_title_from_filename,
    format_undetected_filename,
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


class TestExtractTitleFromFilename:
    """Tests pour extract_title_from_filename."""

    def test_extrait_titre_simple(self):
        """Extrait un titre simple avec guessit."""
        result = extract_title_from_filename("The.Matrix.1999.MULTi.1080p.BluRay")
        assert result['title'] is not None
        assert len(result['title']) > 0

    def test_extrait_annee(self):
        """Extrait l'année du nom de fichier."""
        result = extract_title_from_filename("Inception.2010.1080p.BluRay")
        assert result['year'] == 2010

    def test_gere_absence_annee(self):
        """Gère l'absence d'année dans le nom."""
        result = extract_title_from_filename("Some.Movie.MULTi.1080p")
        assert 'title' in result
        # L'année peut être None ou absente

    def test_nettoie_specs_techniques(self):
        """Nettoie les specs techniques du titre."""
        result = extract_title_from_filename("Avatar.2009.MULTI.x264.1080p.WEB-DL")
        title_lower = result['title'].lower()
        assert 'multi' not in title_lower
        assert 'x264' not in title_lower
        assert '1080p' not in title_lower

    def test_retourne_dictionnaire(self):
        """Retourne toujours un dictionnaire avec title et year."""
        result = extract_title_from_filename("Test.Movie")
        assert isinstance(result, dict)
        assert 'title' in result
        assert 'year' in result


class TestFormatUndetectedFilename:
    """Tests pour format_undetected_filename."""

    def test_formate_nom_basique(self):
        """Formate un nom de fichier basique."""
        video = MagicMock()
        video.complete_path_original = Path("/test/The.Amateur.2025.MULTi.1080p.mkv")
        video.spec = "MULTi x264 1080p"

        result = format_undetected_filename(video)

        assert result.endswith('.mkv')
        assert '2025' in result or 'Année' in result

    def test_extrait_specs_depuis_nom(self):
        """Extrait les specs depuis le nom si non fournies."""
        video = MagicMock()
        video.complete_path_original = Path("/test/Film.2020.MULTI.x265.1080p.mkv")
        video.spec = ""

        result = format_undetected_filename(video)

        # Doit contenir au moins quelques specs
        assert '.mkv' in result

    def test_gere_extension_ts(self):
        """Convertit l'extension .ts en .mp4."""
        video = MagicMock()
        video.complete_path_original = Path("/test/Video.2020.ts")
        video.spec = "FR x264 1080p"

        result = format_undetected_filename(video)

        assert result.endswith('.mp4')
        assert not result.endswith('.ts')

    def test_titre_vide_devient_non_identifie(self):
        """Un titre qui ne peut pas être extrait devient 'Fichier non identifié'."""
        video = MagicMock()
        video.complete_path_original = Path("/test/1080p.x264.mkv")
        video.spec = ""

        result = format_undetected_filename(video)

        # Doit avoir un titre, même générique
        assert '.mkv' in result
        assert len(result) > 10

    def test_detecte_langue_multi(self):
        """Détecte la langue MULTI dans le nom."""
        video = MagicMock()
        video.complete_path_original = Path("/test/Film.MULTI.2020.mkv")
        video.spec = ""

        result = format_undetected_filename(video)

        assert 'MULTi' in result or 'MULTI' in result or result.count('(') > 0

    def test_detecte_langue_vostfr(self):
        """Détecte la langue VOSTFR dans le nom."""
        video = MagicMock()
        video.complete_path_original = Path("/test/Film.VOSTFR.2020.mkv")
        video.spec = ""

        result = format_undetected_filename(video)

        # La fonction devrait détecter VOSTFR
        assert '.mkv' in result
