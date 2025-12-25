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


class TestDisplayTree:
    """Tests for display_tree function."""

    def test_display_tree_empty(self):
        """Displays empty tree without error."""
        from organize.ui.display import display_tree

        with patch("organize.ui.display.console") as mock_console:
            display_tree({})
            mock_console.print.assert_called_once()

    def test_display_tree_with_files(self):
        """Displays tree with files."""
        from organize.ui.display import display_tree

        tree_structure = {
            "Films/Action": ["Movie1.mkv", "Movie2.mkv"],
            "Séries/Drama": ["Episode.mkv"],
        }

        with patch("organize.ui.display.console") as mock_console:
            display_tree(tree_structure)
            mock_console.print.assert_called_once()

    def test_display_tree_truncates_long_lists(self):
        """Truncates file lists that exceed max."""
        from organize.ui.display import display_tree

        tree_structure = {
            "Films/Action": [f"Movie{i}.mkv" for i in range(10)],
        }

        with patch("organize.ui.display.console") as mock_console:
            display_tree(tree_structure, max_files_per_folder=3)
            mock_console.print.assert_called_once()

    def test_display_tree_non_detected_folder(self):
        """Handles non détectés folder styling."""
        from organize.ui.display import display_tree

        tree_structure = {
            "Films/non détectés": ["Unknown.mkv"],
        }

        with patch("organize.ui.display.console") as mock_console:
            display_tree(tree_structure)
            mock_console.print.assert_called_once()


class TestDisplayStatistics:
    """Tests for display_statistics function."""

    def test_display_statistics_empty(self):
        """Warns when no videos provided."""
        from organize.ui.display import display_statistics

        with patch("organize.ui.display.console") as mock_console:
            display_statistics([])
            mock_console.print_warning.assert_called_once()

    def test_display_statistics_with_videos(self):
        """Displays statistics for videos."""
        from organize.ui.display import display_statistics

        video1 = MagicMock()
        video1.type_file = "Films"
        video1.genre = "Action"

        video2 = MagicMock()
        video2.type_file = "Séries"
        video2.genre = "Drama"

        with patch("organize.ui.display.console") as mock_console:
            mock_console.create_table.return_value = MagicMock()
            display_statistics([video1, video2])
            assert mock_console.rule.called
            assert mock_console.create_table.call_count == 2


class TestDisplaySummary:
    """Tests for display_summary function."""

    def test_display_summary_normal_mode(self):
        """Displays summary in normal mode."""
        from organize.ui.display import display_summary

        with patch("organize.ui.display.console") as mock_console:
            display_summary(10, 8, 2, dry_run=False)
            mock_console.rule.assert_called_once()
            assert mock_console.print.call_count >= 2

    def test_display_summary_dry_run(self):
        """Displays summary in dry run mode."""
        from organize.ui.display import display_summary

        with patch("organize.ui.display.console") as mock_console:
            display_summary(10, 10, 0, dry_run=True)
            call_args = mock_console.rule.call_args[0][0]
            assert "SIMULATION" in call_args

    def test_display_summary_no_failures(self):
        """Skips failure line when no failures."""
        from organize.ui.display import display_summary

        with patch("organize.ui.display.console") as mock_console:
            display_summary(10, 10, 0)
            # Should have 2 print calls (total, successful) but not failed
            assert mock_console.print.call_count == 2


class TestGenerateTreeStructureFilmWithGenre:
    """Additional tests for generate_tree_structure."""

    def test_handles_film_with_genre(self):
        """Handles films with detected genre."""
        video = MagicMock()
        video.formatted_filename = "Action.mkv"
        video.sub_directory = None
        video.is_film_anim.return_value = True
        video.is_serie.return_value = False
        video.genre = "Action & Aventure"

        result = generate_tree_structure([video])

        assert "Films/Action & Aventure" in result

    def test_handles_other_type(self):
        """Handles non-film, non-series types."""
        video = MagicMock()
        video.formatted_filename = "Doc.mkv"
        video.sub_directory = None
        video.is_film_anim.return_value = False
        video.is_serie.return_value = False
        video.type_file = "Docs"

        result = generate_tree_structure([video])

        assert "Docs" in result
