"""Tests for series episode handling."""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.pipeline.series_handler import (
    format_season_folder,
    find_series_folder,
    build_episode_filename,
    should_create_season_folder,
)


class TestFormatSeasonFolder:
    """Tests for format_season_folder function."""

    def test_formats_single_digit(self):
        """Formats single digit season with leading zero."""
        result = format_season_folder(1)
        assert result == "Saison 01"

    def test_formats_double_digit(self):
        """Formats double digit season."""
        result = format_season_folder(10)
        assert result == "Saison 10"

    def test_zero_returns_empty(self):
        """Zero season returns empty string."""
        result = format_season_folder(0)
        assert result == ""


class TestFindSeriesFolder:
    """Tests for find_series_folder function."""

    def test_finds_folder_with_year(self):
        """Finds folder ending with (YYYY)."""
        path = Path("/work/Séries/Breaking Bad (2008)/Saison 01/episode.mkv")
        result = find_series_folder(path)
        assert result.name == "Breaking Bad (2008)"

    def test_returns_parent_when_no_year_found(self):
        """Returns immediate parent when no year pattern found."""
        path = Path("/work/Séries/episode.mkv")
        result = find_series_folder(path)
        assert result == path.parent

    def test_handles_nested_structure(self):
        """Handles deeply nested paths."""
        path = Path("/storage/nas/work/Séries/Show Name (2020)/extras/episode.mkv")
        result = find_series_folder(path)
        assert result.name == "Show Name (2020)"


class TestBuildEpisodeFilename:
    """Tests for build_episode_filename function."""

    def test_builds_complete_filename(self):
        """Builds filename with all components."""
        result = build_episode_filename(
            series_title="Breaking Bad",
            year=2008,
            sequence="- S01E05 -",
            episode_title="Gray Matter",
            spec="MULTi HEVC 1080p",
            extension=".mkv"
        )

        assert "Breaking Bad" in result
        assert "2008" in result
        assert "S01E05" in result
        assert "Gray Matter" in result
        assert "MULTi" in result
        assert ".mkv" in result

    def test_handles_no_episode_title(self):
        """Handles missing episode title."""
        result = build_episode_filename(
            series_title="Show",
            year=2020,
            sequence="- S01E01 -",
            episode_title="",
            spec="FR",
            extension=".mkv"
        )

        assert "Show" in result
        assert "2020" in result
        assert ".mkv" in result

    def test_handles_special_characters(self):
        """Handles special characters in title."""
        result = build_episode_filename(
            series_title="Grey's Anatomy",
            year=2005,
            sequence="- S01E01 -",
            episode_title="Pilot",
            spec="FR",
            extension=".mkv"
        )

        assert "Grey's Anatomy" in result


class TestShouldCreateSeasonFolder:
    """Tests for should_create_season_folder function."""

    def test_returns_true_when_not_in_season(self):
        """Returns True when not already in season folder."""
        current_path = Path("/work/Séries/Show (2020)/episode.mkv")
        result = should_create_season_folder(current_path, 1)
        assert result is True

    def test_returns_false_when_in_season(self):
        """Returns False when already in correct season folder."""
        current_path = Path("/work/Séries/Show (2020)/Saison 01/episode.mkv")
        result = should_create_season_folder(current_path, 1)
        assert result is False

    def test_returns_false_for_zero_season(self):
        """Returns False for season 0."""
        current_path = Path("/work/Séries/Show (2020)/episode.mkv")
        result = should_create_season_folder(current_path, 0)
        assert result is False

    def test_returns_true_for_different_season(self):
        """Returns True when in different season folder."""
        current_path = Path("/work/Séries/Show (2020)/Saison 01/episode.mkv")
        result = should_create_season_folder(current_path, 2)
        assert result is True
