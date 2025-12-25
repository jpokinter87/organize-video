"""Tests for CacheDB SQLite cache."""

import pytest
import time
from pathlib import Path
from organize.api.cache_db import CacheDB


class TestCacheDB:
    """Tests for the CacheDB class."""

    def test_cache_db_creates_file(self, tmp_path):
        """CacheDB creates database file on init."""
        db_path = tmp_path / "test_cache.db"
        cache = CacheDB(db_path)
        assert db_path.exists()
        cache.close()

    def test_cache_db_creates_tables(self, tmp_path):
        """CacheDB creates required tables."""
        db_path = tmp_path / "test_cache.db"
        cache = CacheDB(db_path)

        # Check tables exist by querying them
        cursor = cache.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert 'tmdb_cache' in tables
        assert 'tvdb_cache' in tables
        cache.close()


class TestCacheDBTmdb:
    """Tests for TMDB cache operations."""

    def test_get_tmdb_missing_returns_empty(self, tmp_path):
        """get_tmdb returns empty dict for missing key."""
        cache = CacheDB(tmp_path / "test.db")
        result = cache.get_tmdb("nonexistent_query")
        assert result == {}
        cache.close()

    def test_set_and_get_tmdb(self, tmp_path):
        """set_tmdb stores data that can be retrieved."""
        cache = CacheDB(tmp_path / "test.db")

        test_data = {"title": "Matrix", "year": 1999}
        cache.set_tmdb("matrix 1999", test_data)

        result = cache.get_tmdb("matrix 1999")
        assert result == test_data
        cache.close()

    def test_get_tmdb_expired_returns_empty(self, tmp_path):
        """get_tmdb returns empty dict for expired cache."""
        cache = CacheDB(tmp_path / "test.db")

        test_data = {"title": "Old Movie"}
        cache.set_tmdb("old_query", test_data)

        # Get with 0 expiration (immediately expired)
        result = cache.get_tmdb("old_query", expiration=0)
        assert result == {}
        cache.close()

    def test_set_tmdb_overwrites(self, tmp_path):
        """set_tmdb overwrites existing entry."""
        cache = CacheDB(tmp_path / "test.db")

        cache.set_tmdb("query1", {"version": 1})
        cache.set_tmdb("query1", {"version": 2})

        result = cache.get_tmdb("query1")
        assert result == {"version": 2}
        cache.close()


class TestCacheDBTvdb:
    """Tests for TVDB cache operations."""

    def test_get_tvdb_missing_returns_empty(self, tmp_path):
        """get_tvdb returns empty dict for missing entry."""
        cache = CacheDB(tmp_path / "test.db")
        result = cache.get_tvdb(series_id=12345, season=1, episode=1)
        assert result == {}
        cache.close()

    def test_set_and_get_tvdb(self, tmp_path):
        """set_tvdb stores episode data that can be retrieved."""
        cache = CacheDB(tmp_path / "test.db")

        test_data = {"episodeName": "Pilot"}
        cache.set_tvdb(series_id=1396, season=1, episode=1, result=test_data)

        result = cache.get_tvdb(series_id=1396, season=1, episode=1)
        assert result == test_data
        cache.close()

    def test_get_tvdb_different_episodes(self, tmp_path):
        """get_tvdb returns correct data for different episodes."""
        cache = CacheDB(tmp_path / "test.db")

        cache.set_tvdb(1396, 1, 1, {"episodeName": "Pilot"})
        cache.set_tvdb(1396, 1, 2, {"episodeName": "Cat's in the Bag"})
        cache.set_tvdb(1396, 2, 1, {"episodeName": "Seven Thirty-Seven"})

        assert cache.get_tvdb(1396, 1, 1)["episodeName"] == "Pilot"
        assert cache.get_tvdb(1396, 1, 2)["episodeName"] == "Cat's in the Bag"
        assert cache.get_tvdb(1396, 2, 1)["episodeName"] == "Seven Thirty-Seven"
        cache.close()

    def test_get_tvdb_expired_returns_empty(self, tmp_path):
        """get_tvdb returns empty dict for expired cache."""
        cache = CacheDB(tmp_path / "test.db")

        cache.set_tvdb(1396, 1, 1, {"episodeName": "Old"})

        # Get with 0 expiration (immediately expired)
        result = cache.get_tvdb(1396, 1, 1, expiration=0)
        assert result == {}
        cache.close()


class TestCacheDBClose:
    """Tests for connection management."""

    def test_close_closes_connection(self, tmp_path):
        """close() properly closes the database connection."""
        cache = CacheDB(tmp_path / "test.db")
        assert cache.conn is not None

        cache.close()
        assert cache.conn is None

    def test_operations_after_close_safe(self, tmp_path):
        """Operations after close don't crash (return empty)."""
        cache = CacheDB(tmp_path / "test.db")
        cache.close()

        # These should not raise exceptions
        assert cache.get_tmdb("test") == {}
        assert cache.get_tvdb(1, 1, 1) == {}
        cache.set_tmdb("test", {"data": 1})  # Should be no-op
        cache.set_tvdb(1, 1, 1, {"data": 1})  # Should be no-op
