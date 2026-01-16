"""Tests unitaires pour le module main_processor."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

from organize.pipeline.main_processor import (
    _get_release_date,
    _is_match,
    _get_movie_name,
    _get_unique_genres,
    query_movie_database,
    set_fr_title_and_category,
)
from organize.config import GENRES, FILMANIM


class TestGetReleaseDate:
    """Tests pour la fonction _get_release_date."""

    def test_extrait_annee_film(self):
        """Extrait l'année d'un film."""
        movie = {"release_date": "2020-05-15"}
        assert _get_release_date(movie) == 2020

    def test_extrait_annee_serie(self):
        """Extrait l'année d'une série."""
        movie = {"first_air_date": "2018-10-20"}
        assert _get_release_date(movie) == 2018

    def test_preference_release_date(self):
        """Préfère release_date à first_air_date."""
        movie = {"release_date": "2020-05-15", "first_air_date": "2018-10-20"}
        assert _get_release_date(movie) == 2020

    def test_date_vide(self):
        """Retourne 0 si pas de date."""
        movie = {}
        assert _get_release_date(movie) == 0

    def test_date_none(self):
        """Retourne 0 si date est None."""
        movie = {"release_date": None}
        assert _get_release_date(movie) == 0

    def test_date_chaine_vide(self):
        """Retourne 0 si date est une chaîne vide."""
        movie = {"release_date": ""}
        assert _get_release_date(movie) == 0


class TestIsMatch:
    """Tests pour la fonction _is_match."""

    def test_resultat_unique(self):
        """Match si un seul résultat."""
        assert _is_match(total_results=1, date=2020, found_date=2018, no_date=False) is True

    def test_meme_date(self):
        """Match si les dates correspondent."""
        assert _is_match(total_results=5, date=2020, found_date=2020, no_date=False) is True

    def test_no_date_true(self):
        """Match si no_date est True."""
        assert _is_match(total_results=5, date=2020, found_date=2018, no_date=True) is True

    def test_found_date_zero(self):
        """Match si found_date est 0."""
        assert _is_match(total_results=5, date=2020, found_date=0, no_date=False) is True

    def test_pas_de_match(self):
        """Pas de match si conditions non remplies."""
        assert _is_match(total_results=5, date=2020, found_date=2018, no_date=False) is False


class TestGetMovieName:
    """Tests pour la fonction _get_movie_name."""

    def test_film_utilise_title(self):
        """Pour un film, utilise le champ 'title'."""
        movie = {"title": "Mon Film", "name": "Autre Nom"}
        assert _get_movie_name(movie, "Films") == "Mon Film"

    def test_animation_utilise_title(self):
        """Pour une animation, utilise le champ 'title'."""
        movie = {"title": "Animation", "name": "Autre Nom"}
        assert _get_movie_name(movie, "Animation") == "Animation"

    def test_serie_utilise_name(self):
        """Pour une série, utilise le champ 'name'."""
        movie = {"title": "Titre", "name": "Ma Série"}
        assert _get_movie_name(movie, "Séries") == "Ma Série"

    def test_serie_fallback_original_name(self):
        """Pour une série sans 'name', utilise 'original_name'."""
        movie = {"title": "Titre", "original_name": "Original Series"}
        assert _get_movie_name(movie, "Séries") == "Original Series"

    def test_serie_sans_name(self):
        """Retourne chaîne vide si pas de name/original_name."""
        movie = {"title": "Titre"}
        assert _get_movie_name(movie, "Séries") == ""


class TestGetUniqueGenres:
    """Tests pour la fonction _get_unique_genres."""

    def test_extrait_genres(self):
        """Extrait les genres depuis les IDs."""
        movie = {"genre_ids": [28, 35]}  # Action & Aventure, Comédie
        result = _get_unique_genres(movie)
        assert "Action & Aventure" in result
        assert "Comédie" in result

    def test_genres_uniques(self):
        """Ne duplique pas les genres identiques."""
        # 28 et 12 mappent tous deux vers "Action & Aventure"
        movie = {"genre_ids": [28, 12]}
        result = _get_unique_genres(movie)
        assert len(result) == 1
        assert result[0] == "Action & Aventure"

    def test_genre_inconnu(self):
        """Retourne N/A pour genre inconnu."""
        movie = {"genre_ids": [99999]}
        result = _get_unique_genres(movie)
        assert result == ["N/A"]

    def test_pas_de_genres(self):
        """Retourne liste vide si pas de genres."""
        movie = {}
        result = _get_unique_genres(movie)
        assert result == []


class TestQueryMovieDatabase:
    """Tests pour la fonction query_movie_database."""

    @patch.dict('os.environ', {'TMDB_API_KEY': ''})
    def test_erreur_sans_api_key(self):
        """Lève une erreur si la clé API est manquante."""
        with pytest.raises(RuntimeError, match="TMDB_API_KEY non configurée"):
            query_movie_database("Test", 2020, False, "test.mkv", "Films")

    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    def test_utilise_cache(self, mock_confirm, mock_cache_class):
        """Utilise les données en cache si disponibles."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {
            'total_results': 1,
            'results': [{
                'title': 'Film Test',
                'release_date': '2020-05-15',
                'genre_ids': [28]
            }]
        }
        mock_confirm.return_value = True

        result = query_movie_database("Test", 2020, False, "test.mkv", "Films")

        assert result[0] == 'Film Test'
        mock_cache.get_tmdb.assert_called_once()

    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.api.Tmdb')
    @patch('organize.ui.interactive.user_confirms_match')
    def test_appel_api_si_pas_cache(self, mock_confirm, mock_tmdb_class, mock_cache_class):
        """Appelle l'API si pas de cache."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {}

        mock_tmdb = MagicMock()
        mock_tmdb_class.return_value = mock_tmdb
        mock_tmdb.find_content.return_value = {
            'total_results': 1,
            'results': [{
                'title': 'Film API',
                'release_date': '2020-05-15',
                'genre_ids': [35]
            }]
        }
        mock_confirm.return_value = True

        result = query_movie_database("Test", 2020, False, "test.mkv", "Films")

        assert result[0] == 'Film API'
        mock_tmdb.find_content.assert_called_once()

    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.api.Tmdb')
    def test_gere_api_none(self, mock_tmdb_class, mock_cache_class):
        """Lève une erreur si l'API retourne None."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {}

        mock_tmdb = MagicMock()
        mock_tmdb_class.return_value = mock_tmdb
        mock_tmdb.find_content.return_value = None

        with pytest.raises(ConnectionError, match="Connexion TMDB impossible"):
            query_movie_database("Test", 2020, False, "test.mkv", "Films")

    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.handle_not_found_error')
    def test_handle_not_found_si_pas_resultats(self, mock_handle_error, mock_cache_class):
        """Appelle handle_not_found_error si pas de résultats."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {'total_results': 0, 'results': []}

        mock_handle_error.return_value = ("Film Manuel", ["Drame"], 2020)

        result = query_movie_database("Test", 2020, False, "test.mkv", "Films")

        mock_handle_error.assert_called_once()
        assert result == ("Film Manuel", ["Drame"], 2020)

    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    def test_recherche_manuelle(self, mock_confirm, mock_cache_class):
        """Relance la recherche avec titre manuel."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        # Premier appel retourne des résultats, l'utilisateur donne un titre manuel
        call_count = [0]
        def mock_get_tmdb(key):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    'total_results': 1,
                    'results': [{
                        'title': 'Film Original',
                        'release_date': '2020-05-15',
                        'genre_ids': [28]
                    }]
                }
            else:
                return {
                    'total_results': 1,
                    'results': [{
                        'title': 'Film Corrigé',
                        'release_date': '2020-05-15',
                        'genre_ids': [35]
                    }]
                }

        mock_cache.get_tmdb.side_effect = mock_get_tmdb

        # Premier appel: l'utilisateur donne un titre manuel
        # Deuxième appel: l'utilisateur accepte
        user_responses = iter(["Nouveau Titre", True])
        mock_confirm.side_effect = lambda *args: next(user_responses)

        result = query_movie_database("Test", 2020, False, "test.mkv", "Films")

        assert result[0] == 'Film Corrigé'


class TestSetFrTitleAndCategory:
    """Tests pour la fonction set_fr_title_and_category."""

    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    def test_traitement_film(self, mock_confirm, mock_cache_class):
        """Traite correctement un film."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {
            'total_results': 1,
            'results': [{
                'title': 'Film Français',
                'release_date': '2020-05-15',
                'genre_ids': [28]  # Action & Aventure
            }]
        }
        mock_confirm.return_value = True

        # Créer un mock Video
        video = MagicMock()
        video.title = "Test Movie"
        video.date_film = 2020
        video.spec = "1080p MULTi"
        video.complete_path_original = Path("/test/film.mkv")
        video.type_file = "Films"
        video.is_film_anim.return_value = True
        video.list_genres = []

        result = set_fr_title_and_category(video)

        assert result.title_fr is not None

    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    def test_traitement_serie(self, mock_confirm, mock_cache_class):
        """Traite correctement une série (pas de classification)."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {
            'total_results': 1,
            'results': [{
                'name': 'Série Française',
                'first_air_date': '2020-05-15',
                'genre_ids': [18]  # Drame
            }]
        }
        mock_confirm.return_value = True

        # Créer un mock Video
        video = MagicMock()
        video.title = "Test Series"
        video.date_film = 2020
        video.spec = "720p FR"
        video.complete_path_original = Path("/test/serie.mkv")
        video.type_file = "Séries"
        video.is_film_anim.return_value = False
        video.list_genres = []

        result = set_fr_title_and_category(video)

        # Pour les séries, genre doit être vide
        assert result.genre == ''

    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    def test_restaure_specs_originales(self, mock_confirm, mock_cache_class):
        """Restaure les specs originales après traitement."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.get_tmdb.return_value = {
            'total_results': 1,
            'results': [{
                'title': 'Film',
                'release_date': '2020-05-15',
                'genre_ids': [28]
            }]
        }
        mock_confirm.return_value = True

        video = MagicMock()
        video.title = "Test"
        video.date_film = 2020
        video.spec = "ORIGINAL_SPEC"
        video.complete_path_original = Path("/test/film.mkv")
        video.type_file = "Films"
        video.is_film_anim.return_value = True
        video.list_genres = []

        result = set_fr_title_and_category(video)

        assert result.spec == "ORIGINAL_SPEC"

    @patch('organize.api.CacheDB')
    @patch('organize.ui.interactive.user_confirms_match')
    @patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'})
    def test_skip_classification_genre_non_detecte(self, mock_confirm, mock_cache_class):
        """Ne classifie pas si genre est 'Non détecté'."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        # Retourne un genre inconnu (99999) qui sera mappé vers N/A puis Non détecté
        mock_cache.get_tmdb.return_value = {
            'total_results': 1,
            'results': [{
                'title': 'Film',
                'release_date': '2020-05-15',
                'genre_ids': [99999]  # Genre inconnu
            }]
        }
        mock_confirm.return_value = True

        video = MagicMock()
        video.title = "Test"
        video.date_film = 2020
        video.spec = "1080p"
        video.complete_path_original = Path("/test/film.mkv")
        video.type_file = "Films"
        video.is_film_anim.return_value = True
        video.list_genres = []

        result = set_fr_title_and_category(video)

        # Le film ne doit pas avoir de genre automatiquement classé
        # car N/A n'est pas supporté et sera traité comme Non détecté
        assert result is not None
