"""TMDB Service for Django web interface.

Provides enhanced TMDB API integration with poster caching,
credits retrieval, and detailed metadata.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@dataclass
class TmdbCandidate:
    """Represents a TMDB search result candidate."""
    id: int
    title: str
    original_title: str
    release_date: Optional[str]
    first_air_date: Optional[str]  # For TV shows
    overview: str
    poster_path: Optional[str]
    vote_average: float
    vote_count: int
    genres: List[str]
    directors: List[str]
    media_type: str  # 'movie' or 'tv'

    @property
    def year(self) -> Optional[int]:
        """Extract year from release date."""
        date = self.release_date or self.first_air_date
        if date and len(date) >= 4:
            try:
                return int(date[:4])
            except ValueError:
                pass
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'original_title': self.original_title,
            'release_date': self.release_date,
            'first_air_date': self.first_air_date,
            'overview': self.overview,
            'poster_path': self.poster_path,
            'vote_average': self.vote_average,
            'vote_count': self.vote_count,
            'genres': self.genres,
            'directors': self.directors,
            'media_type': self.media_type,
            'year': self.year,
        }


class TmdbService:
    """
    Enhanced TMDB API service for Django.

    Provides search, details, credits, and poster caching capabilities.
    """

    BASE_URL = 'https://api.themoviedb.org/3'
    IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/'
    DEFAULT_LANGUAGE = 'fr-FR'
    REQUEST_TIMEOUT = 10

    # Genre ID to French name mapping
    GENRE_MAP = {
        28: 'Action',
        12: 'Aventure',
        16: 'Animation',
        35: 'Comedie',
        80: 'Crime',
        99: 'Documentaire',
        18: 'Drame',
        10751: 'Famille',
        14: 'Fantastique',
        36: 'Histoire',
        27: 'Horreur',
        10402: 'Musique',
        9648: 'Mystere',
        10749: 'Romance',
        878: 'Science-Fiction',
        10770: 'Telefilm',
        53: 'Thriller',
        10752: 'Guerre',
        37: 'Western',
        # TV genres
        10759: 'Action & Adventure',
        10762: 'Enfants',
        10763: 'News',
        10764: 'Reality',
        10765: 'Sci-Fi & Fantasy',
        10766: 'Soap',
        10767: 'Talk',
        10768: 'War & Politics',
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TMDB service.

        Args:
            api_key: TMDB API key. Uses settings if not provided.
        """
        self.api_key = api_key or getattr(settings, 'TMDB_API_KEY', '')
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/120.0'
        })

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make authenticated API request."""
        if not self.api_key:
            logger.warning("TMDB API key not configured")
            return None

        url = f"{self.BASE_URL}{endpoint}"
        request_params = {
            'api_key': self.api_key,
            'language': self.DEFAULT_LANGUAGE,
        }
        if params:
            request_params.update(params)

        try:
            response = self._session.get(
                url,
                params=request_params,
                timeout=self.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"TMDB API error: {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"TMDB request failed: {e}")
            return None

    def search_movie(
        self,
        query: str,
        year: Optional[int] = None
    ) -> List[TmdbCandidate]:
        """
        Search for movies.

        Args:
            query: Search query string.
            year: Optional release year filter.

        Returns:
            List of TmdbCandidate objects.
        """
        params = {'query': query}
        if year:
            params['year'] = year

        data = self._make_request('/search/movie', params)
        if not data:
            return []

        candidates = []
        for result in data.get('results', [])[:10]:
            candidates.append(self._parse_movie_result(result))

        return candidates

    def search_tv(
        self,
        query: str,
        year: Optional[int] = None
    ) -> List[TmdbCandidate]:
        """
        Search for TV shows.

        Args:
            query: Search query string.
            year: Optional first air year filter.

        Returns:
            List of TmdbCandidate objects.
        """
        params = {'query': query}
        if year:
            params['first_air_date_year'] = year

        data = self._make_request('/search/tv', params)
        if not data:
            return []

        candidates = []
        for result in data.get('results', [])[:10]:
            candidates.append(self._parse_tv_result(result))

        return candidates

    def search(
        self,
        query: str,
        content_type: str = 'films',
        year: Optional[int] = None
    ) -> List[TmdbCandidate]:
        """
        Search for content based on type.

        Args:
            query: Search query string.
            content_type: 'films', 'series', 'animation', etc.
            year: Optional year filter.

        Returns:
            List of TmdbCandidate objects.
        """
        if content_type.lower() in ('series', 'séries'):
            return self.search_tv(query, year)
        else:
            return self.search_movie(query, year)

    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed movie information including credits.

        Args:
            movie_id: TMDB movie ID.

        Returns:
            Dictionary with full movie details.
        """
        data = self._make_request(
            f'/movie/{movie_id}',
            {'append_to_response': 'credits'}
        )
        if not data:
            return None

        directors = []
        cast = []

        credits = data.get('credits', {})
        for crew_member in credits.get('crew', []):
            if crew_member.get('job') == 'Director':
                directors.append(crew_member.get('name'))

        for actor in credits.get('cast', [])[:10]:
            cast.append(actor.get('name'))

        genres = [
            self.GENRE_MAP.get(g.get('id'), g.get('name'))
            for g in data.get('genres', [])
        ]

        return {
            'id': data.get('id'),
            'title': data.get('title'),
            'original_title': data.get('original_title'),
            'release_date': data.get('release_date'),
            'overview': data.get('overview'),
            'poster_path': data.get('poster_path'),
            'backdrop_path': data.get('backdrop_path'),
            'vote_average': data.get('vote_average', 0),
            'vote_count': data.get('vote_count', 0),
            'genres': genres,
            'directors': directors,
            'cast': cast,
            'runtime': data.get('runtime'),
            'media_type': 'movie',
        }

    def get_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed TV show information including credits.

        Args:
            tv_id: TMDB TV show ID.

        Returns:
            Dictionary with full TV show details.
        """
        data = self._make_request(
            f'/tv/{tv_id}',
            {'append_to_response': 'credits'}
        )
        if not data:
            return None

        creators = [c.get('name') for c in data.get('created_by', [])]
        cast = []

        credits = data.get('credits', {})
        for actor in credits.get('cast', [])[:10]:
            cast.append(actor.get('name'))

        genres = [
            self.GENRE_MAP.get(g.get('id'), g.get('name'))
            for g in data.get('genres', [])
        ]

        return {
            'id': data.get('id'),
            'title': data.get('name'),
            'original_title': data.get('original_name'),
            'first_air_date': data.get('first_air_date'),
            'overview': data.get('overview'),
            'poster_path': data.get('poster_path'),
            'backdrop_path': data.get('backdrop_path'),
            'vote_average': data.get('vote_average', 0),
            'vote_count': data.get('vote_count', 0),
            'genres': genres,
            'directors': creators,  # Use creators as directors for TV
            'cast': cast,
            'number_of_seasons': data.get('number_of_seasons'),
            'number_of_episodes': data.get('number_of_episodes'),
            'media_type': 'tv',
        }

    def get_details(
        self,
        tmdb_id: int,
        media_type: str = 'movie'
    ) -> Optional[Dict[str, Any]]:
        """
        Get details for movie or TV show.

        Args:
            tmdb_id: TMDB ID.
            media_type: 'movie' or 'tv'.

        Returns:
            Dictionary with full details.
        """
        if media_type == 'tv':
            return self.get_tv_details(tmdb_id)
        return self.get_movie_details(tmdb_id)

    def _parse_movie_result(self, result: Dict) -> TmdbCandidate:
        """Parse movie search result into TmdbCandidate."""
        genres = [
            self.GENRE_MAP.get(gid, str(gid))
            for gid in result.get('genre_ids', [])
        ]

        return TmdbCandidate(
            id=result.get('id'),
            title=result.get('title', ''),
            original_title=result.get('original_title', ''),
            release_date=result.get('release_date'),
            first_air_date=None,
            overview=result.get('overview', ''),
            poster_path=result.get('poster_path'),
            vote_average=result.get('vote_average', 0),
            vote_count=result.get('vote_count', 0),
            genres=genres,
            directors=[],  # Not available in search results
            media_type='movie',
        )

    def _parse_tv_result(self, result: Dict) -> TmdbCandidate:
        """Parse TV search result into TmdbCandidate."""
        genres = [
            self.GENRE_MAP.get(gid, str(gid))
            for gid in result.get('genre_ids', [])
        ]

        return TmdbCandidate(
            id=result.get('id'),
            title=result.get('name', ''),
            original_title=result.get('original_name', ''),
            release_date=None,
            first_air_date=result.get('first_air_date'),
            overview=result.get('overview', ''),
            poster_path=result.get('poster_path'),
            vote_average=result.get('vote_average', 0),
            vote_count=result.get('vote_count', 0),
            genres=genres,
            directors=[],
            media_type='tv',
        )

    def get_poster_url(
        self,
        poster_path: str,
        size: str = 'w342'
    ) -> Optional[str]:
        """
        Get full poster URL.

        Args:
            poster_path: Poster path from TMDB.
            size: Image size (w92, w154, w185, w342, w500, w780, original).

        Returns:
            Full poster URL or None.
        """
        if not poster_path:
            return None
        return f"{self.IMAGE_BASE_URL}{size}{poster_path}"

    def download_poster(
        self,
        poster_path: str,
        size: str = 'w342'
    ) -> Optional[bytes]:
        """
        Download poster image.

        Args:
            poster_path: Poster path from TMDB.
            size: Image size.

        Returns:
            Image bytes or None.
        """
        url = self.get_poster_url(poster_path, size)
        if not url:
            return None

        try:
            response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
            if response.status_code == 200:
                return response.content
            return None
        except requests.RequestException as e:
            logger.error(f"Failed to download poster: {e}")
            return None

    def cache_poster_for_video(self, video) -> bool:
        """
        Download and cache poster for a Video model instance.

        Args:
            video: Video model instance with poster_path set.

        Returns:
            True if poster was cached successfully.
        """
        if not video.poster_path:
            return False

        # Download poster
        image_data = self.download_poster(video.poster_path, 'w342')
        if not image_data:
            return False

        # Generate unique filename
        hash_input = f"{video.tmdb_id}_{video.poster_path}"
        filename = hashlib.md5(hash_input.encode()).hexdigest()[:16]
        filename = f"{filename}.jpg"

        # Save to video model
        video.poster_local.save(
            filename,
            ContentFile(image_data),
            save=True
        )

        return True

    def enrich_candidates_with_details(
        self,
        candidates: List[TmdbCandidate]
    ) -> List[TmdbCandidate]:
        """
        Enrich search candidates with director information.

        Args:
            candidates: List of candidates from search.

        Returns:
            Candidates with directors populated (for first 5).
        """
        enriched = []
        for i, candidate in enumerate(candidates):
            if i < 5:  # Only enrich first 5 to limit API calls
                details = self.get_details(candidate.id, candidate.media_type)
                if details:
                    candidate.directors = details.get('directors', [])
            enriched.append(candidate)
        return enriched

    def test_connection(self) -> bool:
        """Test API connection and key validity."""
        if not self.api_key:
            return False

        data = self._make_request('/configuration')
        return data is not None
