"""Tests for display functions."""

import pytest
from unittest.mock import MagicMock, patch

from organize.ui.display import (
    generate_tree_structure,
    format_file_count,
    get_category_stats,
)


class TestGenerateTreeStructure:
    """Tests for generate_tree_structure function."""

    def test_empty_list_returns_empty_dict(self):
        """Empty video list returns empty dict."""
        result = generate_tree_structure([])
        assert result == {}

    def test_groups_videos_by_path(self):
        """Groups videos by relative path."""
        video1 = MagicMock()
        video1.formatted_filename = "Movie1.mkv"
        video1.sub_directory = "Films/Action"
        video1.is_film_anim.return_value = True
        video1.is_serie.return_value = False
        video1.genre = "Action & Aventure"

        video2 = MagicMock()
        video2.formatted_filename = "Movie2.mkv"
        video2.sub_directory = "Films/Action"
        video2.is_film_anim.return_value = True
        video2.is_serie.return_value = False
        video2.genre = "Action & Aventure"

        result = generate_tree_structure([video1, video2])

        assert "Films/Action" in result
        assert len(result["Films/Action"]) == 2

    def test_skips_videos_without_filename(self):
        """Skips videos without formatted_filename."""
        video = MagicMock()
        video.formatted_filename = ""

        result = generate_tree_structure([video])

        assert result == {}

    def test_handles_non_detected_films(self):
        """Handles films with Non détecté genre."""
        video = MagicMock()
        video.formatted_filename = "Unknown.mkv"
        video.sub_directory = None
        video.is_film_anim.return_value = True
        video.is_serie.return_value = False
        video.genre = "Non détecté"

        result = generate_tree_structure([video])

        assert "Films/non détectés" in result

    def test_handles_series(self):
        """Handles series videos."""
        video = MagicMock()
        video.formatted_filename = "Episode.mkv"
        video.sub_directory = None
        video.is_film_anim.return_value = False
        video.is_serie.return_value = True
        video.type_file = "Séries"

        result = generate_tree_structure([video])

        assert "Séries/Séries TV" in result


class TestFormatFileCount:
    """Tests for format_file_count function."""

    def test_singular(self):
        """Returns singular for count of 1."""
        result = format_file_count(1)
        assert result == "1 fichier"

    def test_plural(self):
        """Returns plural for count > 1."""
        result = format_file_count(5)
        assert result == "5 fichiers"

    def test_zero(self):
        """Returns singular for count of 0."""
        result = format_file_count(0)
        assert result == "0 fichier"


class TestGetCategoryStats:
    """Tests for get_category_stats function."""

    def test_counts_by_type(self):
        """Counts videos by type."""
        video1 = MagicMock()
        video1.type_file = "Films"
        video2 = MagicMock()
        video2.type_file = "Films"
        video3 = MagicMock()
        video3.type_file = "Séries"

        result = get_category_stats([video1, video2, video3])

        assert result["Films"] == 2
        assert result["Séries"] == 1

    def test_empty_list(self):
        """Returns empty dict for empty list."""
        result = get_category_stats([])
        assert result == {}

    def test_counts_by_genre(self):
        """Counts videos by genre when requested."""
        video1 = MagicMock()
        video1.genre = "Action & Aventure"
        video2 = MagicMock()
        video2.genre = "Drame"
        video3 = MagicMock()
        video3.genre = "Action & Aventure"

        result = get_category_stats([video1, video2, video3], by_genre=True)

        assert result["Action & Aventure"] == 2
        assert result["Drame"] == 1
