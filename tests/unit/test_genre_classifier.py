"""Tests for genre classification functions."""

import pytest
from unittest.mock import MagicMock

from organize.classification.genre_classifier import (
    suggest_genre_mapping,
    classify_movie,
    classify_animation,
    filter_supported_genres,
)


class TestSuggestGenreMapping:
    """Tests for suggest_genre_mapping function."""

    def test_maps_romance_to_drame(self):
        """Romance maps to Drame."""
        result = suggest_genre_mapping(["Romance"])
        assert result == "Drame"

    def test_maps_crime_to_policier(self):
        """Crime maps to Policier."""
        result = suggest_genre_mapping(["Crime"])
        assert result == "Policier"

    def test_maps_mystery_to_thriller(self):
        """Mystery maps to Thriller."""
        result = suggest_genre_mapping(["Mystery"])
        assert result == "Thriller"

    def test_maps_adventure_to_action(self):
        """Adventure maps to Action & Aventure."""
        result = suggest_genre_mapping(["Adventure"])
        assert result == "Action & Aventure"

    def test_maps_family_to_enfants(self):
        """Family maps to Films pour enfants."""
        result = suggest_genre_mapping(["Family"])
        assert result == "Films pour enfants"

    def test_maps_biography_to_drame(self):
        """Biography maps to Drame."""
        result = suggest_genre_mapping(["Biography"])
        assert result == "Drame"

    def test_maps_sport_to_drame(self):
        """Sport maps to Drame."""
        result = suggest_genre_mapping(["Sport"])
        assert result == "Drame"

    def test_maps_musical_to_drame(self):
        """Musical maps to Drame."""
        result = suggest_genre_mapping(["Musical"])
        assert result == "Drame"

    def test_maps_telefilm_to_drame(self):
        """Téléfilm maps to Drame."""
        result = suggest_genre_mapping(["Téléfilm"])
        assert result == "Drame"

    def test_partial_match_works(self):
        """Partial matching works for genre variations."""
        result = suggest_genre_mapping(["Romantic Comedy"])
        assert result == "Drame"

    def test_first_mappable_genre_wins(self):
        """First mappable genre in list is used."""
        result = suggest_genre_mapping(["Unknown", "Crime", "Mystery"])
        assert result == "Policier"  # Crime maps first

    def test_narrative_indicator_fallback(self):
        """Narrative indicators fall back to Drame."""
        result = suggest_genre_mapping(["Drama Special"])
        assert result == "Drame"

    def test_no_match_returns_empty(self):
        """Returns empty string when no match found."""
        result = suggest_genre_mapping(["Unknown Genre XYZ"])
        assert result == ""

    def test_empty_list_returns_empty(self):
        """Empty list returns empty string."""
        result = suggest_genre_mapping([])
        assert result == ""

    def test_case_insensitive(self):
        """Matching is case insensitive."""
        result = suggest_genre_mapping(["ROMANCE"])
        assert result == "Drame"


class TestFilterSupportedGenres:
    """Tests for filter_supported_genres function."""

    def test_filters_supported_genres(self):
        """Returns only supported genres."""
        genres = ["Action & Aventure", "Romance", "Comédie"]
        valid, unsupported = filter_supported_genres(genres)
        assert "Action & Aventure" in valid
        assert "Comédie" in valid
        assert "Romance" in unsupported

    def test_all_supported(self):
        """All supported genres returns empty unsupported list."""
        genres = ["Drame", "Thriller"]
        valid, unsupported = filter_supported_genres(genres)
        assert valid == ["Drame", "Thriller"]
        assert unsupported == []

    def test_none_supported(self):
        """None supported returns all in unsupported."""
        genres = ["Romance", "Musical"]
        valid, unsupported = filter_supported_genres(genres)
        assert valid == []
        assert "Romance" in unsupported
        assert "Musical" in unsupported

    def test_empty_list(self):
        """Empty list returns empty lists."""
        valid, unsupported = filter_supported_genres([])
        assert valid == []
        assert unsupported == []


class TestClassifyMovie:
    """Tests for classify_movie function."""

    @pytest.fixture
    def mock_video(self):
        """Create a mock Video object."""
        video = MagicMock()
        video.list_genres = []
        video.genre = ""
        return video

    def test_no_genres_returns_non_detecte(self, mock_video):
        """Empty genre list sets genre to Non détecté."""
        mock_video.list_genres = []
        result = classify_movie(mock_video)
        assert result.genre == "Non détecté"

    def test_already_non_detecte(self, mock_video):
        """Already Non détecté stays Non détecté."""
        mock_video.list_genres = ["Non détecté"]
        result = classify_movie(mock_video)
        assert result.genre == "Non détecté"

    def test_animation_delegates_to_classify_animation(self, mock_video):
        """Animation genre triggers classify_animation."""
        mock_video.list_genres = ["Animation"]
        result = classify_movie(mock_video)
        # classify_animation sets specific animation subgenre
        assert "Animation" in result.genre

    def test_drame_comedie_becomes_comedie_dramatique(self, mock_video):
        """Drame + Comédie becomes Comédie dramatique."""
        mock_video.list_genres = ["Drame", "Comédie"]
        result = classify_movie(mock_video)
        assert result.genre == "Comédie dramatique"

    def test_priority_genre_selected(self, mock_video):
        """Priority genre is selected when present."""
        mock_video.list_genres = ["Drame", "Western"]
        result = classify_movie(mock_video)
        assert result.genre == "Western"

    def test_sf_priority(self, mock_video):
        """SF is a priority genre."""
        mock_video.list_genres = ["Drame", "SF"]
        result = classify_movie(mock_video)
        assert result.genre == "SF"

    def test_historique_priority(self, mock_video):
        """Historique is a priority genre."""
        mock_video.list_genres = ["Action & Aventure", "Historique"]
        result = classify_movie(mock_video)
        assert result.genre == "Historique"

    def test_first_genre_fallback(self, mock_video):
        """First genre is used when no priority match."""
        mock_video.list_genres = ["Drame", "Thriller"]
        result = classify_movie(mock_video)
        # When no priority genre, first genre is used
        assert result.genre in ["Drame", "Thriller"]


class TestClassifyAnimation:
    """Tests for classify_animation function."""

    @pytest.fixture
    def mock_video(self):
        """Create a mock Video object."""
        video = MagicMock()
        video.list_genres = ["Animation"]
        video.genre = ""
        return video

    def test_single_animation_becomes_adultes(self, mock_video):
        """Single Animation genre becomes Animation/Adultes."""
        mock_video.list_genres = ["Animation"]
        result = classify_animation(mock_video)
        assert result.genre == "Animation/Adultes"

    def test_animation_with_enfants(self, mock_video):
        """Animation + Films pour enfants becomes Animation/Animation Enfant."""
        mock_video.list_genres = ["Animation", "Films pour enfants"]
        result = classify_animation(mock_video)
        assert result.genre == "Animation/Animation Enfant"

    def test_animation_with_other_genre(self, mock_video):
        """Animation + other genre defaults to Animation/Animation Enfant."""
        mock_video.list_genres = ["Animation", "Comédie"]
        result = classify_animation(mock_video)
        assert result.genre == "Animation/Animation Enfant"

    def test_updates_list_genres(self, mock_video):
        """Updates list_genres to reflect new genre."""
        mock_video.list_genres = ["Animation", "Comédie"]
        result = classify_animation(mock_video)
        assert "Animation/Animation Enfant" in result.list_genres
