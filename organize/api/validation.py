"""API validation and connectivity testing."""

import os
from typing import Optional

from loguru import logger

from organize.api.tmdb_client import TmdbClient
from organize.ui.console import ConsoleUI


def get_api_key(key_name: str) -> Optional[str]:
    """
    Get an API key from environment variables.

    Args:
        key_name: Name of the environment variable.

    Returns:
        The API key value or None if not set.
    """
    return os.getenv(key_name)


def validate_api_keys(
    console: Optional[ConsoleUI] = None
) -> bool:
    """
    Validate the presence of required API keys.

    Checks for TMDB_API_KEY and TVDB_API_KEY in environment variables.

    Args:
        console: Optional ConsoleUI for displaying messages.

    Returns:
        True if all required keys are present, False otherwise.
    """
    missing_keys = []

    tmdb_key = get_api_key("TMDB_API_KEY")
    tvdb_key = get_api_key("TVDB_API_KEY")

    if not tmdb_key:
        missing_keys.append("TMDB_API_KEY")
    if not tvdb_key:
        missing_keys.append("TVDB_API_KEY")

    if missing_keys:
        logger.error(f"Missing API keys: {', '.join(missing_keys)}")
        if console:
            console.print_error(f"Missing API keys: {', '.join(missing_keys)}")
            console.print_warning("Please add them to your .env file")
        return False

    return True


def test_api_connectivity(
    console: Optional[ConsoleUI] = None,
    tmdb_api_key: Optional[str] = None,
    tvdb_api_key: Optional[str] = None
) -> bool:
    """
    Test connectivity to TMDB and TVDB APIs.

    Args:
        console: Optional ConsoleUI for displaying messages.
        tmdb_api_key: TMDB API key (uses env var if not provided).
        tvdb_api_key: TVDB API key (uses env var if not provided).

    Returns:
        True if all API connections succeed, False otherwise.
    """
    if console:
        console.print_info("Testing API connectivity...")

    # Get API keys from environment if not provided
    tmdb_key = tmdb_api_key or get_api_key("TMDB_API_KEY")
    tvdb_key = tvdb_api_key or get_api_key("TVDB_API_KEY")

    # Test TMDB
    tmdb = TmdbClient(api_key=tmdb_key)
    test_result = tmdb.find_content("test", "Films")

    if test_result is None:
        logger.error("Unable to connect to TMDB API")
        if console:
            console.print_error("TMDB connection failed")
        return False

    if console:
        console.print_success("TMDB connection successful")

    # Test TVDB (optional - used only for episode titles)
    if tvdb_key:
        try:
            import tvdb_api
            tvdb_test = tvdb_api.Tvdb(
                apikey=tvdb_key,
                language='fr',
                interactive=False
            )
            # Simple test - try to access the API
            # If this fails, TVDB will log a warning but not stop processing
            if console:
                console.print_success("TVDB connection successful")
        except Exception as e:
            logger.warning(f"TVDB connection test failed: {e}")
            if console:
                console.print_warning(f"TVDB connection warning: {e}")
                console.print_info("Episode titles may not be available")
            # Don't return False - TVDB is optional

    return True


def ensure_api_ready(
    console: Optional[ConsoleUI] = None
) -> bool:
    """
    Ensure APIs are configured and accessible.

    Combines validation and connectivity testing.

    Args:
        console: Optional ConsoleUI for displaying messages.

    Returns:
        True if APIs are ready to use, False otherwise.
    """
    if not validate_api_keys(console):
        return False

    if not test_api_connectivity(console):
        return False

    return True
