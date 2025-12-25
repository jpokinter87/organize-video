"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def sample_video_names():
    """Sample video filenames for testing."""
    return [
        "The.Matrix.1999.MULTi.1080p.BluRay.x264-GROUP.mkv",
        "Breaking.Bad.S01E01.720p.WEB-DL.x265.mkv",
        "Inception.2010.FRENCH.BDRip.x264.mkv",
        "Game.of.Thrones.S08E06.VOSTFR.1080p.HDTV.mkv",
        "Les.Misérables.2012.TRUEFRENCH.1080p.BluRay.mkv",
    ]


@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file for testing."""
    video_file = tmp_path / "test_video.mkv"
    # Create file with some content for hash testing
    video_file.write_bytes(b"fake video content " * 1000)
    return video_file


@pytest.fixture
def mock_tmdb_response():
    """Mock TMDB API response."""
    return {
        "total_results": 1,
        "results": [{
            "id": 603,
            "title": "Matrix",
            "original_title": "The Matrix",
            "release_date": "1999-03-30",
            "genre_ids": [28, 878],
            "overview": "A computer hacker learns about the true nature of reality.",
        }]
    }


@pytest.fixture
def mock_tmdb_series_response():
    """Mock TMDB API response for TV series."""
    return {
        "total_results": 1,
        "results": [{
            "id": 1396,
            "name": "Breaking Bad",
            "original_name": "Breaking Bad",
            "first_air_date": "2008-01-20",
            "genre_ids": [18, 80],
            "overview": "A high school chemistry teacher turned meth producer.",
        }]
    }
