"""Tests for MediaInfo extraction module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.classification.media_info import (
    _is_french,
    extract_media_info,
    media_info,
)
from organize.models.video import Video


class TestIsFrench:
    """Tests for _is_french helper function."""

    def test_detects_french_lowercase(self):
        """Should detect 'french' in lowercase."""
        assert _is_french(['french']) is True

    def test_detects_french_mixed_case(self):
        """Should detect 'French' with mixed case."""
        assert _is_french(['French']) is True

    def test_detects_french_in_list(self):
        """Should detect french among other languages."""
        assert _is_french(['english', 'french', 'german']) is True

    def test_returns_false_no_french(self):
        """Should return False when no french present."""
        assert _is_french(['english', 'german']) is False

    def test_returns_false_empty_list(self):
        """Should return False for empty list."""
        assert _is_french([]) is False


class TestExtractMediaInfo:
    """Tests for extract_media_info function."""

    def test_returns_existing_spec_if_complete(self):
        """Should return existing spec if it has 3+ parts."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = 'MULTi x264 1080p'

        result = extract_media_info(video)
        assert result == 'MULTi x264 1080p'

    def test_returns_existing_spec_on_error(self):
        """Should return existing spec if MediaInfo fails."""
        video = Video()
        video.complete_path_original = Path('/nonexistent/video.mkv')
        video.spec = 'VO'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi.parse.side_effect = Exception("File not found")
            result = extract_media_info(video)
            assert result == 'VO'

    def test_extracts_multi_for_multiple_audio(self):
        """Should detect MULTi when multiple audio tracks present."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 2
        mock_track0.audio_language_list = 'French / English'
        mock_track0.text_language_list = 'French'

        mock_track1 = MagicMock()
        mock_track1.width = 1920
        mock_track1.height = 1080
        mock_track1.format = 'AVC'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert 'MULTi' in result
            assert '1080p' in result
            assert 'x264' in result

    def test_extracts_fr_for_french_audio(self):
        """Should detect FR when single French audio track."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 1
        mock_track0.audio_language_list = 'French'
        mock_track0.text_language_list = None

        mock_track1 = MagicMock()
        mock_track1.width = 1920
        mock_track1.height = 1080
        mock_track1.format = 'x264'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert 'FR' in result

    def test_extracts_vostfr_for_french_subtitles(self):
        """Should detect VOSTFR when French subtitles only."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 1
        mock_track0.audio_language_list = 'English'
        mock_track0.text_language_list = 'French'

        mock_track1 = MagicMock()
        mock_track1.width = 1920
        mock_track1.height = 1080
        mock_track1.format = 'HEVC'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert 'VOSTFR' in result

    def test_extracts_vo_for_no_french(self):
        """Should detect VO when no French audio or subtitles."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 1
        mock_track0.audio_language_list = 'English'
        mock_track0.text_language_list = 'English'

        mock_track1 = MagicMock()
        mock_track1.width = 1920
        mock_track1.height = 1080
        mock_track1.format = 'x264'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert 'VO' in result

    def test_extracts_4k_resolution(self):
        """Should detect 2160p for 4K video."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 1
        mock_track0.audio_language_list = 'French'
        mock_track0.text_language_list = None

        mock_track1 = MagicMock()
        mock_track1.width = 3840
        mock_track1.height = 2160
        mock_track1.format = 'HEVC'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert '2160p' in result

    def test_extracts_720p_resolution(self):
        """Should detect 720p for HD video."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = ''

        mock_track0 = MagicMock()
        mock_track0.count_of_audio_streams = 1
        mock_track0.audio_language_list = 'French'
        mock_track0.text_language_list = None

        mock_track1 = MagicMock()
        mock_track1.width = 1280
        mock_track1.height = 720
        mock_track1.format = 'x264'

        with patch('pymediainfo.MediaInfo') as mock_mi:
            mock_mi_instance = MagicMock()
            mock_mi_instance.tracks = [mock_track0, mock_track1]
            mock_mi.parse.return_value = mock_mi_instance

            result = extract_media_info(video)
            assert '720p' in result


class TestMediaInfoAlias:
    """Tests for backward compatible media_info alias."""

    def test_alias_calls_extract_function(self):
        """Should call extract_media_info."""
        video = Video()
        video.complete_path_original = Path('/test/video.mkv')
        video.spec = 'FR x264 1080p'

        result = media_info(video)
        assert result == 'FR x264 1080p'