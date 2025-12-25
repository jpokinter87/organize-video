"""Tests for TMDB API client."""

import pytest
from unittest.mock import Mock, patch
from organize.api.tmdb_client import TmdbClient


class TestTmdbClientBuildUrl:
    """Tests for URL building."""

    def test_build_url_movie(self):
        """build_url creates correct movie search URL."""
        client = TmdbClient(api_key="test_key")
        url = client.build_url("Matrix", content_type="Films")

        assert "api.themoviedb.org" in url
        assert "/search/movie" in url
        assert "api_key=test_key" in url
        assert "query=Matrix" in url
        assert "language=fr-FR" in url

    def test_build_url_tv(self):
        """build_url creates correct TV search URL."""
        client = TmdbClient(api_key="test_key")
        url = client.build_url("Breaking Bad", content_type="Séries")

        assert "/search/tv" in url
        assert "query=Breaking" in url

    def test_build_url_animation_uses_movie(self):
        """Animation type uses movie endpoint."""
        client = TmdbClient(api_key="test_key")
        url = client.build_url("Toy Story", content_type="Animation")

        assert "/search/movie" in url


class TestTmdbClientFindContent:
    """Tests for content searching."""

    def test_find_content_no_api_key(self):
        """find_content returns None without API key."""
        client = TmdbClient(api_key=None)
        result = client.find_content("Matrix")
        assert result is None

    def test_find_content_empty_api_key(self):
        """find_content returns None with empty API key."""
        client = TmdbClient(api_key="")
        result = client.find_content("Matrix")
        assert result is None

    @patch('organize.api.tmdb_client.requests.get')
    def test_find_content_success(self, mock_get):
        """find_content returns API response on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_results": 1,
            "results": [{"title": "Matrix"}]
        }
        mock_get.return_value = mock_response

        client = TmdbClient(api_key="test_key")
        result = client.find_content("Matrix")

        assert result is not None
        assert result["total_results"] == 1
        assert result["results"][0]["title"] == "Matrix"

    @patch('organize.api.tmdb_client.requests.get')
    def test_find_content_http_error(self, mock_get):
        """find_content returns None on HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = TmdbClient(api_key="test_key")
        result = client.find_content("NonexistentMovie")

        assert result is None

    @patch('organize.api.tmdb_client.requests.get')
    def test_find_content_network_error(self, mock_get):
        """find_content returns None on network error."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        client = TmdbClient(api_key="test_key")
        result = client.find_content("Matrix")

        assert result is None

    @patch('organize.api.tmdb_client.requests.get')
    def test_find_content_timeout(self, mock_get):
        """find_content handles timeout properly."""
        import requests
        mock_get.side_effect = requests.Timeout("Request timed out")

        client = TmdbClient(api_key="test_key")
        result = client.find_content("Matrix")

        assert result is None


class TestTmdbClientIntegration:
    """Integration-style tests with mocked responses."""

    @patch('organize.api.tmdb_client.requests.get')
    def test_movie_search_full_response(self, mock_get):
        """Test full movie search response handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "page": 1,
            "total_results": 2,
            "total_pages": 1,
            "results": [
                {
                    "id": 603,
                    "title": "Matrix",
                    "original_title": "The Matrix",
                    "release_date": "1999-03-30",
                    "genre_ids": [28, 878],
                    "overview": "A computer hacker learns...",
                },
                {
                    "id": 604,
                    "title": "Matrix Reloaded",
                    "original_title": "The Matrix Reloaded",
                    "release_date": "2003-05-15",
                    "genre_ids": [28, 878],
                    "overview": "Neo and the rebels...",
                }
            ]
        }
        mock_get.return_value = mock_response

        client = TmdbClient(api_key="test_key")
        result = client.find_content("Matrix", "Films")

        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == 603

    @patch('organize.api.tmdb_client.requests.get')
    def test_tv_search_full_response(self, mock_get):
        """Test full TV search response handling."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "page": 1,
            "total_results": 1,
            "results": [
                {
                    "id": 1396,
                    "name": "Breaking Bad",
                    "original_name": "Breaking Bad",
                    "first_air_date": "2008-01-20",
                    "genre_ids": [18, 80],
                }
            ]
        }
        mock_get.return_value = mock_response

        client = TmdbClient(api_key="test_key")
        result = client.find_content("Breaking Bad", "Séries")

        assert result["total_results"] == 1
        assert result["results"][0]["name"] == "Breaking Bad"
