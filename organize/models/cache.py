"""Caching utilities for the organize package."""

from typing import Any, Dict, Optional


class SubfolderCache:
    """
    Simple in-memory cache for subfolder lookups.

    Used to avoid repeated filesystem traversals when finding
    the appropriate subfolder for video files.
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._cache: Dict[Any, Any] = {}

    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value, or None if not found.
        """
        return self._cache.get(key)

    def set(self, key: Any, value: Any) -> None:
        """
        Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to store.
        """
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)
