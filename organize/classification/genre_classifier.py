"""Genre classification functions for video files."""

from typing import TYPE_CHECKING, List, Tuple

from loguru import logger

from organize.config.settings import (
    SUPPORTED_GENRES,
    PRIORITY_GENRES,
    GENRE_MAPPING,
)

if TYPE_CHECKING:
    from organize.models.video import Video


def suggest_genre_mapping(unsupported_genres: List[str]) -> str:
    """
    Suggest a supported genre based on unsupported genres detected.

    Args:
        unsupported_genres: List of genre names not in SUPPORTED_GENRES.

    Returns:
        Suggested supported genre name, or empty string if no match.
    """
    if not unsupported_genres:
        return ""

    # Rechercher le premier genre mappé
    for genre in unsupported_genres:
        genre_lower = genre.lower()
        if genre_lower in GENRE_MAPPING:
            return GENRE_MAPPING[genre_lower]

        # Correspondance partielle pour les variations
        for unsupported, supported in GENRE_MAPPING.items():
            if unsupported in genre_lower or genre_lower in unsupported:
                return supported

    # Repli : les indicateurs narratifs suggèrent Drame
    narrative_indicators = ['drama', 'story', 'film', 'movie', 'drame', 'histoire']
    for genre in unsupported_genres:
        for indicator in narrative_indicators:
            if indicator in genre.lower():
                return 'Drame'

    return ""


def filter_supported_genres(detected_genres: List[str]) -> Tuple[List[str], List[str]]:
    """
    Filter genres into supported and unsupported categories.

    Args:
        detected_genres: List of detected genre names.

    Returns:
        Tuple of (valid_genres, unsupported_genres).
    """
    valid_genres = [g for g in detected_genres if g in SUPPORTED_GENRES]
    unsupported_genres = [g for g in detected_genres if g not in SUPPORTED_GENRES]
    return valid_genres, unsupported_genres


def classify_movie(video: "Video") -> "Video":
    """
    Automatically classify a video by selecting the first appropriate genre.

    Args:
        video: Video object with list_genres populated.

    Returns:
        Video object with genre field set.
    """
    if not video.list_genres:
        video.genre = 'Non détecté'
        return video

    # Conserver tel quel si déjà marqué comme non détecté
    if video.list_genres[0] == "Non détecté":
        video.genre = "Non détecté"
        return video

    video_genres = set(video.list_genres)

    # Traitement spécial pour l'animation
    if 'Animation' in video_genres:
        return classify_animation(video)

    # Combinaisons de genres spécifiques
    if {'Drame', 'Comédie'}.issubset(video_genres):
        video.genre = 'Comédie dramatique'
        return video

    # Sélection de genre prioritaire
    matching_genres = PRIORITY_GENRES.intersection(video_genres)
    if matching_genres:
        video.genre = next(iter(matching_genres))
        return video

    # Prendre le premier genre automatiquement
    video.genre = video.list_genres[0]
    return video


def classify_animation(video: "Video") -> "Video":
    """
    Specifically classify animation films.

    Args:
        video: Video object with Animation in list_genres.

    Returns:
        Video object with specific animation subgenre set.
    """
    if len(video.list_genres) == 1:
        video.genre = 'Animation/Adultes'
    elif 'Films pour enfants' in video.list_genres:
        video.genre = 'Animation/Animation Enfant'
    else:
        # Choix automatique basé sur les défauts
        video.genre = 'Animation/Animation Enfant'
        logger.debug(f"Genre animation automatiquement sélectionné : {video.genre}")

    video.list_genres = [video.genre if x == 'Animation' else x for x in video.list_genres]
    return video


def handle_unsupported_genres(video: "Video", detected_genres: List[str]) -> "Video":
    """
    Gère les genres non supportés en essayant de les mapper vers des genres supportés.

    Si tous les genres détectés sont non supportés, tente de suggérer un mapping
    automatique. Si aucun mapping n'est trouvé, marque le genre comme 'Non détecté'.

    Args:
        video: Objet Video à traiter.
        detected_genres: Liste des genres détectés par l'API.

    Returns:
        Objet Video avec list_genres mis à jour.
    """
    from organize.config import GENRE_UNDETECTED

    if not detected_genres:
        video.list_genres = [GENRE_UNDETECTED]
        return video

    valid_genres, unsupported_genres = filter_supported_genres(detected_genres)

    if valid_genres:
        # On a au moins un genre supporté
        video.list_genres = valid_genres
    elif unsupported_genres:
        # Tous les genres sont non supportés - essayer de mapper
        suggested = suggest_genre_mapping(unsupported_genres)
        if suggested:
            logger.debug(f"Genre non supporté '{unsupported_genres}' mappé vers '{suggested}'")
            video.list_genres = [suggested]
        else:
            logger.warning(f"Genres non supportés sans mapping : {unsupported_genres}")
            video.list_genres = [GENRE_UNDETECTED]
    else:
        video.list_genres = [GENRE_UNDETECTED]

    return video
