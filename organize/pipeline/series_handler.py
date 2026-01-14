"""Series episode handling functions."""

import re
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

from loguru import logger
from rich.console import Console
from tqdm import tqdm

if TYPE_CHECKING:
    from organize.models.video import Video

# Console pour l'affichage
console = Console()


def format_season_folder(season: int) -> str:
    """
    Format season number as folder name.

    Args:
        season: Season number.

    Returns:
        Formatted string like "Saison 01" or empty string for season 0.
    """
    if season == 0:
        return ""
    return f"Saison {season:02d}"


def find_series_folder(file_path: Path) -> Path:
    """
    Find the series root folder (the one ending with year).

    Walks up the path looking for a folder matching pattern "(YYYY)".

    Args:
        file_path: Path to the episode file.

    Returns:
        Path to the series folder, or immediate parent if not found.
    """
    current = file_path.parent

    while current.parent and current.parent != current:
        # Check if folder name ends with (YYYY)
        if re.search(r'\(\d{4}\)$', current.name):
            return current
        current = current.parent

    return file_path.parent


def build_episode_filename(
    series_title: str,
    year: int,
    sequence: str,
    episode_title: str,
    spec: str,
    extension: str
) -> str:
    """
    Build the complete episode filename.

    Args:
        series_title: Title of the series.
        year: Release year.
        sequence: Season/episode sequence like "- S01E05 -".
        episode_title: Title of the episode.
        spec: Technical specifications (language, codec, resolution).
        extension: File extension including dot.

    Returns:
        Formatted filename string.
    """
    parts = [f"{series_title} ({year})"]

    if sequence:
        parts.append(sequence)

    if episode_title:
        parts.append(episode_title)

    if spec:
        parts.append(f"- {spec}")

    filename = " ".join(parts)

    # Clean up multiple spaces
    filename = " ".join(filename.split())

    return f"{filename}{extension}"


def should_create_season_folder(current_path: Path, season: int) -> bool:
    """
    Check if a season folder needs to be created.

    Args:
        current_path: Current file path.
        season: Season number.

    Returns:
        True if season folder should be created.
    """
    if season == 0:
        return False

    season_folder = format_season_folder(season)
    parent_str = str(current_path.parent)

    # Check if we're already in the correct season folder
    return season_folder not in parent_str


def organize_episode_by_season(
    current_path: Path,
    formatted_filename: str,
    season: int,
    dry_run: bool = False
) -> Path:
    """
    Organize an episode file into the correct season folder.

    Args:
        current_path: Current path of the episode file.
        formatted_filename: New filename for the episode.
        season: Season number.
        dry_run: If True, simulate without making changes.

    Returns:
        New path for the episode file.
    """
    if season == 0:
        return current_path

    season_folder = format_season_folder(season)

    if not should_create_season_folder(current_path, season):
        # Already in correct season folder, just rename if needed
        new_path = current_path.parent / formatted_filename
        if new_path != current_path:
            if not dry_run and current_path.exists():
                current_path.rename(new_path)
                logger.debug(f"Episode renamed: {new_path}")
        return new_path

    # Need to create/move to season folder
    series_folder = find_series_folder(current_path)
    season_path = series_folder / season_folder
    new_path = season_path / formatted_filename

    if dry_run:
        logger.debug(f"SIMULATION - Create season folder: {season_path}")
        logger.debug(f"SIMULATION - Move episode to: {new_path}")
    else:
        season_path.mkdir(exist_ok=True)
        if current_path.exists():
            current_path.rename(new_path)
            logger.debug(f"Episode moved to season: {new_path}")

    return new_path


def _format_and_rename(video_obj: "Video", dry_run: bool = False) -> None:
    """
    Crée le sous-répertoire Saison XX seulement si nécessaire.

    Fonction interne utilisée par add_episodes_titles.

    Args:
        video_obj: Objet Video représentant l'épisode.
        dry_run: Si True, simule uniquement l'opération.
    """
    if video_obj.season == 0:
        return

    # Vérifier si on est déjà dans un dossier Saison
    current_path = video_obj.complete_path_temp_links
    current_parent = current_path.parent

    sequence_season = f'Saison {video_obj.season:02d}'

    # Si le parent ne contient pas déjà "Saison", on le crée
    if sequence_season not in str(current_parent):
        # Remonter jusqu'au dossier de la série (celui avec l'année)
        serie_folder = current_parent
        while serie_folder.parent and not re.search(r'\(\d{4}\)$', serie_folder.name):
            serie_folder = serie_folder.parent

        # Créer le dossier saison dans le dossier série
        complete_path_with_season = serie_folder / sequence_season
        new_file_path = complete_path_with_season / video_obj.formatted_filename

        if dry_run:
            logger.debug(f"SIMULATION - Création saison: {complete_path_with_season}")
            video_obj.complete_path_temp_links = new_file_path
        else:
            complete_path_with_season.mkdir(exist_ok=True)
            if current_path.exists():
                current_path.rename(new_file_path)
                video_obj.complete_path_temp_links = new_file_path
                logger.debug(f"Fichier déplacé vers saison: {new_file_path}")
            else:
                video_obj.complete_path_temp_links = new_file_path
    else:
        # On est déjà dans le bon dossier Saison, juste mettre à jour le nom
        if not dry_run and current_path.exists():
            new_path = current_parent / video_obj.formatted_filename
            if new_path != current_path:
                current_path.rename(new_path)
                video_obj.complete_path_temp_links = new_path


def _get_episode_title_from_tvdb(
    video_obj: "Video",
    serial: int,
    dry_run: bool = False
) -> Tuple["Video", int]:
    """
    Recherche le titre de l'épisode via l'API TVDB.

    Fonction interne utilisée par add_episodes_titles.

    Args:
        video_obj: Objet Video représentant l'épisode.
        serial: ID de la série TVDB (0 si inconnu).
        dry_run: Si True, simule uniquement l'opération.

    Returns:
        Tuple (video mise à jour, ID de série).
    """
    import os
    try:
        import tvdb_api
    except ImportError:
        logger.warning("tvdb_api non installé, impossible de récupérer les titres d'épisodes")
        return video_obj, serial

    from organize.api import CacheDB
    from organize.classification.text_processing import normalize

    TVDB_API_KEY = os.getenv("TVDB_API_KEY", "")

    if not TVDB_API_KEY:
        logger.warning("Clé API TVDB manquante, impossible de récupérer les titres d'épisodes")
        return video_obj, serial

    cache = CacheDB()

    # Vérifier le cache d'abord
    cached_data = cache.get_tvdb(serial, video_obj.season, video_obj.episode)
    if cached_data and cached_data.get("episodeName"):
        episode_name = cached_data["episodeName"]
        ext = video_obj.complete_path_original.suffix
        video_obj.formatted_filename = (
            f"{video_obj.title_fr} ({video_obj.date_film}) {video_obj.sequence} "
            f"{episode_name} - {video_obj.spec}{ext}"
        )
        if dry_run:
            logger.debug(f"SIMULATION - Titre épisode (cache): {episode_name}")
        cache.close()
        return video_obj, serial

    # Recherche réelle même en dry_run pour avoir les vrais titres
    if dry_run:
        console.print(
            f"[dim]🔍 Recherche du titre pour {video_obj.title_fr} S{video_obj.season:02d}E{video_obj.episode:02d}"
            f"...[/dim]")

    databases = [
        tvdb_api.Tvdb(apikey=TVDB_API_KEY, language='fr', interactive=False),
        tvdb_api.Tvdb(apikey=TVDB_API_KEY, language='en', interactive=False)
    ]

    for lang_index, data_serie in enumerate(databases):
        try:
            if not serial:
                try:
                    serial = data_serie[video_obj.title_fr]['id']
                    if dry_run:
                        logger.debug(f"SIMULATION - Série trouvée avec ID: {serial}")
                except (tvdb_api.tvdb_shownotfound, KeyError):
                    logger.debug(
                        f"Série {video_obj.title_fr} non trouvée en {'français' if lang_index == 0 else 'anglais'}")
                    continue

            data_episode = data_serie[serial][video_obj.season][video_obj.episode]
            titre_episode = data_episode.get('episodeName', '')

            if titre_episode:
                titre_episode = normalize(titre_episode)
                ext = video_obj.complete_path_original.suffix
                video_obj.formatted_filename = (
                    f'{video_obj.title_fr} ({video_obj.date_film}) {video_obj.sequence} '
                    f'{titre_episode} - {video_obj.spec}{ext}'
                )

                # Sauvegarder en cache
                cache.set_tvdb(serial, video_obj.season, video_obj.episode, {"episodeName": titre_episode})

                if dry_run:
                    console.print(f"[dim]✅ Trouvé: {titre_episode}[/dim]")
                break

        except (tvdb_api.tvdb_shownotfound, tvdb_api.tvdb_episodenotfound,
                tvdb_api.tvdb_seasonnotfound) as e:
            logger.warning(f'{video_obj.title_fr}: {type(e).__name__}')
            continue
        except Exception as e:
            logger.warning(f'Erreur TVDB pour {video_obj.title_fr}: {e}')
            continue

    cache.close()
    return video_obj, serial


def add_episodes_titles(
    list_of_videos: List["Video"],
    rep_destination: Path,
    dry_run: bool = False
) -> None:
    """
    Ajoute les titres d'épisodes et organise par saisons.

    Pour chaque épisode de série dans la liste, recherche le titre
    de l'épisode via l'API TVDB et renomme le fichier en conséquence.
    Organise également les fichiers dans des dossiers par saison.

    Args:
        list_of_videos: Liste des objets Video à traiter.
        rep_destination: Chemin du répertoire de destination.
        dry_run: Si True, simule uniquement les opérations.
    """
    # Traitement des séries avec barre de progression
    done = {}
    series_to_process = [video for video in list_of_videos if video.is_serie() and video.season > 0]

    if not series_to_process:
        return

    mode_text = "SIMULATION - " if dry_run else ""
    with tqdm(series_to_process, desc=f"{mode_text}Titres d'épisodes", unit="épisode") as pbar:
        for video in pbar:
            pbar.set_postfix_str(f"{video.title_fr} S{video.season:02d}E{video.episode:02d}")

            num_serie = done.get(video.title_fr, 0)
            video, num_serie = _get_episode_title_from_tvdb(video, num_serie, dry_run)
            done[video.title_fr] = num_serie
            _format_and_rename(video, dry_run)
