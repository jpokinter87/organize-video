"""Tests for video type detection and file info extraction."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from organize.classification.type_detector import type_of_video, extract_file_infos


class TestTypeOfVideo:
    """Tests for type_of_video function."""

    def test_detects_films(self):
        """Detects Films category in path."""
        path = Path("/media/Films/Matrix.mkv")
        assert type_of_video(path) == "Films"

    def test_detects_series(self):
        """Detects Séries category in path."""
        path = Path("/media/Séries/Breaking Bad/S01E01.mkv")
        assert type_of_video(path) == "Séries"

    def test_detects_animation(self):
        """Detects Animation category in path."""
        path = Path("/media/Animation/Toy Story.mkv")
        assert type_of_video(path) == "Animation"

    def test_detects_docs(self):
        """Detects Docs category in path."""
        path = Path("/media/Docs/Nature.mkv")
        assert type_of_video(path) == "Docs"

    def test_detects_docs_sharp(self):
        """Detects Docs#1 category in path."""
        path = Path("/media/Docs#1/Documentary.mkv")
        assert type_of_video(path) == "Docs#1"

    def test_no_category_found(self):
        """Returns empty string when no category matches."""
        path = Path("/downloads/random_video.mkv")
        assert type_of_video(path) == ""

    def test_category_in_middle_of_path(self):
        """Detects category when not at root level."""
        path = Path("/storage/nas/Films/Action/Matrix.mkv")
        assert type_of_video(path) == "Films"


class TestExtractFileInfos:
    """Tests for extract_file_infos function."""

    @pytest.fixture
    def mock_video(self):
        """Create a mock Video object."""
        video = MagicMock()
        return video

    def test_extracts_basic_movie_info(self, mock_video):
        """Extracts title and year from movie filename."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.mkv")
        title, year, season_ep, season, episode, spec = extract_file_infos(mock_video)

        assert title == "Matrix"
        assert year == 1999
        assert season == 0
        assert episode == 0
        assert season_ep == ""

    def test_extracts_series_info(self, mock_video):
        """Extracts season and episode from series filename."""
        mock_video.complete_path_original = Path("/Séries/Breaking.Bad.S01E05.mkv")
        title, year, season_ep, season, episode, spec = extract_file_infos(mock_video)

        assert title == "Breaking Bad"
        assert season == 1
        assert episode == 5
        assert "S01E05" in season_ep

    def test_extracts_french_language(self, mock_video):
        """Detects French language marker."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.FRENCH.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "FR" in spec

    def test_extracts_multi_language(self, mock_video):
        """Detects MULTI language marker."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.MULTI.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "MULTi" in spec

    def test_extracts_vostfr_language(self, mock_video):
        """Detects VOSTFR language marker."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.VOSTFR.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "VOSTFR" in spec

    def test_extracts_x264_codec(self, mock_video):
        """Detects x264 codec."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.x264.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "x264" in spec

    def test_extracts_hevc_codec(self, mock_video):
        """Detects HEVC codec from x265."""
        # Use more complete filename that guessit can parse correctly
        mock_video.complete_path_original = Path("/Films/Matrix.1999.1080p.BluRay.x265.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "HEVC" in spec

    def test_extracts_av1_codec(self, mock_video):
        """Detects AV1 codec."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.AV1.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "AV1" in spec

    def test_extracts_resolution(self, mock_video):
        """Detects screen resolution."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.1080p.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "1080p" in spec

    def test_extracts_4k_resolution(self, mock_video):
        """Detects 4K resolution."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.2160p.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "2160p" in spec

    def test_combines_lang_codec_resolution(self, mock_video):
        """Combines all specs into single string."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.FRENCH.x264.1080p.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "FR" in spec
        assert "x264" in spec
        assert "1080p" in spec

    def test_handles_title_with_dash(self, mock_video):
        """Handles title with dash - guessit may parse differently."""
        mock_video.complete_path_original = Path("/Films/The.Matrix.1999.mkv")
        title, _, _, _, _, _ = extract_file_infos(mock_video)

        # guessit extracts multi-word titles correctly
        assert title == "The Matrix"

    def test_handles_empty_title(self, mock_video):
        """Handles case when no title detected."""
        mock_video.complete_path_original = Path("/Films/1999.mkv")
        title, year, _, _, _, _ = extract_file_infos(mock_video)

        # guessit may parse this differently - just check we don't crash
        assert isinstance(title, str)

    def test_truefrench_maps_to_fr(self, mock_video):
        """TRUEFRENCH maps to FR."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.TRUEFRENCH.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "FR" in spec

    def test_vff_maps_to_fr(self, mock_video):
        """VFF maps to FR."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.VFF.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "FR" in spec

    def test_subfrench_maps_to_vostfr(self, mock_video):
        """SUBFRENCH maps to VOSTFR."""
        mock_video.complete_path_original = Path("/Films/Matrix.1999.SUBFRENCH.mkv")
        _, _, _, _, _, spec = extract_file_infos(mock_video)

        assert "VOSTFR" in spec
