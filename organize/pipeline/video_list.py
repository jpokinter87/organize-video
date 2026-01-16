"""Module de création et gestion de la liste des vidéos à traiter."""

import fcntl
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger
from rich.console import Console
from tqdm import tqdm

from organize.models.video import Video
from organize.utils.hash import checksum_md5
from organize.utils.database import select_db, hash_exists_in_db, add_hash_to_db
from organize.classification.type_detector import type_of_video, extract_file_infos
from organize.filesystem.discovery import get_files
from organize.pipeline.processor import create_paths

# Console pour l'affichage
console = Console()


def load_last_exec() -> float:
    """
    Charge la date de dernière exécution et met à jour le fichier.

    Lit la date de dernière exécution depuis le fichier last_exec_video.
    Si le fichier n'existe pas ou est invalide, utilise 3 jours en arrière.
    Sauvegarde la date actuelle pour la prochaine exécution.

    Utilise un verrouillage de fichier pour éviter les conditions de concurrence
    lorsque plusieurs instances du script s'exécutent simultanément.

    Returns:
        Timestamp de la dernière exécution.
    """
    last_exec_file_path = Path("last_exec_video")
    lock_file_path = Path("last_exec_video.lock")

    # Valeur par défaut : 3 jours avant
    last_exec = time.time() - 259200

    try:
        # Créer le fichier de verrouillage si nécessaire
        lock_file_path.touch(exist_ok=True)

        with open(lock_file_path, "r+") as lock_file:
            # Acquérir un verrou exclusif
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            try:
                # Lire la dernière exécution
                if last_exec_file_path.exists():
                    content = last_exec_file_path.read_text().strip()
                    if content:
                        last_exec = float(content)

                # Écriture atomique : écrire dans un fichier temporaire puis renommer
                temp_file = Path("last_exec_video.tmp")
                temp_file.write_text(str(time.time()))
                temp_file.replace(last_exec_file_path)

            finally:
                # Libérer le verrou
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    except (IOError, OSError, ValueError) as e:
        logger.warning(f"Erreur lors de la gestion de la date d'exécution : {e}")

    return last_exec


def get_last_exec_readonly() -> float:
    """
    Lit la date de dernière exécution sans la modifier.

    Utilisé en mode simulation pour ne pas modifier le fichier last_exec_video.

    Returns:
        Timestamp de la dernière exécution.
    """
    last_exec_file_path = Path("last_exec_video")
    try:
        content = last_exec_file_path.read_text().strip()
        return float(content) if content else time.time() - 259200
    except (FileNotFoundError, ValueError, OSError):
        return time.time() - 259200  # 3 jours avant


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

        # Vérification des doublons seulement si pas en mode force
        if not force_mode and not dry_run:
            video_db = select_db(file, storage_dir)
            if hash_exists_in_db(video_db, video.hash):
                logger.info(f"Hash de {file.name} déjà présent dans {video_db.name}")
                return None
        elif dry_run:
            logger.debug(f"SIMULATION - Vérification hash ignorée pour {file.name}")

        # Extraction des informations
        video.title, video.date_film, video.sequence, video.season, video.episode, video.spec = extract_file_infos(
            video)

        # Ajout à la base de données seulement si pas en mode force ou dry_run
        if not force_mode and not dry_run:
            add_hash_to_db(file, video.hash, storage_dir)
        elif dry_run:
            logger.debug(f"SIMULATION - Ajout hash ignoré pour {file.name}")

        create_paths(file, video, temp_dir, dry_run)

        return video

    except Exception as e:
        logger.error(f"Erreur lors du traitement de {file}: {e}")
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
        days_to_manage: Nombre de jours à considérer (100000000.0 = tous les fichiers).
        temp_dir: Répertoire temporaire pour les liens symboliques.
        storage_dir: Répertoire de stockage contenant les bases de données.
        force_mode: Si True, ignore la vérification des hashes.
        dry_run: Si True, simule les opérations sans modifier les fichiers.
        use_multiprocessing: Si True et plus de 10 fichiers, utilise le multiprocessing.

    Returns:
        Liste des objets Video à traiter.
    """
    files_to_process = []

    # Filtrage des fichiers
    if days_to_manage == 100000000.0:
        last_exec = 0
    else:
        if dry_run:
            # En mode simulation, ne pas mettre à jour le fichier last_exec
            last_exec = get_last_exec_readonly()
        else:
            last_exec = load_last_exec() if not days_to_manage else time.time() - (86400 * days_to_manage)

    for file in get_files(search_dir):
        if file.stat().st_ctime > last_exec or days_to_manage == 100000000.0:
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

    if use_multiprocessing and len(files_to_process) > 10:
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

    # Filtrage des résultats valides
    video_list = [video for video in results if video is not None]
    logger.info(f"Nombre de vidéos valides traitées: {len(video_list)}")
    return video_list
