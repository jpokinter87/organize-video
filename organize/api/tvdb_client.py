"""TVDB (The TV Database) API client wrapper."""

from typing import Optional, Dict, Any

from loguru import logger

try:
    import tvdb_api
    TVDB_AVAILABLE = True
except ImportError:
    TVDB_AVAILABLE = False
    tvdb_api = None


class TvdbClient:
    """
    Wrapper for TVDB API using tvdb_api library.

    Provides methods to fetch TV series and episode information.

    Attributes:
        api_key: TVDB API key for authentication.
        language: Language code for results.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        language: str = 'fr'
    ) -> None:
        """
        Initialize TVDB client.

        Args:
            api_key: TVDB API key. Required for API access.
            language: Language code for results (default: 'fr' for French).
        """
        self.api_key = api_key
        self.language = language
        self._client: Optional[Any] = None

    def _get_client(self, language: Optional[str] = None) -> Optional[Any]:
        """
        Get or create TVDB API client instance.

        Args:
            language: Override language for this client instance.

        Returns:
            tvdb_api.Tvdb instance or None if not available.
        """
        if not TVDB_AVAILABLE:
            logger.warning("tvdb_api library not available")
            return None

        if not self.api_key:
            logger.warning("TVDB API key missing")
            return None

        lang = language or self.language
        try:
            return tvdb_api.Tvdb(
                apikey=self.api_key,
                language=lang,
                interactive=False
            )
        except Exception as e:
            logger.warning(f"Error creating TVDB client: {e}")
            return None

    def get_series_id(self, series_name: str, language: Optional[str] = None) -> Optional[int]:
        """
        Get TVDB series ID by name.

        Args:
            series_name: Name of the TV series to search for.
            language: Override language for this search.

        Returns:
            Series ID if found, None otherwise.
        """
        client = self._get_client(language)
        if not client:
            return None

        try:
            series = client[series_name]
            return series['id'] if series else None
        except (tvdb_api.tvdb_shownotfound, KeyError) as e:
            logger.debug(f"Series '{series_name}' not found: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error searching for series '{series_name}': {e}")
            return None

    def get_episode_info(
        self,
        series_id: int,
        season: int,
        episode: int,
        language: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get episode information by series ID, season, and episode number.

        Args:
            series_id: TVDB series ID.
            season: Season number.
            episode: Episode number.
            language: Override language for this search.

        Returns:
            Episode info dict with keys like 'episodeName', or None if not found.
        """
        client = self._get_client(language)
        if not client:
            return None

        try:
            episode_data = client[series_id][season][episode]
            return dict(episode_data) if episode_data else None
        except (tvdb_api.tvdb_shownotfound,
                tvdb_api.tvdb_seasonnotfound,
                tvdb_api.tvdb_episodenotfound) as e:
            logger.debug(f"Episode S{season:02d}E{episode:02d} not found: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching episode info: {e}")
            return None

    def get_episode_title(
        self,
        series_id: int,
        season: int,
        episode: int,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Get episode title by series ID, season, and episode number.

        Convenience method that extracts just the episode name.

        Args:
            series_id: TVDB series ID.
            season: Season number.
            episode: Episode number.
            language: Override language for this search.

        Returns:
            Episode title string, or None if not found.
        """
        info = self.get_episode_info(series_id, season, episode, language)
        if info:
            return info.get('episodeName')
        return None

    def search_with_fallback(
        self,
        series_name: str,
        season: int,
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """
        Search for episode info with language fallback.

        Tries French first, then English if not found.

        Args:
            series_name: Name of the TV series.
            season: Season number.
            episode: Episode number.

        Returns:
            Dict with 'series_id', 'episode_name', 'language' keys,
            or None if not found in any language.
        """
        # Try French first
        series_id = self.get_series_id(series_name, 'fr')
        if series_id:
            info = self.get_episode_info(series_id, season, episode, 'fr')
            if info and info.get('episodeName'):
                return {
                    'series_id': series_id,
                    'episode_name': info['episodeName'],
                    'language': 'fr'
                }

        # Fallback to English
        series_id = self.get_series_id(series_name, 'en')
        if series_id:
            info = self.get_episode_info(series_id, season, episode, 'en')
            if info and info.get('episodeName'):
                return {
                    'series_id': series_id,
                    'episode_name': info['episodeName'],
                    'language': 'en'
                }

        return None
