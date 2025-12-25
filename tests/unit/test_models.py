"""Tests for data models."""

import pytest
from pathlib import Path
from organize.models.video import Video
from organize.models.cache import SubfolderCache


class TestVideo:
    """Tests for the Video dataclass."""

    def test_video_default_values(self):
        """Video has sensible defaults."""
        video = Video()
        assert video.complete_path_original == Path()
        assert video.title == ""
        assert video.title_fr == ""
        assert video.date_film == 0
        assert video.type_file == ""
        assert video.list_genres == []

    def test_video_is_film(self):
        """is_film() returns True for Films type."""
        video = Video(type_file="Films")
        assert video.is_film() is True
        assert video.is_serie() is False
        assert video.is_animation() is False

    def test_video_is_serie(self):
        """is_serie() returns True for Séries type."""
        video = Video(type_file="Séries")
        assert video.is_serie() is True
        assert video.is_film() is False

    def test_video_is_animation(self):
        """is_animation() returns True for Animation type."""
        video = Video(type_file="Animation")
        assert video.is_animation() is True
        assert video.is_film() is False

    def test_video_is_film_serie(self):
        """is_film_serie() returns True for Films or Séries."""
        film = Video(type_file="Films")
        serie = Video(type_file="Séries")
        animation = Video(type_file="Animation")

        assert film.is_film_serie() is True
        assert serie.is_film_serie() is True
        assert animation.is_film_serie() is False

    def test_video_is_film_anim(self):
        """is_film_anim() returns True for Films or Animation."""
        film = Video(type_file="Films")
        animation = Video(type_file="Animation")
        serie = Video(type_file="Séries")

        assert film.is_film_anim() is True
        assert animation.is_film_anim() is True
        assert serie.is_film_anim() is False

    def test_video_is_not_doc(self):
        """is_not_doc() returns True for non-documentary types."""
        film = Video(type_file="Films")
        serie = Video(type_file="Séries")
        animation = Video(type_file="Animation")
        doc = Video(type_file="Docs")

        assert film.is_not_doc() is True
        assert serie.is_not_doc() is True
        assert animation.is_not_doc() is True
        assert doc.is_not_doc() is False

    def test_video_find_initial(self):
        """find_initial() returns lowercase title without article."""
        video = Video(title_fr="The Matrix")
        # find_initial calls remove_article which preserves case, then lowercases
        result = video.find_initial()
        assert result == "matrix"

    def test_video_format_name_film(self):
        """format_name() formats film name correctly."""
        video = Video(
            type_file="Films",
            title_fr="Matrix",
            date_film=1999,
            spec="MULTi HEVC 1080p",
            complete_path_original=Path("/test/movie.mkv"),
        )
        result = video.format_name("Matrix")
        assert "Matrix" in result
        assert "1999" in result
        assert "MULTi" in result
        assert result.endswith(".mkv")

    def test_video_format_name_serie(self):
        """format_name() formats series name with season/episode."""
        video = Video(
            type_file="Séries",
            title_fr="Breaking Bad",
            date_film=2008,
            season=1,
            episode=1,
            sequence="- S01E01 -",
            spec="MULTi x264 720p",
            complete_path_original=Path("/test/episode.mkv"),
        )
        result = video.format_name("Breaking Bad")
        assert "Breaking Bad" in result
        assert "2008" in result
        assert "S01E01" in result
        assert result.endswith(".mkv")

    def test_video_format_name_ts_extension_converted(self):
        """format_name() converts .ts extension to .mp4."""
        video = Video(
            type_file="Films",
            title_fr="Test",
            date_film=2020,
            spec="FR",
            complete_path_original=Path("/test/movie.ts"),
        )
        result = video.format_name("Test")
        assert result.endswith(".mp4")
        assert not result.endswith(".ts")


class TestSubfolderCache:
    """Tests for the SubfolderCache class."""

    def test_cache_get_missing_key(self):
        """get() returns None for missing key."""
        cache = SubfolderCache()
        assert cache.get("nonexistent") is None

    def test_cache_set_and_get(self):
        """set() stores value that can be retrieved with get()."""
        cache = SubfolderCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_overwrite(self):
        """set() overwrites existing value."""
        cache = SubfolderCache()
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_cache_multiple_keys(self):
        """Cache stores multiple keys independently."""
        cache = SubfolderCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
