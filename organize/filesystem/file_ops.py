"""Opérations sur les fichiers pour le déplacement, la copie et le renommage."""

import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, TYPE_CHECKING

from loguru import logger
from rich.console import Console

from organize.filesystem.symlinks import create_symlink

if TYPE_CHECKING:
    from organize.models.video import Video

# Console pour l'affichage interactif
_console = Console()


def _safe_split_path(path_str: str, separator: str, default: str = "") -> str:
    """
    Divise un chemin de manière sécurisée et retourne la partie après le séparateur.

    Args:
        path_str: Chaîne du chemin à diviser.
        separator: Séparateur à rechercher.
        default: Valeur par défaut si le séparateur n'est pas trouvé.

    Returns:
        La partie du chemin après le séparateur, ou la valeur par défaut.
    """
    parts = path_str.split(separator, 1)
    if len(parts) < 2:
        logger.warning(f"Séparateur '{separator}' non trouvé dans le chemin: {path_str}")
        return default
    return parts[1]


def move_file(source: Path, destination: Path, dry_run: bool = False) -> bool:
    """
    Déplace un fichier vers la destination avec gestion des doublons.

    Args:
        source: Chemin du fichier source.
        destination: Chemin du fichier de destination.
        dry_run: Si True, simule uniquement l'opération.

    Returns:
        True si réussi, False sinon.
    """
    if dry_run:
        logger.info(f'SIMULATION - Déplacement: {source.name} -> {destination}')
        return True

    if not source.exists():
        logger.warning(f'Fichier source non trouvé: {source}')
        return False

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            logger.warning(f'Le fichier de destination existe: {destination}')
            if source.stat().st_size == destination.stat().st_size:
                logger.info(f'Fichier identique détecté, suppression de la source: {source}')
                source.unlink()
                return True
            else:
                destination = ensure_unique_destination(destination)
                logger.info(f'Renommage du fichier en: {destination}')

        shutil.move(str(source), str(destination))
        logger.info(f'Fichier déplacé: {destination}')
        return True

    except (OSError, shutil.Error) as e:
        logger.error(f'Erreur lors du déplacement de {source}: {e}')
        return False


def copy_tree(source_dir: Path, dest_dir: Path, dry_run: bool = False) -> bool:
    """
    Copie l'arborescence de répertoires vers la destination.

    Args:
        source_dir: Chemin du répertoire source.
        dest_dir: Chemin du répertoire de destination.
        dry_run: Si True, simule uniquement l'opération.

    Returns:
        True si réussi, False sinon.
    """
    if not source_dir.exists() or not any(source_dir.iterdir()):
        logger.warning('Aucun fichier à copier.')
        return False

    if dry_run:
        logger.info(f'SIMULATION - Copie arborescence: {source_dir} -> {dest_dir}')
        return True

    try:
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        shutil.copytree(source_dir, dest_dir, symlinks=True)
        logger.info(f"Arborescence copiée: {source_dir} -> {dest_dir}")
        return True

    except (OSError, shutil.Error) as e:
        logger.error(f"Erreur lors de la copie de l'arborescence: {e}")
        return False


def ensure_unique_destination(destination: Path) -> Path:
    """
    S'assure que le chemin de destination est unique en ajoutant un suffixe compteur.

    Args:
        destination: Chemin de destination souhaité.

    Returns:
        Chemin unique (l'original s'il n'existe pas, ou avec suffixe compteur).
    """
    if not destination.exists():
        return destination

    counter = 1
    base_name = destination.stem
    extension = destination.suffix

    while destination.exists():
        destination = destination.parent / f"{base_name}_{counter}{extension}"
        counter += 1

    return destination


def setup_working_directories(
    destination_dir: Path,
    dry_run: bool = False
) -> Tuple[Path, Path, Path, Path]:
    """
    Configure les répertoires de travail pour le traitement des vidéos.

    Args:
        destination_dir: Répertoire de destination de base.
        dry_run: Si True, retourne uniquement les chemins sans les créer.

    Returns:
        Tuple de (work_dir, temp_dir, original_dir, waiting_folder).
    """
    parent = destination_dir.parent
    work_dir = parent / "work"
    temp_dir = parent / "tmp"
    original_dir = parent / "original"
    waiting_folder = parent / "_a_virer"

    if dry_run:
        logger.debug("SIMULATION - Configuration des répertoires de travail")
        return work_dir, temp_dir, original_dir, waiting_folder

    # Créer les répertoires si nécessaire
    for dir_path in [work_dir, temp_dir, original_dir, waiting_folder]:
        dir_path.mkdir(parents=True, exist_ok=True)

    return work_dir, temp_dir, original_dir, waiting_folder


def aplatir_repertoire_series(repertoire_initial: Path) -> None:
    """
    Aplatit l'arborescence des répertoires de séries en déplaçant les fichiers vers le niveau supérieur.

    Déplace les fichiers des sous-répertoires imbriqués vers leurs répertoires parents
    pour simplifier la structure de répertoires des séries.

    Args:
        repertoire_initial: Répertoire initial dans lequel chercher les dossiers de séries.
    """

    def deplacer_fichiers(repertoire_source: Path, repertoire_destination: Path) -> None:
        """Déplace les fichiers du répertoire source vers le répertoire de destination."""
        try:
            for fichier in repertoire_source.iterdir():
                if fichier.is_file():
                    chemin_destination = repertoire_destination / fichier.name
                    if not chemin_destination.exists():
                        shutil.move(str(fichier), str(chemin_destination))
        except (OSError, shutil.Error) as e:
            logger.warning(f"Erreur lors du déplacement des fichiers: {e}")

    def traiter_sous_repertoires_series(repertoire_series: Path) -> None:
        """Traite les sous-répertoires des séries."""
        try:
            for repertoire_premier_niveau in repertoire_series.iterdir():
                if repertoire_premier_niveau.is_dir():
                    for s_rep in repertoire_premier_niveau.iterdir():
                        if s_rep.is_dir():
                            deplacer_fichiers(s_rep, repertoire_premier_niveau)
                            try:
                                s_rep.rmdir()
                            except OSError as e:
                                logger.warning(f"Impossible de supprimer {s_rep}: {e}")
        except OSError as e:
            logger.warning(f"Erreur lors du traitement des séries: {e}")

    try:
        for sous_repertoire in repertoire_initial.glob('**/Séries'):
            traiter_sous_repertoires_series(sous_repertoire)
    except OSError as e:
        logger.warning(f"Erreur lors de l'aplatissement de la structure des séries: {e}")


def rename_video(
    video: "Video",
    dic_serie: dict,
    sub: str = '',
    work_dir: Optional[Path] = None,
    dry_run: bool = False
) -> None:
    """
    Renomme et déplace la vidéo vers le répertoire de travail.

    Args:
        video: Objet Video à renommer.
        dic_serie: Dictionnaire des informations de titre de série.
        sub: Chemin du sous-répertoire.
        work_dir: Chemin du répertoire de travail.
        dry_run: Si True, simule uniquement l'opération.
    """
    if not work_dir:
        work_dir = video.destination_file.parent.parent / "work"

    all_path = work_dir / sub if sub else work_dir

    if video.is_serie():
        items_serie = dic_serie.get(video.title_fr, '')
        if items_serie:
            all_path = all_path.parent / items_serie[4].stem / f'{items_serie[0]} ({items_serie[1]})'
        else:
            all_path = all_path / f'{video.title_fr} ({video.date_film})'

    if dry_run:
        if video.is_not_doc():
            video.complete_path_temp_links = all_path / video.formatted_filename
        else:
            end_path = _safe_split_path(str(video.complete_path_original), video.type_file, video.complete_path_original.name)
            video.complete_path_temp_links = all_path / end_path.lstrip('/')

        logger.debug(f"SIMULATION - Déplacement: {video.destination_file} -> {video.complete_path_temp_links}")
        return

    logger.debug(f"Déplacement vers: {all_path}")

    try:
        if video.is_not_doc():
            video.complete_path_temp_links = all_path / video.formatted_filename
        else:
            end_path = _safe_split_path(str(video.complete_path_original), video.type_file, video.complete_path_original.name)
            video.complete_path_temp_links = all_path / end_path.lstrip('/')

        all_path.mkdir(parents=True, exist_ok=True)

        source = video.destination_file
        destination = video.complete_path_temp_links

        if source.exists():
            shutil.move(str(source), str(destination))
            logger.info(f"Vidéo déplacée: {destination}")
        else:
            logger.warning(f"Fichier source non trouvé: {source}")

    except (OSError, shutil.Error) as e:
        logger.error(f"Erreur lors du renommage de la vidéo: {e}")


def move_file_new_nas(
    video: "Video",
    storage_dir: Path,
    dry_run: bool = False,
    console: Optional[object] = None
) -> None:
    """
    Déplace le fichier vidéo vers le stockage NAS.

    Args:
        video: Objet Video à déplacer.
        storage_dir: Chemin du répertoire de stockage.
        dry_run: Si True, simule uniquement l'opération.
        console: Console optionnelle pour l'affichage.
    """
    origine = video.complete_path_original

    default_sub_dir = str(video.complete_path_temp_links) if video.complete_path_temp_links else ''
    sub_dir = _safe_split_path(str(video.complete_path_temp_links or ''), 'work/', default_sub_dir)

    destination = storage_dir / sub_dir

    if dry_run:
        if console:
            console.print(
                f"[dim]SIMULATION - Déplacement:[/dim] [yellow]{origine.name}[/yellow] -> [cyan]{destination}[/cyan]"
            )
        logger.info(f'SIMULATION - Transfert de {origine.name} vers {destination}')
        logger.debug(f'SIMULATION - Lien symbolique mis à jour: {video.complete_path_temp_links} -> {destination}')
        return

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if origine.exists():
            if destination.exists():
                logger.warning(f'Le fichier de destination existe déjà: {destination}')
                if origine.stat().st_size == destination.stat().st_size:
                    logger.info(f'Fichier identique détecté, suppression de la source: {origine}')
                    origine.unlink()
                else:
                    destination = ensure_unique_destination(destination)
                    shutil.move(str(origine), str(destination))
                    logger.info(f"Fichier déplacé (renommé): {destination}")
            else:
                shutil.move(str(origine), str(destination))
                logger.info(f"Fichier déplacé: {destination}")

            # Mise à jour du lien symbolique
            if video.complete_path_temp_links and video.complete_path_temp_links.exists():
                video.complete_path_temp_links.unlink()
            if video.complete_path_temp_links:
                video.complete_path_temp_links.parent.mkdir(parents=True, exist_ok=True)
                video.complete_path_temp_links.symlink_to(destination)
                logger.debug(f"Lien symbolique mis à jour: {video.complete_path_temp_links} -> {destination}")
        else:
            logger.warning(f"Fichier source non trouvé: {origine}")

    except (OSError, shutil.Error) as e:
        logger.error(f"Erreur lors du déplacement vers le NAS: {e}")


def cleanup_directories(*directories: Path) -> None:
    """
    Nettoie les répertoires temporaires.

    Args:
        *directories: Chemins des répertoires à nettoyer.
    """
    for directory in directories:
        if directory.exists() and any(directory.iterdir()):
            try:
                shutil.rmtree(directory, ignore_errors=True)
                logger.debug(f"Répertoire nettoyé: {directory}")
            except OSError as e:
                logger.warning(f"Impossible de nettoyer {directory}: {e}")


def cleanup_work_directory(work_dir: Path, console: Optional[object] = None) -> None:
    """
    Nettoie les structures récursives dans le répertoire de travail.

    Supprime les dossiers Saison imbriqués qui peuvent survenir suite à des erreurs de traitement.

    Args:
        work_dir: Répertoire de travail à nettoyer.
        console: Console optionnelle pour l'affichage.
    """
    if not work_dir.exists():
        return

    if console:
        console.print("[blue]🧹 Nettoyage préventif du répertoire de travail...[/blue]")

    def remove_nested_saisons(path: Path) -> int:
        """Supprime les dossiers Saison imbriqués de manière récursive."""
        removed = 0

        try:
            for item in list(path.iterdir()):
                if item.is_dir():
                    # Si c'est un dossier Saison qui contient un autre dossier Saison
                    if re.match(r'Saison \d{2}', item.name):
                        for sub_item in list(item.iterdir()):
                            if sub_item.is_dir() and re.match(r'Saison \d{2}', sub_item.name):
                                # Déplacer les fichiers du sous-dossier vers le dossier parent
                                for file in sub_item.iterdir():
                                    if file.is_file():
                                        new_path = item / file.name
                                        file.rename(new_path)
                                        logger.debug(f"Fichier déplacé: {file} -> {new_path}")

                                # Supprimer le dossier Saison imbriqué
                                shutil.rmtree(sub_item)
                                removed += 1
                                logger.info(f"Dossier Saison imbriqué supprimé: {sub_item}")

                    # Récursion
                    removed += remove_nested_saisons(item)
        except OSError as e:
            logger.warning(f"Erreur lors du nettoyage: {e}")

        return removed

    try:
        total_removed = remove_nested_saisons(work_dir)
        if total_removed > 0:
            logger.info(f"Total des dossiers Saison imbriqués supprimés: {total_removed}")
    except OSError as e:
        logger.warning(f"Erreur lors du nettoyage du répertoire de travail: {e}")


def handle_similar_file(
    new_file_path: Path,
    existing_file_path: Path,
    waiting_folder: Path,
    storage_dir: Path
) -> Optional[Path]:
    """
    Gère le cas où un fichier similaire est trouvé.

    Présente à l'utilisateur les options pour gérer le doublon potentiel.

    Args:
        new_file_path: Chemin du nouveau fichier.
        existing_file_path: Chemin du fichier existant similaire.
        waiting_folder: Dossier d'attente pour les fichiers en suspens.
        storage_dir: Répertoire de stockage principal.

    Returns:
        - existing_file_path si l'ancien fichier est conservé (le nouveau est déplacé)
        - new_file_path si le nouveau fichier est conservé (l'ancien est déplacé)
        - None si les deux fichiers sont conservés
    """
    _console.print(f"[yellow]⚠️  Un fichier similaire existe déjà :[/yellow]")
    _console.print(f"   [red]Existant:[/red] {'/'.join(existing_file_path.parts[-3:])}")
    _console.print(f"   [green]Nouveau:[/green] {new_file_path.name}")

    valid_choices = {"1", "2", "3"}
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            raw_input = input("""Que souhaitez-vous faire ?
    1: Garder l'ancien fichier (déplacer le nouveau vers attente)
    2: Remplacer par le nouveau (déplacer l'ancien vers attente)
    3: Conserver les deux
Votre choix (1/2/3): """)
            # Sanitisation: strip, limite à 10 caractères, prend le premier caractère
            choice = raw_input.strip()[:10]
            if choice and choice[0] in valid_choices:
                choice = choice[0]
                break
            _console.print(f"[red]Choix invalide. Veuillez entrer 1, 2 ou 3.[/red]")
        except (EOFError, KeyboardInterrupt):
            _console.print("\n[yellow]Interruption. Conservation des deux fichiers.[/yellow]")
            return None
    else:
        _console.print("[red]Trop de tentatives invalides. Conservation des deux fichiers par défaut.[/red]")
        return None

    match choice:
        case "1":
            _console.print(f"[blue]→ Déplacement du nouveau fichier vers l'attente[/blue]")
            try:
                # Déplacement vers le NAS puis création du symlink d'attente
                waiting_nas_file = storage_dir / 'waiting' / new_file_path.name
                waiting_nas_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(new_file_path), str(waiting_nas_file))
                create_symlink(waiting_nas_file, waiting_folder / new_file_path.name)
                logger.info(f"Fichier déplacé vers l'attente: {waiting_nas_file}")
            except (OSError, shutil.Error) as e:
                logger.error(f"Erreur lors du déplacement: {e}")
            return existing_file_path

        case "2":
            _console.print(f"[blue]→ Remplacement de l'ancien fichier[/blue]")
            try:
                # Déplacement de l'ancien vers l'attente
                waiting_nas_file = storage_dir / 'waiting' / existing_file_path.name
                waiting_nas_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(existing_file_path), str(waiting_nas_file))
                create_symlink(waiting_nas_file, waiting_folder / existing_file_path.name)
                logger.info(f"Ancien fichier déplacé vers l'attente: {waiting_nas_file}")
            except (OSError, shutil.Error) as e:
                logger.error(f"Erreur lors du déplacement de l'ancien fichier: {e}")
            return new_file_path

        case "3":
            _console.print("[blue]→ Conservation des deux fichiers[/blue]")
            return None

        case _:
            _console.print("[red]Choix non valide. Conservation des deux fichiers par défaut.[/red]")
            return None