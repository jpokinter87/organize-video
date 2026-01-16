"""Tests for TVDB API client."""

import pytest
from unittest.mock import patch, MagicMock

from organize.api.tvdb_client import TvdbClient


class TestTvdbClientInit:
    """Tests for TvdbClient initialization."""

    def test_init_with_defaults(self):
        """Creates client with default values."""
        client = TvdbClient()
        assert client.api_key is None
        assert client.language == 'fr'

    def test_init_with_custom_values(self):
        """Creates client with custom values."""
        client = TvdbClient(api_key="test_key", language="en")
        assert client.api_key == "test_key"
        assert client.language == "en"


class TestTvdbClientGetClient:
    """Tests for _get_client method."""

    def test_get_client_no_library(self):
        """Returns None when tvdb_api not available."""
        client = TvdbClient(api_key="test_key")

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", False):
            result = client._get_client()
            assert result is None

    def test_get_client_no_api_key(self):
        """Returns None when API key is missing."""
        client = TvdbClient()

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True):
            result = client._get_client()
            assert result is None

    def test_get_client_success(self):
        """Creates client when library and key available."""
        client = TvdbClient(api_key="test_key")
        mock_tvdb = MagicMock()

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True), \
             patch("organize.api.tvdb_client.tvdb_api") as mock_api:
            mock_api.Tvdb.return_value = mock_tvdb

            result = client._get_client()

            assert result == mock_tvdb
            mock_api.Tvdb.assert_called_once_with(
                apikey="test_key",
                language="fr",
                interactive=False
            )

    def test_get_client_override_language(self):
        """Uses override language when provided."""
        client = TvdbClient(api_key="test_key", language="fr")

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True), \
             patch("organize.api.tvdb_client.tvdb_api") as mock_api:
            client._get_client(language="en")

            mock_api.Tvdb.assert_called_once_with(
                apikey="test_key",
                language="en",
                interactive=False
            )

    def test_get_client_exception(self):
        """Returns None on exception."""
        client = TvdbClient(api_key="test_key")

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True), \
             patch("organize.api.tvdb_client.tvdb_api") as mock_api:
            # Use ConnectionError which is a built-in exception we catch
            mock_api.Tvdb.side_effect = ConnectionError("Connection error")
            mock_api.tvdb_error = type('tvdb_error', (Exception,), {})

            result = client._get_client()

            assert result is None


class TestTvdbClientGetSeriesId:
    """Tests for get_series_id method."""

    def test_get_series_id_no_client(self):
        """Returns None when client unavailable."""
        client = TvdbClient()  # No API key

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True):
            result = client.get_series_id("Breaking Bad")
            assert result is None

    def test_get_series_id_success(self):
        """Returns series ID when found."""
        client = TvdbClient(api_key="test_key")
        mock_tvdb = MagicMock()
        mock_tvdb.__getitem__.return_value = {'id': 81189}

        with patch.object(client, '_get_client', return_value=mock_tvdb):
            result = client.get_series_id("Breaking Bad")

            assert result == 81189

    def test_get_series_id_not_found(self):
        """Returns None when series not found."""
        client = TvdbClient(api_key="test_key")
        mock_tvdb = MagicMock()

        # Simulate tvdb_shownotfound exception
        mock_exception = type('tvdb_shownotfound', (Exception,), {})
        mock_tvdb.__getitem__.side_effect = mock_exception("Not found")

        with patch.object(client, '_get_client', return_value=mock_tvdb), \
             patch("organize.api.tvdb_client.tvdb_api") as mock_api:
            mock_api.tvdb_shownotfound = mock_exception

            result = client.get_series_id("Nonexistent Show")

            assert result is None


class TestTvdbClientGetEpisodeInfo:
    """Tests for get_episode_info method."""

    def test_get_episode_info_no_client(self):
        """Returns None when client unavailable."""
        client = TvdbClient()

        with patch("organize.api.tvdb_client.TVDB_AVAILABLE", True):
            result = client.get_episode_info(81189, 1, 1)
            assert result is None

    def test_get_episode_info_success(self):
        """Returns episode info when found."""
        client = TvdbClient(api_key="test_key")
        mock_tvdb = MagicMock()
        mock_episode = {'episodeName': 'Pilot', 'overview': 'First episode'}
        mock_tvdb.__getitem__.return_value.__getitem__.return_value.__getitem__.return_value = mock_episode

        with patch.object(client, '_get_client', return_value=mock_tvdb):
            result = client.get_episode_info(81189, 1, 1)

            assert result == mock_episode


class TestTvdbClientGetEpisodeTitle:
    """Tests for get_episode_title method."""

    def test_get_episode_title_success(self):
        """Returns episode title when found."""
        client = TvdbClient(api_key="test_key")

        with patch.object(client, 'get_episode_info', return_value={'episodeName': 'Pilot'}):
            result = client.get_episode_title(81189, 1, 1)

            assert result == 'Pilot'

    def test_get_episode_title_no_info(self):
        """Returns None when no info found."""
        client = TvdbClient(api_key="test_key")

        with patch.object(client, 'get_episode_info', return_value=None):
            result = client.get_episode_title(81189, 1, 1)

            assert result is None

    def test_get_episode_title_no_name_key(self):
        """Returns None when episodeName not in info."""
        client = TvdbClient(api_key="test_key")

        with patch.object(client, 'get_episode_info', return_value={'overview': 'test'}):
            result = client.get_episode_title(81189, 1, 1)

            assert result is None


class TestTvdbClientSearchWithFallback:
    """Tests for search_with_fallback method."""

    def test_search_with_fallback_french_success(self):
        """Returns French result when found."""
        client = TvdbClient(api_key="test_key")

        with patch.object(client, 'get_series_id', return_value=81189) as mock_series, \
             patch.object(client, 'get_episode_info', return_value={'episodeName': 'Pilote'}):
            result = client.search_with_fallback("Breaking Bad", 1, 1)

            assert result == {
                'series_id': 81189,
                'episode_name': 'Pilote',
                'language': 'fr'
            }
            mock_series.assert_called_with("Breaking Bad", 'fr')

    def test_search_with_fallback_english_fallback(self):
        """Falls back to English when French not found."""
        client = TvdbClient(api_key="test_key")

        # French fails, English succeeds
        def mock_get_series_id(name, lang):
            if lang == 'en':
                return 81189
            return None

        def mock_get_episode_info(series_id, season, ep, lang):
            if lang == 'en':
                return {'episodeName': 'Pilot'}
            return None

        with patch.object(client, 'get_series_id', side_effect=mock_get_series_id), \
             patch.object(client, 'get_episode_info', side_effect=mock_get_episode_info):
            result = client.search_with_fallback("Breaking Bad", 1, 1)

            assert result == {
                'series_id': 81189,
                'episode_name': 'Pilot',
                'language': 'en'
            }

    def test_search_with_fallback_not_found(self):
        """Returns None when not found in any language."""
        client = TvdbClient(api_key="test_key")

        with patch.object(client, 'get_series_id', return_value=None):
            result = client.search_with_fallback("Nonexistent Show", 1, 1)

            assert result is None
