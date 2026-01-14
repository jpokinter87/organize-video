"""MediaInfo extraction for video technical specs."""

import re
from typing import List, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from organize.models.video import Video


def _is_french(languages: List[str]) -> bool:
    """
    Check if any language in the list indicates French.

    Args:
        languages: List of language strings to check.

    Returns:
        True if French is detected in any language string.
    """
    return any(re.search(r'french', item.lower()) for item in languages)


def extract_media_info(video: "Video") -> str:
    """
    Extract technical specifications from a video file using MediaInfo.

    Extracts:
    - Language information (FR, MULTi, VOSTFR, VO)
    - Video codec
    - Resolution (2160p, 1080p, 720p, DVDRip, XviD)

    Args:
        video: Video object with complete_path_original set.

    Returns:
        Formatted spec string (e.g., "MULTi x264 1080p").
        Returns existing spec if already complete or on error.
    """
    # If specs exist and seem complete (3+ parts), keep them
    if video.spec and len(video.spec.split()) >= 3:
        logger.debug(f"Existing specs preserved: {video.spec}")
        return video.spec

    try:
        from pymediainfo import MediaInfo
        mi = MediaInfo.parse(video.complete_path_original)
    except Exception as e:
        logger.warning(f"MediaInfo error for {video.complete_path_original}: {e}")
        return video.spec  # Return existing specs on error

    if not mi.tracks:
        return video.spec

    nb_audio = mi.tracks[0].count_of_audio_streams
    if not nb_audio:
        return video.spec

    # Extract language information
    try:
        languages = (
            mi.tracks[0].audio_language_list.lower().split(' / ')
            if mi.tracks[0].audio_language_list
            else ['french']
        )
    except Exception:
        languages = ['french']

    # Extract subtitle information
    try:
        subtitles = (
            mi.tracks[0].text_language_list.lower().split(' / ')
            if mi.tracks[0].text_language_list
            else []
        )
    except Exception:
        subtitles = []

    # Extract video track information
    if len(mi.tracks) > 1:
        width = mi.tracks[1].width or 0
        height = mi.tracks[1].height or 0
        codec = mi.tracks[1].format or ''
    else:
        width = height = 0
        codec = ''

    # Normalize codec name
    if 'AVC' in codec:
        codec = 'x264'

    spec = ''

    # Determine language tag
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

    # Determine resolution
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


# Backward compatibility alias
def media_info(video: "Video") -> str:
    """Backward compatible alias for extract_media_info."""
    return extract_media_info(video)