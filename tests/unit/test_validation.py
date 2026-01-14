"""Tests for API validation module."""

import pytest
from unittest.mock import patch, MagicMock

from organize.api.validation import (
    get_api_key,
    validate_api_keys,
    test_api_connectivity,
    ensure_api_ready,
)


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_returns_value_when_set(self):
        """Should return the environment variable value when set."""
        with patch.dict("os.environ", {"TEST_KEY": "test_value"}):
            result = get_api_key("TEST_KEY")
            assert result == "test_value"

    def test_returns_none_when_not_set(self):
        """Should return None when environment variable is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_api_key("NONEXISTENT_KEY")
            assert result is None


class TestValidateApiKeys:
    """Tests for validate_api_keys function."""

    def test_returns_true_when_all_keys_present(self):
        """Should return True when both TMDB and TVDB keys are set."""
        with patch.dict("os.environ", {
            "TMDB_API_KEY": "tmdb_key",
            "TVDB_API_KEY": "tvdb_key"
        }):
            result = validate_api_keys()
            assert result is True

    def test_returns_false_when_tmdb_missing(self):
        """Should return False when TMDB_API_KEY is missing."""
        with patch.dict("os.environ", {"TVDB_API_KEY": "tvdb_key"}, clear=True):
            result = validate_api_keys()
            assert result is False

    def test_returns_false_when_tvdb_missing(self):
        """Should return False when TVDB_API_KEY is missing."""
        with patch.dict("os.environ", {"TMDB_API_KEY": "tmdb_key"}, clear=True):
            result = validate_api_keys()
            assert result is False

    def test_returns_false_when_both_missing(self):
        """Should return False when both keys are missing."""
        with patch.dict("os.environ", {}, clear=True):
            result = validate_api_keys()
            assert result is False

    def test_displays_error_on_console(self):
        """Should display error message on console when keys missing."""
        mock_console = MagicMock()
        with patch.dict("os.environ", {}, clear=True):
            validate_api_keys(console=mock_console)
            mock_console.print_error.assert_called_once()
            mock_console.print_warning.assert_called_once()


class TestTestApiConnectivity:
    """Tests for test_api_connectivity function."""

    def test_returns_true_when_tmdb_accessible(self):
        """Should return True when TMDB API is accessible."""
        with patch("organize.api.validation.TmdbClient") as mock_tmdb:
            mock_instance = MagicMock()
            mock_instance.find_content.return_value = {"results": []}
            mock_tmdb.return_value = mock_instance

            result = test_api_connectivity(tmdb_api_key="test_key")
            assert result is True

    def test_returns_false_when_tmdb_fails(self):
        """Should return False when TMDB API returns None."""
        with patch("organize.api.validation.TmdbClient") as mock_tmdb:
            mock_instance = MagicMock()
            mock_instance.find_content.return_value = None
            mock_tmdb.return_value = mock_instance

            result = test_api_connectivity(tmdb_api_key="test_key")
            assert result is False

    def test_displays_success_on_console(self):
        """Should display success message when connection succeeds."""
        mock_console = MagicMock()
        with patch("organize.api.validation.TmdbClient") as mock_tmdb:
            mock_instance = MagicMock()
            mock_instance.find_content.return_value = {"results": []}
            mock_tmdb.return_value = mock_instance

            test_api_connectivity(console=mock_console, tmdb_api_key="test_key")
            mock_console.print_success.assert_called()

    def test_displays_error_on_tmdb_failure(self):
        """Should display error message when TMDB fails."""
        mock_console = MagicMock()
        with patch("organize.api.validation.TmdbClient") as mock_tmdb:
            mock_instance = MagicMock()
            mock_instance.find_content.return_value = None
            mock_tmdb.return_value = mock_instance

            test_api_connectivity(console=mock_console, tmdb_api_key="test_key")
            mock_console.print_error.assert_called()


class TestEnsureApiReady:
    """Tests for ensure_api_ready function."""

    def test_returns_true_when_all_ready(self):
        """Should return True when validation and connectivity both pass."""
        with patch("organize.api.validation.validate_api_keys", return_value=True):
            with patch("organize.api.validation.test_api_connectivity", return_value=True):
                result = ensure_api_ready()
                assert result is True

    def test_returns_false_when_validation_fails(self):
        """Should return False when validation fails."""
        with patch("organize.api.validation.validate_api_keys", return_value=False):
            result = ensure_api_ready()
            assert result is False

    def test_returns_false_when_connectivity_fails(self):
        """Should return False when connectivity test fails."""
        with patch("organize.api.validation.validate_api_keys", return_value=True):
            with patch("organize.api.validation.test_api_connectivity", return_value=False):
                result = ensure_api_ready()
                assert result is False