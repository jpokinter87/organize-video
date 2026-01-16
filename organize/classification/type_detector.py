"""Video type detection and file information extraction."""

from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import guessit
from loguru import logger

from organize.config.settings import CATEGORIES

if TYPE_CHECKING:
    from organize.models.video import Video


def type_of_video(fichier: Path) -> str:
    """
    Determine video type based on its path.

    Args:
        fichier: Path to the video file.

    Returns:
        Category name if found in path, empty string otherwise.
    """
    return next((cat for cat in CATEGORIES if cat in fichier.parts), '')


def extract_file_infos(video: "Video") -> Tuple[str, int, str, int, int, str]:
    """
    Extract video file information using guessit.

    Args:
        video: Video object with complete_path_original set.

    Returns:
        Tuple of (title, year, season_episode_string, season, episode, spec).
        - title: Detected title from filename
        - year: Release year (0 if not found)
        - season_episode_string: Formatted 'S01E01' string or empty
        - season: Season number (0 if not found)
        - episode: Episode number (0 if not found)
        - spec: Combined language/codec/resolution spec
    """

    def which_lang(lang_info) -> str:
        return 'mul' if isinstance(lang_info, list) else getattr(lang_info, 'alpha3', 'fra')

    dict_lang = {
        "vostfr": "VOSTFR", "vostf": "VOSTFR", "vost": "VOSTFR", "multi": "MULTi",
        "fr en": "MULTi", "fr eng": "MULTi", "vff en": "MULTi", "vf en": "MULTi",
        "vff vo": "MULTi", "french": "FR", "fr ": "FR", "vff": "FR", "truefrench": "FR",
        "vfq": "FR", "vfi": "FR", "vf ": "FR", "vf2": "FR", "vo ": "VO", "fra": "FR",
        "subfrench": "VOSTFR", "mul": "MULTi"
    }

    dict_codec = {
        "h264": "x264", "x264": "x264", "h.264": "x264",
        "x265": "HEVC", "h265": "HEVC", "h.265": "HEVC",
        "av1": "AV1"
    }

    file = Path(video.complete_path_original.name).stem
    infos = guessit.guessit(file)

    title = infos.get('title', '').strip('-')
    year = infos.get('year', 0)
    season = infos.get('season', 0)
    episode = infos.get('episode', 0)
    season_episode = f'- S{season:02d}E{episode:02d} -' if season else ''

    # Traitement de la langue
    lang = ''
    lang_data = infos.get('language', '')
    if lang_data:
        lang = dict_lang.get(which_lang(lang_data).lower(), '')
    if infos.get('subtitle_language'):
        lang = 'VOSTFR'
    if 'multi' in file.lower():
        lang = "MULTi"

    # Traitement du codec
    video_codec = infos.get('video_codec', '')
    if isinstance(video_codec, list):
        video_codec = video_codec[0] if video_codec else ''
    codec = dict_codec.get(str(video_codec).lower(), '')
    if 'av1' in file.lower():
        codec = 'AV1'

    # Résolution
    resol = infos.get('screen_size', '')

    # Créer la chaîne de spécifications
    spec = ' '.join(filter(None, [lang, codec, resol]))
    spec = ' '.join(spec.split())

    if not title:
        logger.warning(f'No title detected for {video.complete_path_original.name}')

    return title, year, season_episode, season, episode, spec
