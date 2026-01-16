"""Fonctions interactives pour la saisie utilisateur et la visualisation."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

from loguru import logger
from rich.panel import Panel
from rich.columns import Columns

from organize.ui.console import console
from organize.ui.confirmations import (
    ConfirmationResult,
    parse_user_response,
    get_available_genres,
)
from organize.config import FILMANIM, VIDEO_PLAYERS, GENRE_UNDETECTED


def launch_video_player(video_path: Path) -> bool:
    """
    Lance le lecteur vidéo par défaut pour visualiser le fichier.

    Détecte automatiquement le système d'exploitation et trouve
    le lecteur vidéo disponible.

    Args:
        video_path: Chemin vers le fichier vidéo à lire.

    Returns:
        True si le lancement réussit, False sinon.
    """
    try:
        # Détection du système et des lecteurs disponibles
        video_players = []

        if sys.platform.startswith('linux'):
            potential_players = VIDEO_PLAYERS.get('linux', ['xdg-open'])
        elif sys.platform == 'darwin':
            potential_players = VIDEO_PLAYERS.get('darwin', ['open'])
        elif sys.platform.startswith('win'):
            potential_players = VIDEO_PLAYERS.get('windows', ['start'])
        else:
            potential_players = VIDEO_PLAYERS.get('linux', ['xdg-open'])

        # Chercher le premier lecteur disponible
        for player in potential_players:
            if shutil.which(player):
                video_players.append(player)

        if not video_players:
            console.print("[red]Aucun lecteur vidéo trouvé[/red]")
            console.print("[dim]Lecteurs supportés: VLC, MPV, MPlayer, etc.[/dim]")
            return False

        # Lancer avec le premier lecteur disponible
        player = video_players[0]
        console.print(f"[blue]Lancement de {player} pour visualiser le fichier...[/blue]")

        if sys.platform.startswith('win') and player == 'start':
            # Utiliser os.startfile() au lieu de shell=True pour éviter l'injection shell
            os.startfile(str(video_path))
        elif sys.platform == 'darwin' and player == 'open':
            subprocess.Popen(['open', str(video_path)])
        else:
            subprocess.Popen(
                [player, str(video_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        console.print("[green]Lecteur vidéo lancé[/green]")
        console.print("[dim]Appuyez sur une touche pour continuer après avoir visionné...[/dim]")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du lancement du lecteur vidéo: {e}")
        return False


def wait_for_user_after_viewing() -> None:
    """Attend que l'utilisateur confirme avoir terminé le visionnage."""
    console.print("\n[bold yellow]Visionnage en cours...[/bold yellow]")
    input("[dim]Appuyez sur Entrée quand vous avez terminé le visionnage[/dim]")
    console.print("[green]Visionnage terminé[/green]")


def choose_genre_manually(video_type: str) -> str:
    """
    Permet à l'utilisateur de choisir manuellement un genre.

    Affiche une liste de genres disponibles et attend la sélection
    de l'utilisateur par numéro ou par nom.

    Args:
        video_type: Type de vidéo ('Films', 'Animation', etc.).

    Returns:
        Genre sélectionné ou chaîne vide si annulé.
    """
    # Pour les séries, pas de genre nécessaire
    if video_type not in FILMANIM:
        return ""

    available_genres = get_available_genres()

    console.print("\n[bold cyan]Sélection du genre :[/bold cyan]")

    # Affichage en colonnes
    genre_panels = []
    for i, genre in enumerate(available_genres, 1):
        color = "green" if genre != GENRE_UNDETECTED else "yellow"
        genre_panels.append(Panel(f"[{color}]{i:2d}. {genre}[/{color}]", expand=False))

    console.print(Columns(genre_panels, equal=False, expand=False))

    while True:
        try:
            choice = input(f"\n➤ Choisissez un genre (1-{len(available_genres)}, ou nom du genre) : ").strip()

            if not choice:
                console.print("[yellow]Aucun choix, veuillez sélectionner un genre[/yellow]")
                continue

            # Choix par numéro
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(available_genres):
                    selected = available_genres[num - 1]
                    console.print(f"[green]Genre sélectionné : {selected}[/green]")
                    return selected
                else:
                    console.print(f"[red]Numéro invalide. Choisissez entre 1 et {len(available_genres)}[/red]")
                    continue

            # Choix par nom (recherche floue)
            choice_lower = choice.lower()
            for genre in available_genres:
                if choice_lower in genre.lower() or genre.lower().startswith(choice_lower):
                    console.print(f"[green]Genre sélectionné : {genre}[/green]")
                    return genre

            console.print(f"[red]Genre '{choice}' non trouvé. Utilisez le numéro ou le nom exact[/red]")

        except (ValueError, KeyboardInterrupt):
            console.print("\n[yellow]Sélection annulée[/yellow]")
            return ""
        except Exception as e:
            logger.warning(f"Erreur lors de la sélection du genre : {e}")
            return ""


def user_confirms_match(
    complete_name: str,
    tmp_name: str,
    found_date: int,
    tmp_list_genre: List[str],
    type_video: str,
    video_file_path: Optional[Path] = None
) -> Union[bool, str]:
    """
    Demande à l'utilisateur de confirmer une correspondance trouvée.

    Affiche les informations du fichier original et de la correspondance
    trouvée, puis attend la réponse de l'utilisateur.

    Args:
        complete_name: Nom complet du fichier original.
        tmp_name: Titre trouvé dans la base de données.
        found_date: Année de sortie trouvée.
        tmp_list_genre: Liste des genres trouvés.
        type_video: Type de vidéo ('Films', 'Séries', etc.).
        video_file_path: Chemin vers le fichier pour visualisation.

    Returns:
        True si accepté, False si refusé, ou str avec le titre manuel.
    """
    console.rule("[bold blue]Vérification de correspondance[/bold blue]")

    # Fichier original
    console.print(Panel(
        f"[yellow]{complete_name}[/yellow]",
        title="Fichier original",
        border_style="yellow"
    ))

    # Correspondance trouvée
    genres_str = ", ".join(tmp_list_genre) if tmp_list_genre else "Aucun genre"

    # Détermination du type pour l'affichage
    if type_video in FILMANIM:
        type_label = "Film" if type_video == "Films" else "Film d'animation"
    else:
        type_label = "Série"

    console.print(Panel(
        f"[cyan]Type :[/cyan] [bold]{type_label}[/bold]\n"
        f"[green]Titre :[/green] [bold]{tmp_name}[/bold]\n"
        f"[blue]Année :[/blue] [bold]{found_date if found_date else 'N/A'}[/bold]\n"
        f"[purple]Genres :[/purple] [italic]{genres_str}[/italic]",
        title="Correspondance trouvée",
        border_style="green"
    ))

    # Options de choix
    console.print("\n[bold cyan]Cette correspondance est-elle correcte ?[/bold cyan]")

    options_text = (
        "[bold green]Entrée[/bold green] = [green]ACCEPTER[/green]\n"
        "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow]\n"
    )

    if video_file_path and video_file_path.exists():
        options_text += "[bold magenta]v[/bold magenta] = [magenta]VISIONNER[/magenta]\n"

    options_text += "[bold red]n[/bold red] = [red]NON[/red] (chercher le suivant)"

    console.print(Panel.fit(options_text, title="Options disponibles", border_style="cyan"))

    while True:
        try:
            response = input("➤ Votre choix : ").strip().lower()
            result = parse_user_response(response)

            if result == ConfirmationResult.ACCEPT:
                console.print("[green]Correspondance acceptée[/green]")
                console.rule()
                return True

            elif result == ConfirmationResult.MANUAL:
                console.print("\n[bold yellow]MODE SAISIE MANUELLE[/bold yellow]")
                console.print("[dim]Tapez 'cancel' pour annuler et revenir aux suggestions[/dim]")

                while True:
                    manual_title = input("➤ Titre exact du film/série : ").strip()

                    if manual_title.lower() == 'cancel':
                        console.print("[yellow]Retour aux suggestions automatiques[/yellow]")
                        break
                    elif manual_title:
                        console.print(f"[green]Titre manuel accepté : '{manual_title}'[/green]")
                        console.rule()
                        return manual_title
                    else:
                        console.print("[red]Veuillez saisir un titre valide ou 'cancel'[/red]")

                console.print(f"\n[bold cyan]Correspondance pour '{tmp_name}' ?[/bold cyan]")
                console.print("[dim]Entrée=accepter | m=manuel | v=visionner | n=non[/dim]")
                continue

            elif result == ConfirmationResult.VIEW:
                if not video_file_path or not video_file_path.exists():
                    console.print("[red]Fichier vidéo non accessible pour la visualisation[/red]")
                    continue

                if launch_video_player(video_file_path):
                    wait_for_user_after_viewing()

                    console.print(f"\n[bold cyan]Après visionnage, '{tmp_name}' correspond-il ?[/bold cyan]")
                    console.print(Panel.fit(
                        "[bold green]Entrée[/bold green] = [green]ACCEPTER[/green]\n"
                        "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow]\n"
                        "[bold red]n[/bold red] = [red]NON[/red]",
                        title="Après visionnage",
                        border_style="cyan"
                    ))
                    continue
                else:
                    console.print("[yellow]Échec du lancement du lecteur, retour aux options...[/yellow]")
                    continue

            elif result == ConfirmationResult.REJECT:
                console.print("[red]Correspondance refusée - Recherche du suivant[/red]")
                console.rule()
                return False

            else:
                console.print(f"[yellow]Réponse '{response}' non reconnue[/yellow]")
                console.print("[dim]Options valides : Entrée, m, v, n[/dim]")
                continue

        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Interruption par l'utilisateur[/red]")
            console.rule()
            return False
        except Exception as e:
            logger.warning(f"Erreur lors de la saisie : {e}")
            console.print("[red]Erreur de saisie, veuillez réessayer[/red]")
            continue


def handle_not_found_error(
    name: str,
    full_name: str,
    date: int,
    no_date: bool,
    video_type: str,
    video_file_path: Optional[Path],
    occurrence: int,
    query_callback
) -> Tuple[str, List[str], int]:
    """
    Gère les cas où aucun résultat n'est trouvé avec options utilisateur.

    Args:
        name: Nom recherché.
        full_name: Nom complet du fichier original.
        date: Année du film.
        no_date: Si True, ignorer la correspondance de date.
        video_type: Type de vidéo.
        video_file_path: Chemin vers le fichier vidéo.
        occurrence: Numéro de tentative actuel.
        query_callback: Fonction de rappel pour relancer la recherche.

    Returns:
        Tuple (titre, genres, année) ou ('', [], date) si ignoré.
    """
    from organize.classification.text_processing import extract_title_from_filename

    if occurrence < 4:
        console.print(f"\n[bold red]'{name}' n'a pas été trouvé dans la base[/bold red]")
        console.print(f"[yellow]Fichier original :[/yellow] [dim]{full_name}[/dim]")
        console.print(f"[yellow]Tentative {occurrence}/3[/yellow]")

        # Options étendues
        console.print("\n[bold cyan]Que souhaitez-vous faire ?[/bold cyan]")

        options_text = (
            "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow] du titre\n"
            "[bold blue]k[/bold blue] = [blue]GARDER LE NOM[/blue] et choisir le genre\n"
        )

        if video_file_path and video_file_path.exists():
            options_text += "[bold magenta]v[/bold magenta] = [magenta]VISIONNER[/magenta] le fichier\n"

        options_text += (
            "[bold red]s[/bold red] = [red]SKIP[/red] (ignorer ce fichier)\n"
            "[bold dim]r[/bold dim] = [dim]RETRY[/dim] avec le même titre"
        )

        console.print(Panel.fit(options_text, title="Options disponibles", border_style="cyan"))

        while True:
            try:
                response = input("➤ Votre choix : ").strip().lower()

                if response in ('m', 'manual', 'manuel'):
                    console.print("\n[bold yellow]SAISIE MANUELLE[/bold yellow]")
                    console.print("[dim]Tapez 'cancel' pour annuler, 'skip' pour ignorer[/dim]")

                    while True:
                        new_name = input('➤ Titre exact du film/série : ').strip()

                        if new_name.lower() == 'cancel':
                            console.print("[yellow]Retour aux options[/yellow]")
                            break
                        elif new_name.lower() == 'skip':
                            logger.info(f"Fichier ignoré par l'utilisateur : {full_name}")
                            return '', [], date
                        elif new_name:
                            console.print(f"[green]Nouvelle recherche avec : '{new_name}'[/green]")
                            return query_callback(
                                new_name, date, no_date, full_name,
                                video_type, video_file_path, occurrence + 1
                            )
                        else:
                            console.print("[red]Veuillez saisir un titre valide, 'cancel' ou 'skip'[/red]")

                    console.print(f"\n[bold cyan]'{name}' non trouvé - Que faire ?[/bold cyan]")
                    console.print("[dim]m=manuel | v=visionner | s=skip | r=retry[/dim]")
                    continue

                elif response in ('k', 'keep', 'garder'):
                    console.print("\n[bold blue]CONSERVATION DU NOM ORIGINAL[/bold blue]")

                    file_stem = Path(full_name).stem
                    clean_title = extract_title_from_filename(file_stem)

                    console.print(f"[green]Titre extrait :[/green] [bold]{clean_title['title']}[/bold]")
                    if clean_title['year']:
                        console.print(f"[blue]Année détectée :[/blue] [bold]{clean_title['year']}[/bold]")

                    title_ok = input(
                        f"➤ Confirmer le titre '{clean_title['title']}' ? (Entrée=oui, autre=modifier) : "
                    ).strip()

                    if title_ok:
                        clean_title['title'] = input("➤ Nouveau titre : ").strip()
                        if not clean_title['title']:
                            console.print("[red]Titre obligatoire, retour aux options[/red]")
                            continue

                    if not clean_title['year']:
                        year_input = input("➤ Année du film (optionnel) : ").strip()
                        if year_input and year_input.isdigit():
                            clean_title['year'] = int(year_input)

                    selected_genre = choose_genre_manually(video_type)
                    if not selected_genre:
                        console.print("[yellow]Aucun genre sélectionné, retour aux options[/yellow]")
                        continue

                    console.print(f"[green]Fichier conservé avec le genre '{selected_genre}'[/green]")
                    return clean_title['title'], [selected_genre], clean_title['year'] or date

                elif response in ('v', 'view', 'visionner'):
                    if not video_file_path or not video_file_path.exists():
                        console.print("[red]Fichier vidéo non accessible pour la visualisation[/red]")
                        continue

                    if launch_video_player(video_file_path):
                        wait_for_user_after_viewing()

                        console.print(f"\n[bold cyan]Après visionnage, quel est le titre ?[/bold cyan]")
                        manual_title = input("➤ Titre exact (ou 'skip' pour ignorer) : ").strip()

                        if manual_title.lower() == 'skip' or not manual_title:
                            return '', [], date
                        else:
                            return query_callback(
                                manual_title, date, no_date, full_name,
                                video_type, video_file_path, occurrence + 1
                            )
                    else:
                        console.print("[yellow]Échec du lancement, retour aux options...[/yellow]")
                        continue

                elif response in ('s', 'skip'):
                    console.print("[red]Fichier ignoré[/red]")
                    logger.info(f"Fichier ignoré par l'utilisateur : {full_name}")
                    return '', [], date

                elif response in ('r', 'retry', ''):
                    console.print("[dim]Nouvelle tentative avec le même titre[/dim]")
                    return query_callback(
                        name, date, no_date, full_name,
                        video_type, video_file_path, occurrence + 1
                    )

                else:
                    console.print(f"[yellow]Réponse '{response}' non reconnue[/yellow]")
                    console.print("[dim]Options valides : m, k, v, s, r[/dim]")
                    continue

            except (KeyboardInterrupt, EOFError):
                console.print("\n[red]Interruption par l'utilisateur[/red]")
                return '', [], date
            except Exception as e:
                logger.warning(f"Erreur lors de la saisie : {e}")
                return '', [], date

    # Après 3 tentatives
    console.print(f"[red]Impossible d'identifier '{name}' après 3 tentatives[/red]")
    console.print(f"[yellow]Le fichier sera placé dans 'non détectés'[/yellow]")
    return '', [], date
