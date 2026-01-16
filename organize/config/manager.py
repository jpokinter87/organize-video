"""Gestion de la configuration pour l'organisation de vidéos."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from organize.config.cli import CLIArgs, parse_arguments, args_to_cli_args
from organize.config.settings import CATEGORIES

# Imports des modules utilisés par les méthodes de validation
# Déplacés au niveau module pour clarifier les dépendances
from organize.api import validate_api_keys as check_api_keys, test_api_connectivity
from organize.filesystem import (
    get_available_categories,
    setup_working_directories as fs_setup_working_directories,
    count_videos,
    aplatir_repertoire_series,
)


@dataclass
class ValidationResult:
    """Résultat d'une validation de configuration."""

    valid: bool
    error_message: Optional[str] = None


class ConfigurationManager:
    """
    Gère la configuration et la validation de l'application.

    Centralise l'analyse des arguments, la validation et la configuration
    pour réduire le couplage dans le point d'entrée principal.
    """

    def __init__(self):
        """Initialise le gestionnaire de configuration."""
        self._cli_args: Optional[CLIArgs] = None
        self._console = None

    @property
    def cli_args(self) -> CLIArgs:
        """Retourne les arguments CLI analysés."""
        if self._cli_args is None:
            raise RuntimeError("Configuration not initialized. Call parse_args() first.")
        return self._cli_args

    def parse_args(self, args: Optional[list] = None) -> CLIArgs:
        """
        Analyse les arguments de ligne de commande.

        Arguments :
            args: Liste optionnelle d'arguments (défaut: sys.argv).

        Retourne :
            Instance CLIArgs analysée.
        """
        namespace = parse_arguments(args)
        self._cli_args = args_to_cli_args(namespace)
        return self._cli_args

    def setup_logging(self, debug: bool = False) -> None:
        """
        Configure la journalisation avec loguru.

        Arguments :
            debug: Active le niveau debug si True.
        """
        logger.remove()

        # File logging
        logger.add(
            "organize.log",
            rotation="100 MB",
            level="DEBUG" if debug else "INFO"
        )

        # Console logging
        logger.add(
            sys.stderr,
            level="DEBUG" if debug else "WARNING"
        )

    def validate_input_directory(self) -> ValidationResult:
        """
        Valide que le répertoire d'entrée existe.

        Retourne :
            ValidationResult avec statut et message d'erreur optionnel.
        """
        if not self.cli_args.search_dir.exists():
            return ValidationResult(
                valid=False,
                error_message=f"Input directory {self.cli_args.search_dir} does not exist"
            )
        return ValidationResult(valid=True)

    def validate_api_keys(self) -> ValidationResult:
        """
        Valide que les clés API sont présentes.

        Retourne :
            ValidationResult avec statut et message d'erreur optionnel.
        """
        if not check_api_keys():
            return ValidationResult(
                valid=False,
                error_message="Cles API manquantes (TMDB_API_KEY, TVDB_API_KEY)"
            )
        return ValidationResult(valid=True)

    def validate_api_connectivity(self) -> ValidationResult:
        """
        Valide la connectivité aux APIs.

        Retourne :
            ValidationResult avec statut et message d'erreur optionnel.
        """
        if not test_api_connectivity():
            return ValidationResult(
                valid=False,
                error_message="Impossible de se connecter aux APIs"
            )
        return ValidationResult(valid=True)

    def validate_categories(self) -> Tuple[ValidationResult, list]:
        """
        Valide la structure des catégories dans le répertoire de recherche.

        Retourne :
            Tuple (ValidationResult, liste des catégories disponibles).
        """
        available = get_available_categories(self.cli_args.search_dir)
        if not available:
            return (
                ValidationResult(
                    valid=False,
                    error_message=f"Aucune categorie trouvee dans {self.cli_args.search_dir}. "
                                  f"Categories attendues: {', '.join(CATEGORIES)}"
                ),
                []
            )
        return ValidationResult(valid=True), available

    def validate_all(self) -> ValidationResult:
        """
        Exécute toutes les validations.

        Retourne :
            ValidationResult avec le premier échec ou succès.
        """
        validations = [
            self.validate_input_directory,
            self.validate_api_keys,
            self.validate_api_connectivity,
        ]

        for validation in validations:
            result = validation()
            if not result.valid:
                return result

        cat_result, _ = self.validate_categories()
        return cat_result

    def setup_working_directories(self) -> Tuple[Path, Path, Path, Path]:
        """
        Configure les répertoires de travail pour le traitement.

        Retourne :
            Tuple (work_dir, temp_dir, original_dir, waiting_folder).
        """
        return fs_setup_working_directories(
            self.cli_args.output_dir,
            self.cli_args.dry_run
        )

    def get_video_count(self) -> int:
        """
        Compte les vidéos dans le répertoire de recherche.

        Retourne :
            Nombre de vidéos trouvées.
        """
        return count_videos(self.cli_args.search_dir)

    def flatten_series_directories(self) -> None:
        """Aplatit les répertoires de séries si pas en mode simulation."""
        if not self.cli_args.dry_run:
            aplatir_repertoire_series(self.cli_args.search_dir)
