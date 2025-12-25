"""Tests for symlink operations."""

import pytest
from pathlib import Path

from organize.filesystem.symlinks import (
    create_symlink,
    verify_symlinks,
    is_valid_symlink,
)


class TestCreateSymlink:
    """Tests for create_symlink function."""

    def test_creates_symlink(self, tmp_path):
        """Creates symlink pointing to source."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "link.mkv"

        create_symlink(source, dest)

        assert dest.is_symlink()
        assert dest.resolve() == source

    def test_dry_run_does_not_create(self, tmp_path):
        """Dry run does not create actual symlink."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "link.mkv"

        create_symlink(source, dest, dry_run=True)

        assert not dest.exists()

    def test_replaces_existing_symlink(self, tmp_path):
        """Replaces existing symlink."""
        source1 = tmp_path / "source1.mkv"
        source1.touch()
        source2 = tmp_path / "source2.mkv"
        source2.touch()
        dest = tmp_path / "link.mkv"

        create_symlink(source1, dest)
        create_symlink(source2, dest)

        assert dest.resolve() == source2

    def test_replaces_existing_file(self, tmp_path):
        """Replaces existing regular file with symlink."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "dest.mkv"
        dest.touch()

        create_symlink(source, dest)

        assert dest.is_symlink()
        assert dest.resolve() == source

    def test_resolves_source_symlink(self, tmp_path):
        """Resolves source if it's a symlink."""
        original = tmp_path / "original.mkv"
        original.touch()
        source = tmp_path / "source_link.mkv"
        source.symlink_to(original)
        dest = tmp_path / "dest.mkv"

        create_symlink(source, dest)

        assert dest.is_symlink()
        # The link should point to the resolved original
        assert dest.resolve() == original


class TestVerifySymlinks:
    """Tests for verify_symlinks function."""

    def test_no_broken_links(self, tmp_path):
        """No action when all links are valid."""
        source = tmp_path / "source.mkv"
        source.touch()
        link = tmp_path / "link.mkv"
        link.symlink_to(source)

        # Should not raise
        verify_symlinks(tmp_path)

        assert link.exists()

    def test_removes_broken_links(self, tmp_path):
        """Removes broken symlinks."""
        link = tmp_path / "broken_link.mkv"
        link.symlink_to(tmp_path / "nonexistent.mkv")

        verify_symlinks(tmp_path)

        assert not link.exists()

    def test_handles_nested_directories(self, tmp_path):
        """Checks symlinks in nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        link = subdir / "broken.mkv"
        link.symlink_to(tmp_path / "nonexistent.mkv")

        verify_symlinks(tmp_path)

        assert not link.exists()


class TestIsValidSymlink:
    """Tests for is_valid_symlink function."""

    def test_valid_symlink(self, tmp_path):
        """Returns True for valid symlink."""
        source = tmp_path / "source.mkv"
        source.touch()
        link = tmp_path / "link.mkv"
        link.symlink_to(source)

        assert is_valid_symlink(link) is True

    def test_broken_symlink(self, tmp_path):
        """Returns False for broken symlink."""
        link = tmp_path / "broken.mkv"
        link.symlink_to(tmp_path / "nonexistent.mkv")

        assert is_valid_symlink(link) is False

    def test_not_a_symlink(self, tmp_path):
        """Returns False for regular file."""
        regular = tmp_path / "regular.mkv"
        regular.touch()

        assert is_valid_symlink(regular) is False

    def test_nonexistent_path(self, tmp_path):
        """Returns False for nonexistent path."""
        assert is_valid_symlink(tmp_path / "nonexistent") is False
