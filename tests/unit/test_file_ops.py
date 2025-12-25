"""Tests for file operations."""

import pytest
import shutil
from pathlib import Path

from organize.filesystem.file_ops import (
    move_file,
    copy_tree,
    ensure_unique_destination,
    setup_working_directories,
)


class TestMoveFile:
    """Tests for move_file function."""

    def test_moves_file(self, tmp_path):
        """Moves file to destination."""
        source = tmp_path / "source.mkv"
        source.write_text("video content")
        dest = tmp_path / "subdir" / "dest.mkv"

        move_file(source, dest)

        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "video content"

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if needed."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "a" / "b" / "c" / "dest.mkv"

        move_file(source, dest)

        assert dest.exists()

    def test_dry_run_does_not_move(self, tmp_path):
        """Dry run does not move file."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "dest.mkv"

        move_file(source, dest, dry_run=True)

        assert source.exists()
        assert not dest.exists()

    def test_handles_same_size_duplicate(self, tmp_path):
        """Removes source when destination has same size."""
        source = tmp_path / "source.mkv"
        source.write_text("content")
        dest = tmp_path / "dest.mkv"
        dest.write_text("content")

        move_file(source, dest)

        assert not source.exists()
        assert dest.exists()

    def test_returns_false_for_missing_source(self, tmp_path):
        """Returns False when source doesn't exist."""
        source = tmp_path / "nonexistent.mkv"
        dest = tmp_path / "dest.mkv"

        result = move_file(source, dest)

        assert result is False


class TestCopyTree:
    """Tests for copy_tree function."""

    def test_copies_directory_tree(self, tmp_path):
        """Copies entire directory tree."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").touch()
        (source / "subdir").mkdir()
        (source / "subdir" / "file2.txt").touch()
        dest = tmp_path / "dest"

        copy_tree(source, dest)

        assert dest.exists()
        assert (dest / "file1.txt").exists()
        assert (dest / "subdir" / "file2.txt").exists()

    def test_dry_run_does_not_copy(self, tmp_path):
        """Dry run does not copy."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").touch()
        dest = tmp_path / "dest"

        copy_tree(source, dest, dry_run=True)

        assert not dest.exists()

    def test_skips_empty_source(self, tmp_path):
        """Skips copy when source is empty."""
        source = tmp_path / "source"
        source.mkdir()
        dest = tmp_path / "dest"

        copy_tree(source, dest)

        assert not dest.exists()

    def test_replaces_existing_destination(self, tmp_path):
        """Replaces existing destination directory."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "new.txt").touch()
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "old.txt").touch()

        copy_tree(source, dest)

        assert (dest / "new.txt").exists()
        assert not (dest / "old.txt").exists()


class TestEnsureUniqueDestination:
    """Tests for ensure_unique_destination function."""

    def test_returns_same_path_if_not_exists(self, tmp_path):
        """Returns same path if it doesn't exist."""
        dest = tmp_path / "file.mkv"

        result = ensure_unique_destination(dest)

        assert result == dest

    def test_adds_counter_if_exists(self, tmp_path):
        """Adds counter suffix if file exists."""
        dest = tmp_path / "file.mkv"
        dest.touch()

        result = ensure_unique_destination(dest)

        assert result == tmp_path / "file_1.mkv"

    def test_increments_counter_for_multiple(self, tmp_path):
        """Increments counter for multiple existing files."""
        (tmp_path / "file.mkv").touch()
        (tmp_path / "file_1.mkv").touch()
        (tmp_path / "file_2.mkv").touch()

        result = ensure_unique_destination(tmp_path / "file.mkv")

        assert result == tmp_path / "file_3.mkv"


class TestSetupWorkingDirectories:
    """Tests for setup_working_directories function."""

    def test_returns_directory_paths(self, tmp_path):
        """Returns correct directory paths."""
        work, temp, original, waiting = setup_working_directories(tmp_path)

        assert work == tmp_path.parent / "work"
        assert temp == tmp_path.parent / "tmp"
        assert original == tmp_path.parent / "original"
        assert waiting == tmp_path.parent / "_a_virer"

    def test_dry_run_does_not_create(self, tmp_path):
        """Dry run does not create directories."""
        # Use a nested path that doesn't exist
        nested = tmp_path / "nested" / "deep"
        work, temp, original, waiting = setup_working_directories(nested, dry_run=True)

        # The returned paths should not be created in dry_run mode
        assert not work.exists()
        assert not temp.exists()
