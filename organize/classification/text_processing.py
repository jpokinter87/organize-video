"""Utilitaires de traitement de texte pour les titres et noms de fichiers vidéo."""

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from guessit import guessit

if TYPE_CHECKING:
    from organize.models.video import Video


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

    # Gestion des ligatures (œ et æ)
    if 'œ' in string or 'æ' in string:
        translate = {'œ': 'o', 'æ': 'a'}
        result = ''.join(translate.get(char, char) for char in string)

    # Remplacements de caractères pour la sécurité des noms de fichiers
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
    seg_f = title[:6]  # Vérifier seulement les 6 premiers caractères pour l'efficacité

    for article in ARTICLES:
        if article in seg_f and title.startswith(article):
            title = title[len(article):]
            break

    # Normalize accents after article removal
    title = normalize_accents(title)
    return normalize(title).strip()


def extract_title_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extrait le titre et l'année d'un nom de fichier en nettoyant les specs techniques.

    Utilise guessit pour une extraction intelligente, avec fallback manuel.

    Args:
        filename: Nom de fichier (sans extension) à analyser.

    Returns:
        Dictionnaire avec les clés 'title' et 'year'.

    Examples:
        >>> extract_title_from_filename("The.Matrix.1999.MULTi.1080p.BluRay")
        {'title': 'The Matrix', 'year': 1999}
    """
    # Utiliser guessit pour une extraction intelligente
    info = guessit(filename)

    # Récupération du titre
    title = info.get('title', '')
    year = info.get('year', None)

    # Si guessit n'a pas trouvé de titre, extraction manuelle
    if not title:
        # Patterns techniques à supprimer
        tech_patterns = [
            r'\b\d{4}\b',  # Années
            r'\b(MULTI|MULTi|VF|VOSTFR|FR|VO|FRENCH|TRUEFRENCH)\b',  # Langues
            r'\b(x264|x265|HEVC|H264|H265|AV1)\b',  # Codecs
            r'\b(1080p|720p|480p|2160p|4K|UHD)\b',  # Résolutions
            r'\b(WEB|BluRay|BDRip|DVDRip|WEBRip|HDTV|WEB-DL)\b',  # Sources
            r'\b(AC3|DTS|AAC|MP3|DD|DDPlus|Atmos)\b',  # Audio
            r'\b(5\.1|7\.1|2\.0)\b',  # Canaux audio
            r'-[A-Z0-9]+$',  # Tags de release
        ]

        cleaned = filename
        for pattern in tech_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        # Nettoyage des séparateurs
        cleaned = re.sub(r'[._-]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Extraction de l'année si présente
        year_match = re.search(r'\b(19|20)\d{2}\b', filename)
        if year_match and not year:
            year = int(year_match.group())
            # Supprimer l'année du titre nettoyé
            cleaned = re.sub(r'\b' + str(year) + r'\b', '', cleaned).strip()

        title = cleaned.title() if cleaned else filename

    # Nettoyage final du titre
    title = normalize(title)

    return {
        'title': title,
        'year': year
    }


def format_undetected_filename(video: "Video") -> str:
    """
    Formate le nom de fichier pour les vidéos non détectées.

    Extrait et nettoie le titre depuis le nom de fichier original,
    identifie les specs techniques, et génère un nom formaté.

    Args:
        video: Objet Video avec complete_path_original défini.

    Returns:
        Nom de fichier formaté avec extension.

    Examples:
        >>> # Pour un fichier "The.Amateur.2025.MULTi.1080p.mkv"
        >>> # Retourne: "The Amateur (2025) MULTi x264 1080p.mkv"
    """
    # Extraction du titre à partir du nom de fichier original
    original_name = video.complete_path_original.stem

    # Patterns de nettoyage complets et précis
    patterns_to_remove = [
        # Années
        r'\b\d{4}\b',

        # Langues et sous-titres
        r'\bMULTI\b', r'\bMULTi\b', r'\bVFQ\b', r'\bVF\d*\b', r'\bVOSTFR\b',
        r'\bFR\b', r'\bVO\b', r'\bFRENCH\b', r'\bTRUEFRENCH\b',

        # Codecs vidéo
        r'\bx264\b', r'\bx265\b', r'\bHEVC\b', r'\bH264\b', r'\bH265\b', r'\bAV1\b',

        # Résolutions
        r'\b1080p\b', r'\b720p\b', r'\b480p\b', r'\b2160p\b',

        # Sources
        r'\bWEB\b', r'\bWEBRip\b', r'\bWEB-DL\b', r'\bBluRay\b', r'\bBDRip\b',
        r'\bDVDRip\b', r'\bHDRip\b', r'\bTVRip\b',

        # Audio
        r'\bAC3\b', r'\bDTS\b', r'\bAAC\b', r'\bMP3\b', r'\bDD5\.1\b', r'\bDD\b',
        r'\b5\.1\b', r'\b7\.1\b', r'\bDolby\b', r'\bAtmos\b',

        # Caractéristiques techniques
        r'\b10Bit\b', r'\b8Bit\b', r'\bHDR\b', r'\bSDR\b', r'\bDL\b', r'\bAD\b',

        # Formats conteneurs
        r'\bMkv\b', r'\bAvi\b', r'\bMp4\b',

        # Tags de release et groupes (à la fin)
        r'-[A-Z0-9]+$', r'\b[A-Z0-9]{4,}$',

        # Patterns spécifiques problématiques
        r'\bSlay3R\b', r'\bSHADOW\b', r'\bTyHD\b',

        # Parenthèses vides
        r'\(\s*\)',
    ]

    cleaned_title = original_name

    # Application des patterns de nettoyage
    for pattern in patterns_to_remove:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)

    # Nettoyage des séparateurs multiples et caractères résiduels
    cleaned_title = re.sub(r'[.\-_]+', ' ', cleaned_title)
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title)
    cleaned_title = cleaned_title.strip()

    # Nettoyage supplémentaire des mots isolés problématiques
    problematic_words = ['vfq', 'mkv', 'avi', 'mp4', 'dd5', '10bit', '1', 'slay3r']
    words = cleaned_title.split()
    cleaned_words = [word for word in words if word.lower() not in problematic_words]
    cleaned_title = ' '.join(cleaned_words)

    # Capitalisation du titre
    cleaned_title = cleaned_title.title()

    # Si le titre est vide après nettoyage, essayer une approche plus conservative
    if not cleaned_title or len(cleaned_title) < 3:
        conservative_clean = original_name

        # Chercher le premier élément technique pour couper avant
        tech_patterns = [r'\b\d{4}\b', r'\bMULTI\b', r'\bVFQ\b', r'\b1080p\b', r'\bWEB\b']
        for pattern in tech_patterns:
            match = re.search(pattern, conservative_clean, re.IGNORECASE)
            if match:
                cleaned_title = conservative_clean[:match.start()].strip()
                break

        if not cleaned_title:
            cleaned_title = original_name.split('.')[0]

        # Nettoyage basique et capitalisation
        cleaned_title = re.sub(r'[._-]', ' ', cleaned_title)
        cleaned_title = cleaned_title.title().strip()

    # Si toujours vide, utiliser le nom de base
    if not cleaned_title:
        cleaned_title = "Fichier non identifié"

    # Extraction de l'année du nom original
    year_match = re.search(r'\b(19|20)\d{2}\b', original_name)
    year = year_match.group() if year_match else "Année inconnue"

    # Utilisation des specs existantes ou création de specs basiques
    if video.spec and video.spec.strip():
        specs = video.spec.strip()
    else:
        # Extraction basique des caractéristiques depuis le nom original
        specs_parts = []

        # Langue
        if re.search(r'\bMULTI\b', original_name, re.IGNORECASE):
            specs_parts.append('MULTi')
        elif re.search(r'\b(VF|FR|FRENCH)\b', original_name, re.IGNORECASE):
            specs_parts.append('FR')
        elif re.search(r'\bVOSTFR\b', original_name, re.IGNORECASE):
            specs_parts.append('VOSTFR')
        else:
            specs_parts.append('VO')

        # Codec
        if re.search(r'\bAV1\b', original_name, re.IGNORECASE):
            specs_parts.append('AV1')
        elif re.search(r'\b(x265|HEVC|H265)\b', original_name, re.IGNORECASE):
            specs_parts.append('HEVC')
        elif re.search(r'\b(x264|H264)\b', original_name, re.IGNORECASE):
            specs_parts.append('x264')

        # Résolution
        if re.search(r'\b2160p\b', original_name, re.IGNORECASE):
            specs_parts.append('2160p')
        elif re.search(r'\b1080p\b', original_name, re.IGNORECASE):
            specs_parts.append('1080p')
        elif re.search(r'\b720p\b', original_name, re.IGNORECASE):
            specs_parts.append('720p')

        specs = ' '.join(specs_parts) if specs_parts else 'Specs inconnues'

    # Construction du nom formaté
    formatted_name = f"{cleaned_title} ({year}) {specs}"
    formatted_name = normalize(formatted_name)

    # Ajout de l'extension
    file_ext = video.complete_path_original.suffix
    if file_ext == '.ts':
        file_ext = '.mp4'

    return formatted_name + file_ext
