"""Video processing functions."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from loguru import logger

from organize.models.video import Video
from organize.utils.hash import checksum_md5
from organize.classification.type_detector import type_of_video

if TYPE_CHECKING:
    pass


@dataclass
class VideoProcessingResult:
    """
    Result of processing a single video file.

    Attributes:
        success: Whether processing completed successfully.
        video: The processed Video object (if successful).
        error: Error message (if failed).
        skipped: Whether video was skipped (e.g., duplicate).
        skip_reason: Reason for skipping.
    """

    success: bool = False
    video: Optional[Video] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


def create_video_from_file(file_path: Path) -> Video:
    """
    Create a Video object from a file path.

    Extracts basic metadata like hash and type.

    Args:
        file_path: Path to the video file.

    Returns:
        Video object with basic metadata set.
    """
    video = Video()
    video.complete_path_original = file_path
    video.hash = checksum_md5(file_path)
    video.type_file = type_of_video(file_path)

    # Définir extended_sub pour les séries
    if video.is_serie():
        video.extended_sub = Path(video.type_file) / "Séries TV"
    else:
        video.extended_sub = Path("")

    return video


def should_skip_duplicate(
    hash_value: Optional[str],
    force_mode: bool,
    dry_run: bool,
    hash_exists_fn: Callable[[str], bool]
) -> bool:
    """
    Check if video should be skipped due to being a duplicate.

    Args:
        hash_value: MD5 hash of the video file, or None if hashing failed.
        force_mode: If True, never skip duplicates.
        dry_run: If True, don't check for duplicates.
        hash_exists_fn: Function to check if hash exists in database.

    Returns:
        True if video should be skipped.
    """
    # Ne jamais ignorer en mode force ou dry_run
    if force_mode or dry_run:
        if dry_run:
            logger.debug("SIMULATION - Hash check skipped")
        return False

    # Impossible de vérifier les doublons sans hash
    if hash_value is None:
        logger.warning("Impossible de vérifier les doublons : calcul du hash échoué")
        return False

    # Vérifier si le hash existe
    if hash_exists_fn(hash_value):
        logger.debug("Hash déjà présent dans la base de données")
        return True

    return False


def process_video_metadata(video: Video) -> Video:
    """
    Process and extract metadata from video file.

    Uses guessit to extract title, year, season/episode info.

    Args:
        video: Video object with complete_path_original set.

    Returns:
        Video with metadata fields populated.
    """
    from organize.classification.type_detector import extract_file_infos

    (
        video.title,
        video.date_film,
        video.sequence,
        video.season,
        video.episode,
        video.spec
    ) = extract_file_infos(video)

    return video


def process_single_video_file(
    file_path: Path,
    force_mode: bool = False,
    dry_run: bool = False,
    hash_exists_fn: Optional[Callable[[str], bool]] = None,
    add_hash_fn: Optional[Callable[[str], None]] = None
) -> VideoProcessingResult:
    """
    Process a single video file.

    Args:
        file_path: Path to the video file.
        force_mode: If True, skip duplicate checks.
        dry_run: If True, simulate operations.
        hash_exists_fn: Function to check if hash exists.
        add_hash_fn: Function to add hash to database.

    Returns:
        VideoProcessingResult with processing outcome.
    """
    try:
        # Créer l'objet vidéo avec les métadonnées de base
        video = create_video_from_file(file_path)

        # Vérifier les doublons
        if hash_exists_fn is not None and video.hash is not None:
            if should_skip_duplicate(video.hash, force_mode, dry_run, hash_exists_fn):
                return VideoProcessingResult(
                    success=True,
                    skipped=True,
                    skip_reason=f"Duplicate hash: {video.hash[:8]}..."
                )

        # Extraire les métadonnées détaillées
        video = process_video_metadata(video)

        # Ajouter le hash à la base de données si pas en dry_run
        if add_hash_fn is not None and video.hash is not None and not dry_run and not force_mode:
            add_hash_fn(video.hash)
        elif dry_run:
            logger.debug(f"SIMULATION - Hash add skipped for {file_path.name}")

        return VideoProcessingResult(success=True, video=video)

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return VideoProcessingResult(success=False, error=str(e))


def create_paths(
    file: Path,
    video: Video,
    temp_dir: Path,
    dry_run: bool = False
) -> None:
    """
    Crée les chemins et liens symboliques temporaires.

    Crée la structure de répertoires temporaires et les liens symboliques
    pour le traitement des vidéos. En mode simulation, les opérations
    sont uniquement loggées sans créer de fichiers.

    Args:
        file: Chemin du fichier vidéo source.
        video: Objet Video contenant les métadonnées.
        temp_dir: Répertoire temporaire de base.
        dry_run: Si True, simule uniquement les opérations.
    """
    from organize.filesystem.symlinks import create_symlink

    def reps_pattern(filename: Path, pattern: str) -> tuple:
        """Extrait les chemins avant et après le pattern."""
        reps = filename.parts
        if 'Animation' in filename.parts:
            index = reps.index('Animation')
            pattern = '/'.join(reps[index - 1:index + 1])
        filename_str = str(filename)
        pattern = f'/{pattern}/'
        if pattern in filename_str:
            before, after = filename_str.split(pattern, 1)
            return Path(before), Path(after)
        else:
            logger.warning(f'Pattern {pattern} non trouvé dans {filename_str}')
            return Path(''), Path('')

    # Déterminer le chemin temporaire selon le type de vidéo
    if video.is_film():
        temp_path = temp_dir / video.type_file
    elif video.is_animation():
        temp_path = temp_dir / 'Films' / video.type_file
    else:
        b_rep, s_rep = reps_pattern(video.complete_path_original, video.type_file)
        temp_path = temp_dir / video.type_file / s_rep.parent

    if dry_run:
        logger.debug(f'SIMULATION - Création du répertoire: {temp_path}')
        name = video.complete_path_original.name
        video.destination_file = temp_path / name
        logger.debug(f'SIMULATION - Nouveau lien: {file} -> {video.destination_file}')
        return

    temp_path.mkdir(parents=True, exist_ok=True)

    name = video.complete_path_original.name
    video.destination_file = temp_path / name
    create_symlink(file, video.destination_file)
    logger.debug(f'Nouveau lien créé: {video.destination_file}')


def process_video(
    video: Video,
    waiting_folder: Path,
    storage_dir: Path,
    symlinks_dir: Path,
    similarity_threshold: int = 80,
    year_tolerance: int = 1
) -> Optional[Video]:
    """
    Traite une vidéo en vérifiant l'existence de fichiers similaires.

    Pour les films et animations, recherche des fichiers similaires et
    propose à l'utilisateur de gérer les doublons potentiels.

    Args:
        video: Objet Video à traiter.
        waiting_folder: Dossier d'attente pour les fichiers en suspens.
        storage_dir: Répertoire de stockage principal.
        symlinks_dir: Répertoire des liens symboliques.
        similarity_threshold: Seuil de similarité pour la détection (0-100).
        year_tolerance: Tolérance en années pour la correspondance.

    Returns:
        L'objet Video traité, ou None si le fichier a été ignoré.
    """
    from organize.filesystem.paths import find_similar_file
    from organize.filesystem.file_ops import handle_similar_file

    if video.is_film_anim():
        similar_file = find_similar_file(video, storage_dir, similarity_threshold, year_tolerance)
        if similar_file:
            result = handle_similar_file(
                video.complete_path_original,
                similar_file,
                waiting_folder,
                storage_dir
            )
            if result == similar_file:
                return None  # On garde l'ancien fichier
            elif result:
                video.complete_path_original = result

    return video
