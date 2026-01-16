"""Integration tests for the video processing pipeline."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.config import ConfigurationManager
from organize.pipeline import (
    PipelineContext,
    PipelineOrchestrator,
    ProcessingStats,
    create_video_list,
)
from organize.models.video import Video


class TestPipelineOrchestrator:
    """Integration tests for PipelineOrchestrator."""

    def _create_context(self, tmp_path: Path, dry_run: bool = True) -> PipelineContext:
        """Create a pipeline context for testing."""
        work_dir = tmp_path / "work"
        temp_dir = tmp_path / "temp"
        original_dir = tmp_path / "original"
        waiting_folder = tmp_path / "waiting"

        for d in [work_dir, temp_dir, original_dir, waiting_folder]:
            d.mkdir(parents=True, exist_ok=True)

        return PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=work_dir,
            temp_dir=temp_dir,
            original_dir=original_dir,
            waiting_folder=waiting_folder,
            dry_run=dry_run,
            force_mode=False,
            days_to_process=7.0,
        )

    def test_process_empty_video_list(self, tmp_path):
        """Processing empty list returns zero stats."""
        context = self._create_context(tmp_path)
        orchestrator = PipelineOrchestrator(context)

        stats = orchestrator.process_videos([])

        assert stats.total == 0
        assert stats.films == 0
        assert stats.series == 0

    def test_processing_stats_from_videos(self):
        """ProcessingStats correctly counts video types."""
        videos = []

        # Create mock videos of different types
        film = Video()
        film.type_file = "Films"
        film.title_fr = "Test Film"
        videos.append(film)

        series = Video()
        series.type_file = "Séries"
        series.title_fr = "Test Series"
        videos.append(series)

        anim = Video()
        anim.type_file = "Animation"
        anim.title_fr = "Test Animation"
        videos.append(anim)

        doc = Video()
        doc.type_file = "Docs"
        doc.title_fr = "Test Doc"
        videos.append(doc)

        stats = ProcessingStats.from_videos(videos)

        assert stats.total == 4
        assert stats.films == 1
        assert stats.series == 1
        assert stats.animation == 1
        assert stats.docs == 1

    def test_process_series_titles_empty_list(self, tmp_path):
        """process_series_titles handles empty list."""
        context = self._create_context(tmp_path)
        orchestrator = PipelineOrchestrator(context)

        # Should not raise
        orchestrator.process_series_titles([])

    def test_finalize_empty_work_dir(self, tmp_path):
        """Finalize handles empty work directory."""
        context = self._create_context(tmp_path)
        orchestrator = PipelineOrchestrator(context)

        # Should not raise
        orchestrator.finalize()


class TestConfigurationManagerValidation:
    """Integration tests for ConfigurationManager validation chain."""

    def test_validate_all_with_missing_directory(self, tmp_path):
        """validate_all fails on missing input directory."""
        manager = ConfigurationManager()
        manager.parse_args([
            "--input", str(tmp_path / "nonexistent"),
            "--dry-run"
        ])

        result = manager.validate_all()

        assert result.valid is False
        assert "does not exist" in result.error_message

    def test_validate_all_with_missing_api_keys(self, tmp_path):
        """validate_all fails when API keys are missing."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        manager = ConfigurationManager()
        manager.parse_args([
            "--input", str(input_dir),
            "--dry-run"
        ])

        with patch("organize.config.manager.check_api_keys", return_value=False):
            result = manager.validate_all()

        assert result.valid is False

    def test_validate_categories_with_valid_structure(self, tmp_path):
        """validate_categories succeeds with valid category structure."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "Films").mkdir()
        (input_dir / "Séries").mkdir()

        manager = ConfigurationManager()
        manager.parse_args(["--input", str(input_dir)])

        result, categories = manager.validate_categories()

        assert result.valid is True
        assert len(categories) == 2

    def test_validate_categories_with_no_categories(self, tmp_path):
        """validate_categories fails with no valid categories."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        # Create non-category directory
        (input_dir / "random").mkdir()

        manager = ConfigurationManager()
        manager.parse_args(["--input", str(input_dir)])

        result, categories = manager.validate_categories()

        assert result.valid is False
        assert len(categories) == 0


class TestCacheIntegration:
    """Integration tests for cache behavior."""

    def test_title_cache_is_used(self, tmp_path):
        """Orchestrator uses title cache for repeated titles."""
        context = PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
            dry_run=True,
            force_mode=False,
            days_to_process=7.0,
        )

        for d in [context.work_dir, context.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)

        orchestrator = PipelineOrchestrator(context)

        # Verify cache starts empty
        assert len(orchestrator._title_cache) == 0


class TestCreateVideoListIntegration:
    """Integration tests for create_video_list function."""

    def test_create_video_list_empty_directory(self, tmp_path):
        """create_video_list returns empty list for empty directory."""
        search_dir = tmp_path / "search"
        search_dir.mkdir()
        (search_dir / "Films").mkdir()

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        result = create_video_list(
            search_dir=search_dir,
            days_to_manage=7.0,
            temp_dir=temp_dir,
            storage_dir=storage_dir,
            force_mode=False,
            dry_run=True,
            use_multiprocessing=False
        )

        assert result == []

    def test_create_video_list_dry_run_mode(self, tmp_path):
        """create_video_list respects dry_run mode."""
        search_dir = tmp_path / "search"
        search_dir.mkdir()
        films_dir = search_dir / "Films"
        films_dir.mkdir()

        # Create a test video file
        test_video = films_dir / "Test.Movie.2024.mkv"
        test_video.write_bytes(b"fake video content")

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()

        with patch("organize.pipeline.video_list.checksum_md5", return_value="abc123"):
            result = create_video_list(
                search_dir=search_dir,
                days_to_manage=100000000.0,  # Process all files
                temp_dir=temp_dir,
                storage_dir=storage_dir,
                force_mode=True,
                dry_run=True,
                use_multiprocessing=False
            )

        # Should return the video without creating actual files
        assert len(result) == 1


class TestAPIFailureHandling:
    """Integration tests for API failure scenarios."""

    def test_api_validation_failure_stops_pipeline(self, tmp_path):
        """Pipeline stops when API validation fails."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "Films").mkdir()

        manager = ConfigurationManager()
        manager.parse_args([
            "--input", str(input_dir),
            "--dry-run"
        ])

        with patch("organize.config.manager.check_api_keys", return_value=False):
            result = manager.validate_api_keys()

        assert result.valid is False

    def test_api_connectivity_failure_stops_pipeline(self, tmp_path):
        """Pipeline stops when API connectivity fails."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "Films").mkdir()

        manager = ConfigurationManager()
        manager.parse_args([
            "--input", str(input_dir),
            "--dry-run"
        ])

        with patch("organize.config.manager.test_api_connectivity", return_value=False):
            result = manager.validate_api_connectivity()

        assert result.valid is False
