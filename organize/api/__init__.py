"""API clients for TMDB and TVDB."""

from organize.api.cache_db import CacheDB
from organize.api.tmdb_client import TmdbClient, Tmdb
from organize.api.tvdb_client import TvdbClient
from organize.api.validation import (
    validate_api_keys,
    test_api_connectivity,
    ensure_api_ready,
    get_api_key,
)
from organize.api.exceptions import (
    APIError,
    APIConfigurationError,
    APIConnectionError,
    APIResponseError,
)

__all__ = [
    "CacheDB",
    "TmdbClient",
    "Tmdb",
    "TvdbClient",
    "validate_api_keys",
    "test_api_connectivity",
    "ensure_api_ready",
    "get_api_key",
    "APIError",
    "APIConfigurationError",
    "APIConnectionError",
    "APIResponseError",
]
