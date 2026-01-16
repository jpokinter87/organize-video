"""Fonctions de résolution de chemins pour l'organisation des vidéos."""

import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional, Tuple, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from organize.models.video import Video


# Taille maximale du cache LRU
MAX_CACHE_SIZE = 1000


class LRUCache:
    """
    Cache LRU (Least Recently Used) pour les recherches de sous-dossiers.

    Évite les parcours répétés du système de fichiers tout en limitant
    l'utilisation mémoire grâce à une politique d'éviction.

    Attributes:
        max_size: Nombre maximum d'entrées dans le cache.
    """

    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self._cache: OrderedDict[Tuple[str, str], Path] = OrderedDict()
        self._max_size = max_size

    def get(self, key: Tuple[str, str]) -> Optional[Path]:
        """
        Récupère le chemin en cache pour une clé.

        Déplace l'entrée en fin de liste (plus récemment utilisée).
        """
        if key in self._cache:
            # Déplacer l'entrée en fin (plus récemment utilisée)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: Tuple[str, str], value: Path) -> None:
        """
        Met en cache un chemin pour une clé.

        Évince l'entrée la moins récemment utilisée si le cache est plein.
        """
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                # Supprimer l'entrée la plus ancienne (début de la liste)
                self._cache.popitem(last=False)
        self._cache[key] = value

    def clear(self) -> None:
        """Efface toutes les entrées en cache."""
        self._cache.clear()

    def __len__(self) -> int:
        """Retourne le nombre d'entrées dans le cache."""
        return len(self._cache)


# Caches au niveau du module
subfolder_cache = LRUCache()
series_subfolder_cache = LRUCache()


def in_range(value: str, start: str, end: str) -> bool:
    """
    Vérifie si une valeur est dans une plage alphabétique.

    Args:
        value: Valeur à vérifier.
        start: Début de la plage (inclusif).
        end: Fin de la plage (inclusif).

    Returns:
        True si la valeur est dans la plage.
    """
    return start <= value <= end


def inflate(start: str, end: str, length: int) -> Tuple[str, str]:
    """
    Étend les chaînes à une longueur donnée pour la comparaison.

    Complète start avec 'a' et end avec 'z' jusqu'à la longueur cible.

    Args:
        start: Chaîne de début.
        end: Chaîne de fin.
        length: Longueur cible.

    Returns:
        Tuple de (start_complété, end_complété).
    """
    return start.ljust(length, 'a'), end.ljust(length, 'z')


def find_matching_folder(root_folder: Path, title: str) -> Path:
    """
    Trouve le dossier correspondant le plus profond pour un titre.

    Recherche les dossiers avec des motifs de plage comme "a-m" ou "n-z"
    et trouve celui qui contient le titre alphabétiquement.

    Args:
        root_folder: Dossier racine dans lequel chercher.
        title: Titre à faire correspondre.

    Returns:
        Chemin vers le dossier correspondant le plus profond, ou root_folder si aucune correspondance.
    """
    title_lower = title.lower()
    inflated_ranges: Dict[str, Tuple[str, str]] = {}

    def find_deepest(current_folder: Path, remaining_title: str) -> Path:
        best_match = current_folder

        try:
            for item in current_folder.iterdir():
                if not item.is_dir():
                    continue

                item_name_lower = item.name.lower()

                # Vérifier le motif de plage comme "a-m"
                if '-' in item_name_lower and ' - ' not in item_name_lower:
                    parts = item_name_lower.split('-', 1)
                    if len(parts) == 2:
                        start, end = parts
                        compare_length = max(len(start), len(end))

                        if item_name_lower not in inflated_ranges:
                            if compare_length > 1:
                                inflated_ranges[item_name_lower] = inflate(start, end, compare_length)
                            else:
                                inflated_ranges[item_name_lower] = (start, end)

                        range_start, range_end = inflated_ranges[item_name_lower]
                        if not in_range(remaining_title[:compare_length], range_start[:compare_length], range_end[:compare_length]):
                            continue

                        # Dossier de plage correspondant trouvé, aller plus profond
                        deeper = find_deepest(item, remaining_title)
                        return deeper if deeper != item else item

        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Erreur d'accès au dossier {current_folder}: {e}")

        return best_match

    return find_deepest(root_folder, title_lower)


def find_directory_for_video(video: "Video", root_folder: Path) -> Path:
    """
    Détermine le sous-dossier approprié pour un titre de vidéo.

    Utilise la correspondance de plage alphabétique pour trouver le dossier correspondant le plus profond.
    Les résultats sont mis en cache pour éviter les parcours répétés du système de fichiers.

    Args:
        video: Objet Video avec les informations de titre.
        root_folder: Dossier racine dans lequel chercher.

    Returns:
        Chemin vers le sous-dossier approprié.
    """
    cache_key = (str(video.complete_path_original), str(root_folder))
    cached_result = subfolder_cache.get(cache_key)
    if cached_result:
        return cached_result

    # Cas spécial pour les FILMS non détectés uniquement
    if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
        non_detectes_dir = root_folder / 'non détectés'
        subfolder_cache.set(cache_key, non_detectes_dir)
        return non_detectes_dir

    title = video.name_without_article
    inflated_ranges: Dict[str, Tuple[str, str]] = {}

    def find_deepest_matching_folder(current_folder: Path, remaining_title: str) -> Path:
        best_match = current_folder
        try:
            for item in current_folder.iterdir():
                if not item.is_dir():
                    continue

                item_name_lower = item.name.lower()
                if '-' in item_name_lower and not (' - ' in item_name_lower):
                    start, end = item_name_lower.split('-', 1)
                    compare_length = max(len(start), len(end))
                    if item_name_lower not in inflated_ranges:
                        if compare_length > 1:
                            inflated_ranges[item_name_lower] = inflate(start, end, compare_length)
                        else:
                            inflated_ranges[item_name_lower] = (start, end)
                    start, end = inflated_ranges[item_name_lower]
                    if not in_range(remaining_title[:compare_length], start[:compare_length], end[:compare_length]):
                        continue
                elif not remaining_title.startswith(item.name.lower()):
                    continue

                if video.type_file == 'Séries':
                    series_folder = item / remaining_title
                    if series_folder.exists() and series_folder.is_dir():
                        return series_folder

                deeper_match = find_deepest_matching_folder(item, remaining_title)
                return deeper_match if deeper_match != item else item
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Erreur d'accès au dossier {current_folder}: {e}")

        return best_match

    result = find_deepest_matching_folder(root_folder, title)

    # Pour les séries sans dossier correspondant, utiliser le dossier '#'
    if video.type_file == 'Séries' and result == root_folder:
        result = root_folder / '#'

    subfolder_cache.set(cache_key, result)
    return result


def find_symlink_and_sub_dir(video: "Video", symlinks_dir: Path) -> Tuple[Path, Path]:
    """
    Trouve le répertoire de symlinks et le sous-répertoire appropriés pour une vidéo.

    Args:
        video: Objet Video avec les informations de type et de genre.
        symlinks_dir: Répertoire de base des symlinks.

    Returns:
        Tuple de (complete_dir_symlinks, sub_directory).
    """
    if video.is_film_anim():
        target = symlinks_dir / 'Films' / video.genre
    else:
        target = symlinks_dir / video.extended_sub

    video.complete_dir_symlinks = find_directory_for_video(video, target)

    try:
        # Extraction du chemin relatif à partir du répertoire symlinks
        relative_path = video.complete_dir_symlinks.relative_to(symlinks_dir)
        video.sub_directory = relative_path
    except ValueError as e:
        logger.warning(f"Erreur lors de l'extraction du chemin relatif: {e}")
        video.sub_directory = Path('')

    return video.complete_dir_symlinks, video.sub_directory


def find_similar_file(
    video: "Video",
    storage_dir: Path,
    similarity_threshold: int = 80,
    year_tolerance: int = 1
) -> Optional[Path]:
    """
    Recherche un fichier similaire dans la structure du répertoire de stockage.

    Args:
        video: Vidéo pour laquelle chercher un fichier similaire.
        storage_dir: Répertoire de stockage racine.
        similarity_threshold: Score de similarité minimum (0-100).
        year_tolerance: Différence d'année maximale autorisée.

    Returns:
        Chemin vers le fichier similaire si trouvé, None sinon.
    """
    if video.is_animation():
        folder = storage_dir / 'Films'
    else:
        folder = storage_dir / video.type_file

    root_folders = [folder / genre for genre in video.list_genres if genre]

    for root_folder in root_folders:
        if not root_folder.exists():
            continue
        subfolder = find_directory_for_video(video, root_folder)
        similar_file = find_similar_file_in_folder(
            video, subfolder, similarity_threshold, year_tolerance
        )
        if similar_file:
            return similar_file
    return None


def find_similar_file_in_folder(
    video: "Video",
    sub_folder: Path,
    similarity_threshold: int = 80,
    year_tolerance: int = 1
) -> Optional[Path]:
    """
    Recherche un fichier similaire dans un dossier spécifique.

    Utilise la correspondance floue de chaînes pour trouver des fichiers avec des titres similaires.

    Args:
        video: Vidéo pour laquelle chercher un fichier similaire.
        sub_folder: Dossier dans lequel chercher.
        similarity_threshold: Score de similarité minimum (0-100).
        year_tolerance: Différence d'année maximale autorisée.

    Returns:
        Chemin vers le meilleur fichier correspondant si trouvé, None sinon.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz non disponible, vérification de similarité ignorée")
        return None

    def extract_title_year(filename: Path) -> Tuple[Optional[str], Optional[int]]:
        """Extrait le titre et l'année d'un nom de fichier comme 'Titre (2020).mkv'."""
        filename_str = filename.name
        match = re.match(r"(.+?)\s*\((\d{4})\)", filename_str)
        if match:
            title = match.group(1).strip()
            year = int(match.group(2))
            return title.lower(), year
        return None, None

    if not sub_folder.exists():
        return None

    best_match = None
    highest_similarity = 0
    video_title = video.title_fr.lower() if video.title_fr else ""

    if not video_title:
        return None

    try:
        for file in sub_folder.rglob('*'):
            if not file.is_file():
                continue

            file_title, file_year = extract_title_year(file)
            if not file_title or not file_year:
                continue

            similarity = fuzz.ratio(video_title, file_title)
            if similarity <= similarity_threshold or similarity <= highest_similarity:
                continue

            if abs(video.date_film - file_year) > year_tolerance:
                continue

            best_match = file
            highest_similarity = similarity
    except (FileNotFoundError, PermissionError) as e:
        logger.warning(f"Erreur d'accès au dossier {sub_folder}: {e}")

    return best_match


def clear_caches() -> None:
    """Efface tous les caches de résolution de chemins."""
    subfolder_cache.clear()
    series_subfolder_cache.clear()