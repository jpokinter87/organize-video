"""Video classification and metadata extraction."""

from organize.classification.text_processing import (
    normalize,
    remove_article,
    normalize_accents,
)

__all__ = ["normalize", "remove_article", "normalize_accents"]
