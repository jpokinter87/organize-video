"""Video classification and metadata extraction."""

from organize.classification.text_processing import (
    normalize,
    remove_article,
    normalize_accents,
    extract_title_from_filename,
    format_undetected_filename,
)
from organize.classification.type_detector import (
    type_of_video,
    extract_file_infos,
)
from organize.classification.genre_classifier import (
    suggest_genre_mapping,
    filter_supported_genres,
    classify_movie,
    classify_animation,
)
from organize.classification.media_info import (
    extract_media_info,
    media_info,
)

__all__ = [
    "normalize",
    "remove_article",
    "normalize_accents",
    "extract_title_from_filename",
    "format_undetected_filename",
    "type_of_video",
    "extract_file_infos",
    "suggest_genre_mapping",
    "filter_supported_genres",
    "classify_movie",
    "classify_animation",
    "extract_media_info",
    "media_info",
]
