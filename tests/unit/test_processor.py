"""Tests for video processor functions."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.pipeline.processor import (
    create_video_from_file,
    should_skip_duplicate,
    VideoProcessingResult,
)


class TestCreateVideoFromFile:
    """Tests for create_video_from_file function."""

    def test_creates_video_with_path(self):
        """Creates Video with complete_path_original set."""
        file_path = Path("/Films/Movie.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Films"):
                video = create_video_from_file(file_path)

        assert video.complete_path_original == file_path
        assert video.hash == "abc123"
        assert video.type_file == "Films"

    def test_sets_extended_sub_for_series(self):
        """Sets extended_sub correctly for series."""
        file_path = Path("/Séries/Show/episode.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Séries"):
                video = create_video_from_file(file_path)

        assert "Séries TV" in str(video.extended_sub)

    def test_extended_sub_empty_for_films(self):
        """extended_sub is empty for films."""
        file_path = Path("/Films/Movie.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Films"):
                video = create_video_from_file(file_path)

        assert str(video.extended_sub) == "" or str(video.extended_sub) == "."


class TestShouldSkipDuplicate:
    """Tests for should_skip_duplicate function."""

    def test_skip_in_dry_run(self):
        """Should not skip in dry run mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=True,
            hash_exists_fn=lambda h: True
        )
        assert result is False

    def test_skip_in_force_mode(self):
        """Should not skip in force mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=True,
            dry_run=False,
            hash_exists_fn=lambda h: True
        )
        assert result is False

    def test_skip_when_hash_exists(self):
        """Should skip when hash exists in normal mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=False,
            hash_exists_fn=lambda h: True
        )
        assert result is True

    def test_no_skip_when_hash_not_exists(self):
        """Should not skip when hash doesn't exist."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=False,
            hash_exists_fn=lambda h: False
        )
        assert result is False


class TestVideoProcessingResult:
    """Tests for VideoProcessingResult dataclass."""

    def test_success_result(self):
        """Creates success result."""
        video = MagicMock()
        result = VideoProcessingResult(success=True, video=video)

        assert result.success is True
        assert result.video is video
        assert result.error is None
        assert result.skipped is False

    def test_error_result(self):
        """Creates error result."""
        result = VideoProcessingResult(success=False, error="File not found")

        assert result.success is False
        assert result.video is None
        assert result.error == "File not found"

    def test_skipped_result(self):
        """Creates skipped result."""
        result = VideoProcessingResult(success=True, skipped=True, skip_reason="Duplicate")

        assert result.success is True
        assert result.skipped is True
        assert result.skip_reason == "Duplicate"
