"""SQLite cache for API responses."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from organize.config.settings import CACHE_EXPIRATION_SECONDS


class CacheDB:
    """
    SQLite-based cache for TMDB and TVDB API responses.

    Caches API responses to reduce network requests and improve performance.
    Supports expiration-based cache invalidation.

    Attributes:
        db_path: Path to the SQLite database file.
        conn: Active database connection, or None if closed.
    """

    def __init__(self, db_path: Path = Path("cache.db")) -> None:
        """
        Initialize the cache database.

        Args:
            db_path: Path to the SQLite database file. Created if not exists.
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection and create tables."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")

    def create_tables(self) -> None:
        """Create cache tables if they don't exist."""
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS tmdb_cache (
                    query TEXT PRIMARY KEY,
                    result TEXT,
                    timestamp INTEGER
                );

                CREATE TABLE IF NOT EXISTS tvdb_cache (
                    series_id INTEGER,
                    season INTEGER,
                    episode INTEGER,
                    result TEXT,
                    timestamp INTEGER,
                    PRIMARY KEY (series_id, season, episode)
                );
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

    def get_tmdb(self, query: str, expiration: int = CACHE_EXPIRATION_SECONDS) -> Dict:
        """
        Retrieve cached TMDB response.

        Args:
            query: The search query used as cache key.
            expiration: Cache expiration time in seconds (default 24 hours).

        Returns:
            Cached response dict, or empty dict if not found/expired.
        """
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT result, timestamp FROM tmdb_cache WHERE query = ?",
                (query,)
            )
            row = cursor.fetchone()
            if row and (time.time() - row[1] < expiration):
                return json.loads(row[0])
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Error retrieving TMDB cache: {e}")
        return {}

    def set_tmdb(self, query: str, result: Dict) -> None:
        """
        Store TMDB response in cache.

        Args:
            query: The search query used as cache key.
            result: The API response to cache.
        """
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO tmdb_cache (query, result, timestamp) VALUES (?, ?, ?)",
                (query, json.dumps(result), int(time.time()))
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Error saving TMDB cache: {e}")

    def get_tvdb(
        self,
        series_id: int,
        season: int,
        episode: int,
        expiration: int = CACHE_EXPIRATION_SECONDS
    ) -> Dict:
        """
        Retrieve cached TVDB episode data.

        Args:
            series_id: TVDB series ID.
            season: Season number.
            episode: Episode number.
            expiration: Cache expiration time in seconds (default 24 hours).

        Returns:
            Cached episode data dict, or empty dict if not found/expired.
        """
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT result, timestamp FROM tvdb_cache "
                "WHERE series_id = ? AND season = ? AND episode = ?",
                (series_id, season, episode)
            )
            row = cursor.fetchone()
            if row and (time.time() - row[1] < expiration):
                return json.loads(row[0])
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Error retrieving TVDB cache: {e}")
        return {}

    def set_tvdb(
        self,
        series_id: int,
        season: int,
        episode: int,
        result: Dict
    ) -> None:
        """
        Store TVDB episode data in cache.

        Args:
            series_id: TVDB series ID.
            season: Season number.
            episode: Episode number.
            result: The episode data to cache.
        """
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO tvdb_cache "
                "(series_id, season, episode, result, timestamp) VALUES (?, ?, ?, ?, ?)",
                (series_id, season, episode, json.dumps(result), int(time.time()))
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Error saving TVDB cache: {e}")

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "CacheDB":
        """Context manager entry - retourne l'instance."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ferme la connexion."""
        self.close()
