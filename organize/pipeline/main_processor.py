"""Module principal de traitement des vidéos - classification et titrage."""

import os
from pathlib import Path
from typing import List, Tuple, Union, TYPE_CHECKING

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from organize.config import FILMANIM, GENRES, GENRE_UNDETECTED

if TYPE_CHECKING:
    from organize.models.video import Video

# Console pour l'affichage
console = Console()


def _get_release_date(movie: dict) -> int:
    """Extrait la date de sortie d'un film/série."""
    release_date = movie.get("release_date") or movie.get("first_air_date", '')
    return int(release_date[:4]) if release_date else 0


def _is_match(total_results: int, date: int, found_date: int, no_date: bool) -> bool:
    """Vérifie si un résultat correspond aux critères de recherche."""
    return total_results == 1 or date == found_date or no_date or found_date == 0


def _get_movie_name(movie: dict, video_type: str) -> str:
    """Extrait le nom du film/série."""
    return movie["title"] if video_type in FILMANIM else (movie.get("name") or movie.get("original_name", ""))


def _get_unique_genres(movie: dict) -> List[str]:
    """Extrait la liste unique des genres."""
    return list(dict.fromkeys(GENRES.get(int(g), "N/A") for g in movie.get("genre_ids", [])))


def query_movie_database(
    name: str,
    date: int,
    no_date: bool,
    complete_name: str,
    type_video: str,
    video_file_path: Path = None,
    occurence: int = 1
) -> Tuple[str, List[str], int]:
    """
    Interroge la base de données TMDB pour trouver un film/série.

    Args:
        name: Nom du film/série à rechercher.
        date: Année de sortie.
        no_date: True si l'année n'est pas connue.
        complete_name: Nom complet du fichier original.
        type_video: Type de vidéo ('Films', 'Animation', 'Séries').
        video_file_path: Chemin du fichier vidéo pour visualisation.
        occurence: Numéro de tentative (1-4).

    Returns:
        Tuple (nom français, liste des genres, année).
    """
    from organize.api import CacheDB, Tmdb
    from organize.ui.interactive import (
        launch_video_player,
        wait_for_user_after_viewing,
        choose_genre_manually,
        user_confirms_match,
        handle_not_found_error,
    )
    from organize.classification.text_processing import extract_title_from_filename

    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

    if not TMDB_API_KEY:
        logger.error("Clé API TMDB manquante. Impossible de continuer.")
        raise RuntimeError("TMDB_API_KEY non configurée")

    cache = CacheDB()
    cache_key = f"{type_video}-{name}-{date}"
    cached_data = cache.get_tmdb(cache_key)

    if cached_data:
        json_data = cached_data
    else:
        base = Tmdb()
        json_data = base.find_content(name, type_video)
        if json_data is None:
            logger.error("Impossible de se connecter à l'API TMDB.")
            cache.close()
            raise ConnectionError("Connexion TMDB impossible")
        if json_data:
            cache.set_tmdb(cache_key, json_data)

    cache.close()

    if not json_data or json_data['total_results'] == 0:
        return handle_not_found_error(
            name, complete_name, date, no_date, type_video,
            video_file_path, occurence, query_movie_database
        )

    # Parcourir les résultats
    for movie in json_data['results']:
        found_date = _get_release_date(movie)

        if _is_match(json_data['total_results'], date, found_date, no_date):
            temp_name = _get_movie_name(movie, type_video)
            temp_list_genre = _get_unique_genres(movie)

            user_response = user_confirms_match(
                complete_name, temp_name, found_date,
                temp_list_genre, type_video, video_file_path
            )

            if user_response is True:
                return temp_name, temp_list_genre, found_date
            elif isinstance(user_response, str):
                console.print(f"[blue]🔄 Nouvelle recherche avec le titre manuel : '{user_response}'[/blue]")
                return query_movie_database(
                    user_response, date, no_date, complete_name,
                    type_video, video_file_path, occurence + 1
                )

    return handle_not_found_error(
        name, complete_name, date, no_date, type_video,
        video_file_path, occurence, query_movie_database
    )


def set_fr_title_and_category(video: "Video") -> "Video":
    """
    Définit le titre français et la catégorie d'une vidéo.

    Interroge l'API TMDB pour obtenir le titre français et les genres,
    puis classifie la vidéo selon son genre principal.

    Args:
        video: Objet Video à traiter.

    Returns:
        Objet Video mis à jour avec titre français et genre.
    """
    from organize.classification.text_processing import normalize, remove_article
    from organize.classification.genre_classifier import handle_unsupported_genres, classify_movie

    original_spec = video.spec
    original_filename = video.complete_path_original.name

    no_date = not bool(video.date_film)
    name_fr, video.list_genres, date = query_movie_database(
        str(video.title),
        video.date_film,
        no_date,
        original_filename,
        video.type_file,
        video.complete_path_original
    )

    video.list_genres = list(set(video.list_genres))  # Supprime les doublons

    video.title_fr = normalize(name_fr)
    video.name_without_article = remove_article(video.title_fr).lower()
    video.date_film = date

    # Restaurer les specs originales
    video.spec = original_spec

    if video.is_film_anim():
        # Gérer les genres non supportés AVANT la classification
        video = handle_unsupported_genres(video, video.list_genres)

        # Seulement classifier si on a des genres supportés
        if video.list_genres and video.list_genres[0] != GENRE_UNDETECTED:
            video = classify_movie(video)
    else:
        video.genre = ''

    return video
