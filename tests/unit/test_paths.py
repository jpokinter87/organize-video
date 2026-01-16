"""Tests for path resolution functions."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.filesystem.paths import (
    in_range,
    inflate,
    find_matching_folder,
    find_directory_for_video,
    find_symlink_and_sub_dir,
    find_similar_file_in_folder,
    LRUCache,
    clear_caches,
)
from organize.models.video import Video


class TestInRange:
    """Tests for in_range function."""

    def test_value_in_range(self):
        """Returns True when value is in range."""
        assert in_range("b", "a", "c") is True

    def test_value_at_start(self):
        """Returns True when value equals start."""
        assert in_range("a", "a", "c") is True

    def test_value_at_end(self):
        """Returns True when value equals end."""
        assert in_range("c", "a", "c") is True

    def test_value_before_range(self):
        """Returns False when value is before range."""
        assert in_range("a", "b", "d") is False

    def test_value_after_range(self):
        """Returns False when value is after range."""
        assert in_range("e", "a", "c") is False

    def test_works_with_longer_strings(self):
        """Works with multi-character strings."""
        assert in_range("matrix", "m", "n") is True
        assert in_range("alien", "m", "n") is False


class TestInflate:
    """Tests for inflate function."""

    def test_pads_with_a_and_z(self):
        """Pads start with 'a' and end with 'z'."""
        start, end = inflate("a", "b", 3)
        assert start == "aaa"
        assert end == "bzz"

    def test_preserves_original_chars(self):
        """Preserves original characters."""
        start, end = inflate("ab", "cd", 4)
        assert start == "abaa"
        assert end == "cdzz"

    def test_same_length_no_change(self):
        """No padding needed when already at target length."""
        start, end = inflate("abc", "xyz", 3)
        assert start == "abc"
        assert end == "xyz"


class TestFindMatchingFolder:
    """Tests for find_matching_folder function."""

    def test_finds_exact_match(self, tmp_path):
        """Finds folder with exact prefix match."""
        (tmp_path / "m-n").mkdir()
        (tmp_path / "a-l").mkdir()

        result = find_matching_folder(tmp_path, "matrix")

        assert result == tmp_path / "m-n"

    def test_returns_root_when_no_match(self, tmp_path):
        """Returns root when no matching folder."""
        (tmp_path / "a-l").mkdir()

        result = find_matching_folder(tmp_path, "zebra")

        assert result == tmp_path

    def test_finds_nested_folder(self, tmp_path):
        """Finds matching folder in nested structure."""
        (tmp_path / "m-n").mkdir()
        (tmp_path / "m-n" / "ma-mz").mkdir()

        result = find_matching_folder(tmp_path, "matrix")

        assert result == tmp_path / "m-n" / "ma-mz"

    def test_handles_single_letter_folders(self, tmp_path):
        """Handles single letter range folders."""
        (tmp_path / "m").mkdir()

        result = find_matching_folder(tmp_path, "matrix")

        # Single letter folder "m" won't match range format
        assert result == tmp_path

    def test_ignores_non_range_folders(self, tmp_path):
        """Ignores folders that don't match range pattern."""
        (tmp_path / "random").mkdir()
        (tmp_path / "a-z").mkdir()

        result = find_matching_folder(tmp_path, "matrix")

        assert result == tmp_path / "a-z"

    def test_case_insensitive(self, tmp_path):
        """Matching is case insensitive."""
        (tmp_path / "M-N").mkdir()

        result = find_matching_folder(tmp_path, "matrix")

        assert result == tmp_path / "M-N"


class TestLRUCache:
    """Tests for LRUCache class."""

    def test_get_returns_none_for_missing(self):
        """Returns None for missing keys."""
        cache = LRUCache()
        assert cache.get(("a", "b")) is None

    def test_set_and_get(self):
        """Can set and retrieve values."""
        cache = LRUCache()
        path = Path("/test/path")
        cache.set(("key1", "key2"), path)
        assert cache.get(("key1", "key2")) == path

    def test_clear_removes_all(self):
        """Clear removes all entries."""
        cache = LRUCache()
        cache.set(("k1", "v1"), Path("/p1"))
        cache.set(("k2", "v2"), Path("/p2"))
        cache.clear()
        assert cache.get(("k1", "v1")) is None
        assert cache.get(("k2", "v2")) is None


class TestFindDirectoryForVideo:
    """Tests for find_directory_for_video function."""

    def setup_method(self):
        """Clear caches before each test."""
        clear_caches()

    def test_returns_non_detectes_for_undetected_film(self, tmp_path):
        """Returns 'non détectés' folder for undetected films."""
        video = Video()
        video.complete_path_original = Path("/test/Films/video.mkv")
        video.title_fr = ""
        video.type_file = "Films"

        result = find_directory_for_video(video, tmp_path)
        assert result == tmp_path / "non détectés"

    def test_finds_range_folder(self, tmp_path):
        """Finds matching range folder for video."""
        (tmp_path / "m-n").mkdir()
        video = Video()
        video.complete_path_original = Path("/test/Films/matrix.mkv")
        video.title_fr = "Matrix"
        video.name_without_article = "matrix"  # Required for range matching
        video.type_file = "Films"

        result = find_directory_for_video(video, tmp_path)
        assert result == tmp_path / "m-n"

    def test_uses_cache_on_repeated_calls(self, tmp_path):
        """Uses cached result on repeated calls."""
        (tmp_path / "a-z").mkdir()
        video = Video()
        video.complete_path_original = Path("/test/Films/alien.mkv")
        video.title_fr = "Alien"
        video.type_file = "Films"

        result1 = find_directory_for_video(video, tmp_path)
        result2 = find_directory_for_video(video, tmp_path)
        assert result1 == result2

    def test_series_returns_hash_folder_when_no_match(self, tmp_path):
        """Returns '#' folder for series when no match found."""
        video = Video()
        video.complete_path_original = Path("/test/Séries/show.mkv")
        video.title_fr = "Show"
        video.type_file = "Séries"

        result = find_directory_for_video(video, tmp_path)
        assert result == tmp_path / "#"


class TestFindSymlinkAndSubDir:
    """Tests for find_symlink_and_sub_dir function."""

    def setup_method(self):
        """Clear caches before each test."""
        clear_caches()

    def test_film_uses_genre_path(self, tmp_path):
        """Film uses Films/genre path."""
        genre_path = tmp_path / "Films" / "Action"
        genre_path.mkdir(parents=True)

        video = Video()
        video.complete_path_original = Path("/test/Films/movie.mkv")
        video.title_fr = "Test Movie"
        video.type_file = "Films"
        video.genre = "Action"

        complete_dir, sub_dir = find_symlink_and_sub_dir(video, tmp_path)

        assert "Films" in str(complete_dir)
        assert video.complete_dir_symlinks == complete_dir
        assert video.sub_directory == sub_dir

    def test_series_uses_extended_sub_path(self, tmp_path):
        """Series uses extended_sub path."""
        series_path = tmp_path / "Séries" / "Séries TV"
        series_path.mkdir(parents=True)

        video = Video()
        video.complete_path_original = Path("/test/Séries/show.mkv")
        video.title_fr = "Test Show"
        video.type_file = "Séries"
        video.extended_sub = Path("Séries/Séries TV")

        complete_dir, sub_dir = find_symlink_and_sub_dir(video, tmp_path)

        assert video.complete_dir_symlinks is not None


class TestFindSimilarFileInFolder:
    """Tests for find_similar_file_in_folder function."""

    def test_returns_none_for_nonexistent_folder(self, tmp_path):
        """Returns None when folder doesn't exist."""
        video = Video()
        video.title_fr = "Test"
        video.date_film = 2020

        result = find_similar_file_in_folder(
            video, tmp_path / "nonexistent"
        )
        assert result is None

    def test_returns_none_when_no_title(self, tmp_path):
        """Returns None when video has no title."""
        video = Video()
        video.title_fr = ""
        video.date_film = 2020

        result = find_similar_file_in_folder(video, tmp_path)
        assert result is None

    def test_finds_similar_file(self, tmp_path):
        """Finds file with similar title and matching year."""
        video = Video()
        video.title_fr = "Test Movie"
        video.date_film = 2020

        # Create a file with similar name
        (tmp_path / "Test Movie (2020).mkv").touch()

        result = find_similar_file_in_folder(video, tmp_path)
        assert result is not None
        assert "Test Movie" in result.name

    def test_ignores_file_with_wrong_year(self, tmp_path):
        """Ignores files with year outside tolerance."""
        video = Video()
        video.title_fr = "Test Movie"
        video.date_film = 2020

        # Create a file with different year
        (tmp_path / "Test Movie (2015).mkv").touch()

        result = find_similar_file_in_folder(video, tmp_path)
        assert result is None

    def test_respects_year_tolerance(self, tmp_path):
        """Finds files within year tolerance."""
        video = Video()
        video.title_fr = "Test Movie"
        video.date_film = 2020

        # Create a file 1 year off (within default tolerance)
        (tmp_path / "Test Movie (2019).mkv").touch()

        result = find_similar_file_in_folder(
            video, tmp_path, year_tolerance=1
        )
        assert result is not None


class TestClearCaches:
    """Tests for clear_caches function."""

    def test_clears_all_caches(self, tmp_path):
        """Clears both subfolder and series caches."""
        from organize.filesystem.paths import subfolder_cache, series_subfolder_cache

        # Populate caches
        subfolder_cache.set(("k1", "v1"), Path("/p1"))
        series_subfolder_cache.set(("k2", "v2"), Path("/p2"))

        clear_caches()

        assert subfolder_cache.get(("k1", "v1")) is None
        assert series_subfolder_cache.get(("k2", "v2")) is None
