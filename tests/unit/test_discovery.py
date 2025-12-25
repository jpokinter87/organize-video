"""Tests for file discovery functions."""

import pytest
from pathlib import Path

from organize.filesystem.discovery import (
    get_available_categories,
    get_files,
    count_videos,
)


class TestGetAvailableCategories:
    """Tests for get_available_categories function."""

    def test_finds_existing_categories(self, tmp_path):
        """Finds existing category directories."""
        # Create category directories
        (tmp_path / "Films").mkdir()
        (tmp_path / "Séries").mkdir()

        result = get_available_categories(tmp_path)

        assert len(result) == 2
        assert tmp_path / "Films" in result
        assert tmp_path / "Séries" in result

    def test_ignores_non_category_dirs(self, tmp_path):
        """Ignores directories not in CATEGORIES."""
        (tmp_path / "Films").mkdir()
        (tmp_path / "RandomFolder").mkdir()

        result = get_available_categories(tmp_path)

        assert len(result) == 1
        assert tmp_path / "Films" in result

    def test_returns_empty_for_no_categories(self, tmp_path):
        """Returns empty list when no categories exist."""
        (tmp_path / "RandomFolder").mkdir()

        result = get_available_categories(tmp_path)

        assert result == []

    def test_finds_animation_category(self, tmp_path):
        """Finds Animation category."""
        (tmp_path / "Animation").mkdir()

        result = get_available_categories(tmp_path)

        assert tmp_path / "Animation" in result

    def test_finds_docs_categories(self, tmp_path):
        """Finds Docs and Docs#1 categories."""
        (tmp_path / "Docs").mkdir()
        (tmp_path / "Docs#1").mkdir()

        result = get_available_categories(tmp_path)

        assert tmp_path / "Docs" in result
        assert tmp_path / "Docs#1" in result


class TestGetFiles:
    """Tests for get_files function."""

    def test_yields_video_files(self, tmp_path):
        """Yields video files from categories."""
        films_dir = tmp_path / "Films"
        films_dir.mkdir()
        (films_dir / "movie.mkv").touch()
        (films_dir / "movie.avi").touch()

        result = list(get_files(tmp_path))

        assert len(result) == 2

    def test_yields_files_recursively(self, tmp_path):
        """Yields files from subdirectories."""
        films_dir = tmp_path / "Films" / "SubFolder"
        films_dir.mkdir(parents=True)
        (films_dir / "movie.mkv").touch()

        result = list(get_files(tmp_path))

        assert len(result) == 1

    def test_ignores_non_video_files(self, tmp_path):
        """Ignores files with unsupported extensions."""
        films_dir = tmp_path / "Films"
        films_dir.mkdir()
        (films_dir / "movie.mkv").touch()
        (films_dir / "readme.txt").touch()
        (films_dir / "image.jpg").touch()

        result = list(get_files(tmp_path))

        # Only mkv should be returned (txt is in ALL_EXTENSIONS but jpg is not)
        assert any(f.name == "movie.mkv" for f in result)

    def test_returns_empty_for_no_categories(self, tmp_path):
        """Returns empty when no categories exist."""
        (tmp_path / "RandomFolder").mkdir()

        result = list(get_files(tmp_path))

        assert result == []

    def test_yields_from_multiple_categories(self, tmp_path):
        """Yields files from multiple categories."""
        (tmp_path / "Films").mkdir()
        (tmp_path / "Films" / "movie.mkv").touch()
        (tmp_path / "Séries").mkdir()
        (tmp_path / "Séries" / "episode.mp4").touch()

        result = list(get_files(tmp_path))

        assert len(result) == 2


class TestCountVideos:
    """Tests for count_videos function."""

    def test_counts_video_files(self, tmp_path):
        """Counts video files correctly."""
        films_dir = tmp_path / "Films"
        films_dir.mkdir()
        (films_dir / "movie1.mkv").touch()
        (films_dir / "movie2.avi").touch()

        result = count_videos(tmp_path)

        assert result == 2

    def test_counts_across_categories(self, tmp_path):
        """Counts files across multiple categories."""
        (tmp_path / "Films").mkdir()
        (tmp_path / "Films" / "movie.mkv").touch()
        (tmp_path / "Séries").mkdir()
        (tmp_path / "Séries" / "ep1.mp4").touch()
        (tmp_path / "Séries" / "ep2.mp4").touch()

        result = count_videos(tmp_path)

        assert result == 3

    def test_returns_zero_for_no_categories(self, tmp_path):
        """Returns 0 when no categories exist."""
        result = count_videos(tmp_path)

        assert result == 0

    def test_counts_recursively(self, tmp_path):
        """Counts files in subdirectories."""
        deep_dir = tmp_path / "Films" / "Genre" / "SubGenre"
        deep_dir.mkdir(parents=True)
        (deep_dir / "movie.mkv").touch()

        result = count_videos(tmp_path)

        assert result == 1
