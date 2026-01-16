"""Validation des APIs et test de connectivité."""

import os
from typing import Optional

from loguru import logger

from organize.api.tmdb_client import TmdbClient
from organize.ui.console import ConsoleUI


def get_api_key(key_name: str) -> Optional[str]:
    """
    Récupère une clé API depuis les variables d'environnement.

    Args:
        key_name: Nom de la variable d'environnement.

    Returns:
        La valeur de la clé API ou None si non définie.
    """
    return os.getenv(key_name)


def validate_api_keys(
    console: Optional[ConsoleUI] = None
) -> bool:
    """
    Valide la présence des clés API requises.

    Vérifie TMDB_API_KEY et TVDB_API_KEY dans les variables d'environnement.

    Args:
        console: ConsoleUI optionnelle pour l'affichage des messages.

    Returns:
        True si toutes les clés requises sont présentes, False sinon.
    """
    missing_keys = []

    tmdb_key = get_api_key("TMDB_API_KEY")
    tvdb_key = get_api_key("TVDB_API_KEY")

    if not tmdb_key:
        missing_keys.append("TMDB_API_KEY")
    if not tvdb_key:
        missing_keys.append("TVDB_API_KEY")

    if missing_keys:
        logger.error(f"Clés API manquantes: {', '.join(missing_keys)}")
        if console:
            console.print_error(f"Clés API manquantes: {', '.join(missing_keys)}")
            console.print_warning("Veuillez les ajouter dans le fichier .env")
        return False

    return True


def test_api_connectivity(
    console: Optional[ConsoleUI] = None,
    tmdb_api_key: Optional[str] = None,
    tvdb_api_key: Optional[str] = None
) -> bool:
    """
    Teste la connectivité aux APIs TMDB et TVDB.

    Args:
        console: ConsoleUI optionnelle pour l'affichage des messages.
        tmdb_api_key: Clé API TMDB (utilise la variable d'env si non fournie).
        tvdb_api_key: Clé API TVDB (utilise la variable d'env si non fournie).

    Returns:
        True si toutes les connexions API réussissent, False sinon.
    """
    if console:
        console.print_info("Test de connectivité aux APIs...")

    # Récupérer les clés API depuis l'environnement si non fournies
    tmdb_key = tmdb_api_key or get_api_key("TMDB_API_KEY")
    tvdb_key = tvdb_api_key or get_api_key("TVDB_API_KEY")

    # Test TMDB
    tmdb = TmdbClient(api_key=tmdb_key)
    test_result = tmdb.find_content("test", "Films")

    if test_result is None:
        logger.error("Impossible de se connecter à l'API TMDB")
        if console:
            console.print_error("Connexion TMDB échouée")
        return False

    if console:
        console.print_success("Connexion TMDB réussie")

    # Test TVDB (optionnel - utilisé uniquement pour les titres d'épisodes)
    if tvdb_key:
        try:
            import tvdb_api
            from tvdb_api import TvdbError

            tvdb_test = tvdb_api.Tvdb(
                apikey=tvdb_key,
                language='fr',
                interactive=False
            )
            # Test simple - essayer d'accéder à l'API
            # En cas d'échec, TVDB affichera un avertissement mais ne stoppera pas le traitement
            if console:
                console.print_success("Connexion TVDB réussie")

        except TvdbError as e:
            # Erreur spécifique à TVDB (API key invalide, limite de requêtes, etc.)
            logger.warning(f"Erreur API TVDB: {e}")
            if console:
                console.print_warning(f"Erreur API TVDB: {e}")
                console.print_info("Les titres d'épisodes ne seront pas disponibles")
            # Ne pas retourner False - TVDB est optionnel

        except (ConnectionError, TimeoutError) as e:
            # Erreurs réseau
            logger.warning(f"Erreur réseau TVDB: {e}")
            if console:
                console.print_warning(f"Connexion TVDB impossible (réseau): {e}")
                console.print_info("Les titres d'épisodes ne seront pas disponibles")
            # Ne pas retourner False - TVDB est optionnel

        except ImportError as e:
            # Module tvdb_api non installé
            logger.warning(f"Module tvdb_api non disponible: {e}")
            if console:
                console.print_warning("Module tvdb_api non installé")
            # Ne pas retourner False - TVDB est optionnel

    return True


def ensure_api_ready(
    console: Optional[ConsoleUI] = None
) -> bool:
    """
    S'assure que les APIs sont configurées et accessibles.

    Combine la validation et le test de connectivité.

    Args:
        console: ConsoleUI optionnelle pour l'affichage des messages.

    Returns:
        True si les APIs sont prêtes à être utilisées, False sinon.
    """
    if not validate_api_keys(console):
        return False

    if not test_api_connectivity(console):
        return False

    return True