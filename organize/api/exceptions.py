"""Exceptions personnalisées pour les erreurs API."""


class APIError(Exception):
    """Classe de base pour toutes les erreurs API."""

    pass


class APIConfigurationError(APIError):
    """Erreur de configuration API (clé manquante, invalide, etc.)."""

    pass


class APIConnectionError(APIError):
    """Erreur de connexion à l'API (réseau, timeout, etc.)."""

    pass


class APIResponseError(APIError):
    """Erreur dans la réponse de l'API (format invalide, données manquantes, etc.)."""

    pass
