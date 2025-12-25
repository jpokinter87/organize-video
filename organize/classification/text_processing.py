"""Text processing utilities for video titles and filenames."""

import unicodedata
from typing import List


# French and English articles to remove from titles
ARTICLES: List[str] = [
    "L'", "Les ", "Le ", "La ", "Une ", "Un ", "Des ", "De l'",
    "De la ", "De ", "Du ", "D'un ", "D'une ", "A la ", "A l'",
    "À la ", "À l'", "Au ", "Aux ", "The ", "A ", "L ", "An "
]

# Accent mappings for normalization
ACCENT_MAP = {
    'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
    'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
    'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
    'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
    'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
    'ý': 'y', 'ÿ': 'y',
    'ç': 'c', 'ñ': 'n',
    'œ': 'oe', 'æ': 'ae'
}


def normalize_accents(text: str) -> str:
    """
    Normalize accented characters for alphabetical sorting.

    Args:
        text: Input string that may contain accented characters.

    Returns:
        String with accents removed and ligatures expanded.

    Examples:
        >>> normalize_accents("café")
        'cafe'
        >>> normalize_accents("cœur")
        'coeur'
    """
    if not text:
        return ""

    # Apply manual accent mappings
    for accented, normal in ACCENT_MAP.items():
        text = text.replace(accented, normal)
        text = text.replace(accented.upper(), normal.upper())

    # Unicode normalization for any remaining cases
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    return text


def normalize(string: str) -> str:
    """
    Normalize a string by handling special characters and formatting.

    This function:
    - Replaces œ and æ ligatures
    - Removes spaces before periods
    - Replaces : with comma-space
    - Replaces ? with ellipsis
    - Replaces / with dash
    - Reduces multiple spaces to single
    - Strips leading/trailing whitespace

    Args:
        string: Input string to normalize.

    Returns:
        Normalized string suitable for filenames.

    Examples:
        >>> normalize("Title: Subtitle")
        'Title, Subtitle'
        >>> normalize("What?")
        'What...'
    """
    if not string:
        return ""

    result = string

    # Handle ligatures (œ and æ)
    if 'œ' in string or 'æ' in string:
        translate = {'œ': 'o', 'æ': 'a'}
        result = ''.join(translate.get(char, char) for char in string)

    # Character replacements for filename safety
    result = result.replace(" .", ".")
    result = result.replace(':', ', ').replace('?', '...').replace('/', ' - ')
    result = result.replace(' , ', ', ').replace('  ', ' ')

    return result.strip()


def remove_article(title: str) -> str:
    """
    Remove leading articles from a title and normalize for sorting.

    Removes French and English articles (Le, La, Les, The, A, etc.)
    from the beginning of a title, then normalizes accents.

    Args:
        title: Movie or series title that may start with an article.

    Returns:
        Title without leading article, with accents normalized,
        suitable for alphabetical sorting.

    Examples:
        >>> remove_article("The Matrix")
        'matrix'
        >>> remove_article("Les Misérables")
        'miserables'
    """
    if not title:
        return ""

    title = title.strip()
    seg_f = title[:6]  # Check only first 6 characters for efficiency

    for article in ARTICLES:
        if article in seg_f and title.startswith(article):
            title = title[len(article):]
            break

    # Normalize accents after article removal
    title = normalize_accents(title)
    return normalize(title).strip()
