"""TMDB (The Movie Database) API client."""

import urllib.parse
from typing import Dict, Optional

import requests
from loguru import logger

from organize.config.settings import FILMANIM, REQUEST_TIMEOUT_SECONDS


class TmdbClient:
    """
    Client for The Movie Database (TMDB) API.

    Provides methods to search for movies and TV shows.

    Attributes:
        api_key: TMDB API key for authentication.
        base_url: Base URL for TMDB API.
        language: Language code for results (default: French).
    """

    BASE_URL = 'https://api.themoviedb.org/3'
    SEARCH_MOVIE_ENDPOINT = '/search/movie'
    SEARCH_TV_ENDPOINT = '/search/tv'
    DEFAULT_LANGUAGE = 'fr-FR'
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0'

    def __init__(
        self,
        api_key: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE
    ) -> None:
        """
        Initialize TMDB client.

        Args:
            api_key: TMDB API key. If None, API calls will return None.
            language: Language code for results (default: fr-FR).
        """
        self.api_key = api_key
        self.language = language

    def build_url(self, query: str, content_type: str = 'Films') -> str:
        """
        Build API URL for content search.

        Args:
            query: Search query string.
            content_type: Type of content ('Films', 'Animation', 'Séries').

        Returns:
            Full URL for the API request.
        """
        # Use movie endpoint for Films and Animation, TV for series
        endpoint = (
            self.SEARCH_MOVIE_ENDPOINT
            if content_type in FILMANIM
            else self.SEARCH_TV_ENDPOINT
        )

        query_params = urllib.parse.urlencode({
            'api_key': self.api_key,
            'language': self.language,
            'query': query
        })

        return f'{self.BASE_URL}{endpoint}?{query_params}'

    def find_content(
        self,
        name: str,
        content_type: str = 'Films'
    ) -> Optional[Dict]:
        """
        Search for content in TMDB.

        Args:
            name: Name of the movie or TV show to search for.
            content_type: Type of content ('Films', 'Animation', 'Séries').

        Returns:
            API response as dict containing search results,
            or None if request fails or API key is missing.
        """
        if not self.api_key:
            logger.warning("TMDB API key missing")
            return None

        url = self.build_url(name, content_type)
        headers = {'User-Agent': self.USER_AGENT}

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"API request error: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.warning(f"Request error: {e}")
            return None


# Backward compatibility alias
Tmdb = TmdbClient
