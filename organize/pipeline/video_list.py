"""Module de création et gestion de la liste des vidéos à traiter."""

import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger
from tqdm import tqdm

from organize.ui.console import console

from organize.models.video import Video
from organize.utils.hash import checksum_md5
from organize.utils.database import select_db, hash_exists_in_db, add_hash_to_db
from organize.utils.app_state import (
    load_last_exec,
    get_last_exec_readonly,
)
from organize.classification.type_detector import type_of_video, extract_file_infos
from organize.filesystem.discovery import get_files
from organize.pipeline.processor import create_paths, should_skip_duplicate
from organize.config.settings import PROCESS_ALL_FILES_DAYS, MULTIPROCESSING_VIDEO_THRESHOLD


def process_single_video(args: Tuple[Path, Path, Path, bool, bool]) -> Optional[Video]:
    """
    Traite un seul fichier vidéo (version pour multiprocessing).

    Cette fonction est conçue pour être appelée en parallèle via ProcessPoolExecutor.
    Elle extrait les métadonnées de base, vérifie les doublons et crée les liens temporaires.

    Args:
        args: Tuple contenant (file_path, temp_dir, storage_dir, force_mode, dry_run)

    Returns:
        Objet Video si le traitement réussit, None si le fichier est ignoré.
    """
    file, temp_dir, storage_dir, force_mode, dry_run = args

    try:
        video = Video()
        video.complete_path_original = file
        video.hash = checksum_md5(file)
        video.type_file = type_of_video(file)
        video.extended_sub = Path(video.type_file) / "Séries TV" if video.is_serie() else Path("")

        # Vérification des doublons via la fonction partagée
        video_db = select_db(file, storage_dir)

        def check_hash_exists(hash_value: str) -> bool:
            exists = hash_exists_in_db(video_db, hash_value)
            if exists:
                logger.info(f"Hash de {file.name} déjà présent dans {video_db.name}")
            return exists

        if should_skip_duplicate(video.hash, force_mode, dry_run, check_hash_exists):
            return None

        # Extraction des informations
        video.title, video.date_film, video.sequence, video.season, video.episode, video.spec = extract_file_infos(
            video)

        # Ajout à la base de données seulement si pas en mode force ou dry_run et hash valide
        if not force_mode and not dry_run and video.hash is not None:
            add_hash_to_db(file, video.hash, storage_dir)
        elif dry_run:
            logger.debug(f"SIMULATION - Ajout hash ignoré pour {file.name}")

        create_paths(file, video, temp_dir, dry_run)

        return video

    except Exception as e:
        # Logger au niveau WARNING avec traceback pour le débogage
        logger.warning(f"Échec du traitement de {file.name}: {type(e).__name__}: {e}")
        logger.opt(exception=True).debug(f"Traceback complet pour {file}")
        return None


def create_video_list(
    search_dir: Path,
    days_to_manage: float,
    temp_dir: Path,
    storage_dir: Path,
    force_mode: bool = False,
    dry_run: bool = False,
    use_multiprocessing: bool = False
) -> List[Video]:
    """
    Crée la liste des vidéos à traiter.

    Scanne le répertoire de recherche, filtre les fichiers selon leur date
    de création et traite chaque vidéo pour extraire ses métadonnées.

    Args:
        search_dir: Répertoire à scanner pour les vidéos.
        days_to_manage: Nombre de jours à considérer (PROCESS_ALL_FILES_DAYS = tous les fichiers).
        temp_dir: Répertoire temporaire pour les liens symboliques.
        storage_dir: Répertoire de stockage contenant les bases de données.
        force_mode: Si True, ignore la vérification des hashes.
        dry_run: Si True, simule les opérations sans modifier les fichiers.
        use_multiprocessing: Si True et plus de MULTIPROCESSING_VIDEO_THRESHOLD fichiers,
            utilise le multiprocessing.

    Returns:
        Liste des objets Video à traiter.
    """
    files_to_process = []

    # Filtrage des fichiers
    if days_to_manage == PROCESS_ALL_FILES_DAYS:
        last_exec = 0
    else:
        if dry_run:
            # En mode simulation, ne pas mettre à jour le fichier last_exec
            last_exec = get_last_exec_readonly()
        else:
            last_exec = load_last_exec() if not days_to_manage else time.time() - (86400 * days_to_manage)

    for file in get_files(search_dir):
        if file.stat().st_ctime > last_exec or days_to_manage == PROCESS_ALL_FILES_DAYS:
            if any(exclude in file.parts for exclude in ["ISX", "Applications"]):
                continue
            files_to_process.append(file)

    logger.info(f"Nombre de fichiers à traiter: {len(files_to_process)}")

    # Affichage du mode
    if dry_run:
        console.print("[yellow]🧪 MODE SIMULATION - Aucune modification de fichier[/yellow]")
        logger.warning("Mode simulation activé - aucune modification de fichier")
    if force_mode:
        console.print("[yellow]⚠️  Mode FORCE activé - Ignorer la vérification des hash[/yellow]")
        logger.warning("Mode force activé - vérification des hash désactivée")

    if not files_to_process:
        return []

    # Préparation des arguments avec les paramètres force et dry_run
    args_list = [(f, temp_dir, storage_dir, force_mode, dry_run) for f in files_to_process]

    if use_multiprocessing and len(files_to_process) > MULTIPROCESSING_VIDEO_THRESHOLD:
        console.print(f"🔄 Traitement en parallèle de {len(files_to_process)} fichiers...")
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            results = list(tqdm(
                executor.map(process_single_video, args_list),
                desc="Traitement des vidéos",
                total=len(args_list)
            ))
    else:
        console.print("🔄 Traitement séquentiel...")
        results = [process_single_video(args) for args in tqdm(args_list, desc="Traitement des vidéos")]

    # Filtrage des résultats valides et comptage des échecs
    video_list = [video for video in results if video is not None]
    failed_count = len(results) - len(video_list)

    logger.info(f"Nombre de vidéos valides traitées: {len(video_list)}")

    if failed_count > 0:
        logger.warning(f"Nombre de fichiers ignorés ou en échec: {failed_count}")
        # Identifier les fichiers échoués pour le rapport
        failed_files = [
            args_list[i][0].name for i, video in enumerate(results) if video is None
        ]
        for fname in failed_files[:5]:  # Limiter à 5 pour éviter spam
            logger.debug(f"  - {fname}")
        if len(failed_files) > 5:
            logger.debug(f"  ... et {len(failed_files) - 5} autres fichiers")

    return video_list
