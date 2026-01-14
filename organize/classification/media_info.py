"""Extraction des informations techniques MediaInfo pour les vidéos."""

import re
from typing import List, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from organize.models.video import Video


def _is_french(languages: List[str]) -> bool:
    """
    Vérifie si une langue de la liste indique le français.

    Args:
        languages: Liste de chaînes de langues à vérifier.

    Returns:
        True si le français est détecté dans l'une des chaînes.
    """
    return any(re.search(r'french', item.lower()) for item in languages)


def extract_media_info(video: "Video") -> str:
    """
    Extrait les spécifications techniques d'un fichier vidéo via MediaInfo.

    Extrait:
    - Informations de langue (FR, MULTi, VOSTFR, VO)
    - Codec vidéo
    - Résolution (2160p, 1080p, 720p, DVDRip, XviD)

    Args:
        video: Objet Video avec complete_path_original défini.

    Returns:
        Chaîne de specs formatée (ex: "MULTi x264 1080p").
        Retourne les specs existantes si déjà complètes ou en cas d'erreur.
    """
    # Si les specs existent et semblent complètes (3+ parties), les conserver
    if video.spec and len(video.spec.split()) >= 3:
        logger.debug(f"Specs existantes conservées: {video.spec}")
        return video.spec

    try:
        from pymediainfo import MediaInfo
        mi = MediaInfo.parse(video.complete_path_original)
    except Exception as e:
        logger.warning(f"Erreur MediaInfo pour {video.complete_path_original}: {e}")
        return video.spec  # Retourner les specs existantes en cas d'erreur

    if not mi.tracks:
        return video.spec

    nb_audio = mi.tracks[0].count_of_audio_streams
    if not nb_audio:
        return video.spec

    # Extraction des informations de langue
    try:
        languages = (
            mi.tracks[0].audio_language_list.lower().split(' / ')
            if mi.tracks[0].audio_language_list
            else ['french']
        )
    except Exception:
        languages = ['french']

    # Extraction des informations de sous-titres
    try:
        subtitles = (
            mi.tracks[0].text_language_list.lower().split(' / ')
            if mi.tracks[0].text_language_list
            else []
        )
    except Exception:
        subtitles = []

    # Extraction des informations de la piste vidéo
    if len(mi.tracks) > 1:
        width = mi.tracks[1].width or 0
        height = mi.tracks[1].height or 0
        codec = mi.tracks[1].format or ''
    else:
        width = height = 0
        codec = ''

    # Normalisation du nom du codec
    if 'AVC' in codec:
        codec = 'x264'

    spec = ''

    # Détermination du tag de langue
    if int(nb_audio) > 1:
        if _is_french(subtitles):
            if _is_french(languages):
                spec += 'MULTi '
            else:
                spec += 'VOSTFR '
        else:
            spec += 'MULTi '
    else:
        if _is_french(languages):
            spec += 'FR '
        elif _is_french(subtitles):
            spec += 'VOSTFR '
        else:
            spec += 'VO '

    spec += codec

    # Détermination de la résolution
    if width > 3800 or height > 2100:
        spec += ' 2160p'
    elif width > 1900 or height > 1000:
        spec += ' 1080p'
    elif width > 1200 or height > 700:
        spec += ' 720p'
    elif width > 700 or height > 500:
        spec += ' DVDRip'
    else:
        spec += ' XviD'

    return spec


def media_info(video: "Video") -> str:
    """Alias de compatibilité ascendante pour extract_media_info."""
    return extract_media_info(video)