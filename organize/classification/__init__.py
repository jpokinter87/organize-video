"""Video classification and metadata extraction."""

from organize.classification.text_processing import (
    normalize,
    remove_article,
    normalize_accents,
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

__all__ = [
    "normalize",
    "remove_article",
    "normalize_accents",
    "type_of_video",
    "extract_file_infos",
    "suggest_genre_mapping",
    "filter_supported_genres",
    "classify_movie",
    "classify_animation",
]
