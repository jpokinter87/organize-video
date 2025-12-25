"""Tests for path resolution functions."""

import pytest
from pathlib import Path

from organize.filesystem.paths import (
    in_range,
    inflate,
    find_matching_folder,
)


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
