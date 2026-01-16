"""Configuration settings and constants for the organize package.

Ce module centralise toutes les constantes et paramètres de configuration
utilisés par l'application d'organisation de vidéos.
"""

from pathlib import Path
from typing import Set, Dict, List, Tuple

# =============================================================================
# EXTENSIONS DE FICHIERS
# =============================================================================

# Extensions de fichiers vidéo
EXT_VIDEO: Set[str] = {
    "mkv", "avi", "wmv", "mpeg", "mpg", "m4v", "mp4", "flv", "ts", "rm", "rmvb", "mov"
}

ALL_EXTENSIONS: Set[str] = {
    ".mkv", ".avi", ".wmv", ".mpeg", ".mpg", ".m4v", ".mp4", ".flv", ".ts", ".rm", ".rmvb",
    ".mov", ".mp3", ".flac", ".wav", ".wma", ".cbr", ".cbz", ".pdf", ".epub", ".txt", ".odt",
    ".doc"
}

# Catégories vidéo
CATEGORIES: Set[str] = {'Séries', 'Films', 'Animation', 'Docs#1', 'Docs'}
FILMANIM: Set[str] = {'Films', 'Animation'}
FILMSERIE: Set[str] = {'Films', 'Séries'}
NOT_DOC: Set[str] = {'Films', 'Séries', 'Animation'}

# Répertoires par défaut
DEFAULT_SEARCH_DIR = Path('/media/NAS64/temp')
DEFAULT_STORAGE_DIR = Path('/media/NAS64')
DEFAULT_SYMLINKS_DIR = Path('/media/Serveur/test')
DEFAULT_TEMP_SYMLINKS_DIR = Path('/media/Serveur/LAF/liens_à_faire')

# TMDB Genre ID to French genre name mapping
GENRES: Dict[int, str] = {
    28: "Action & Aventure",
    12: "Action & Aventure",
    16: "Animation",
    35: "Comédie",
    80: "Policier",
    99: "Docs",
    18: "Drame",
    10751: "Films pour enfants",
    14: "Fantastique",
    36: "Historique",
    27: "Horreur",
    10402: "Musique",
    9648: "Thriller",
    10749: "Romance",
    878: "SF",
    10770: "Téléfilm",
    53: "Thriller",
    10752: "Guerre & espionnage",
    37: "Western",
    10765: "SF",
    10759: "Action & Aventure",
    10768: "War & Politics",
    10762: "Séries pour enfants",
    0: "N/A",
}

# Genres prioritaires dans la classification
PRIORITY_GENRES: Set[str] = {
    'Western', 'Historique', 'SF', 'Films pour enfants', 'Comédie dramatique'
}

# Genres supportés par la bibliothèque vidéo
SUPPORTED_GENRES: Set[str] = {
    "Action & Aventure", "Animation", "Comédie", "Comédie dramatique",
    "Policier", "Drame", "Films pour enfants", "Fantastique",
    "Historique", "Horreur", "SF", "Thriller", "Western",
    "Guerre & espionnage"
}

# Correspondance des genres non supportés vers les genres supportés
GENRE_MAPPING: Dict[str, str] = {
    # Romance
    'romance': 'Drame',
    'romantic': 'Drame',
    'romantique': 'Drame',
    # Téléfilm
    'téléfilm': 'Drame',
    'telefilm': 'Drame',
    'tv movie': 'Drame',
    'tv-movie': 'Drame',
    # Musique
    'music': 'Drame',
    'musical': 'Drame',
    'musique': 'Drame',
    # Criminel
    'crime': 'Policier',
    'criminal': 'Policier',
    # Mystère
    'mystery': 'Thriller',
    'mystère': 'Thriller',
    'mysterious': 'Thriller',
    # Aventure
    'adventure': 'Action & Aventure',
    'aventure': 'Action & Aventure',
    # Famille
    'family': 'Films pour enfants',
    'famille': 'Films pour enfants',
    # Biographie
    'biography': 'Drame',
    'biographical': 'Drame',
    'biographie': 'Drame',
    # Sport
    'sport': 'Drame',
    'sports': 'Drame',
    # Actualités
    'news': 'Drame',
    'actualités': 'Drame',
}

# Durée d'expiration du cache en secondes (24 heures)
CACHE_EXPIRATION_SECONDS: int = 86400

# Délai d'attente des requêtes en secondes
REQUEST_TIMEOUT_SECONDS: int = 10

# Nombre maximum d'itérations de nettoyage
MAX_CLEANUP_ITERATIONS: int = 10

# Valeur sentinelle pour « traiter tous les fichiers »
PROCESS_ALL_FILES_DAYS: float = 100000000.0

# =============================================================================
# CONSTANTES DE HACHAGE MD5
# =============================================================================

# Seuil de taille de fichier pour le hachage complet (650 Ko)
SMALL_FILE_THRESHOLD: int = 650000

# Taille du chunk pour le hachage partiel (512 Ko)
PARTIAL_HASH_CHUNK_SIZE: int = 524288

# Diviseur pour la position de lecture dans le fichier (1/8)
HASH_FILE_POSITION_DIVISOR: int = 8

# =============================================================================
# CACHE ET BASE DE DONNÉES
# =============================================================================

# Taille maximale du cache LRU
MAX_CACHE_SIZE: int = 1000

# Nom du fichier de cache API
CACHE_DB_FILENAME: str = 'cache.db'

# Pattern de nom pour les bases de données de symlinks
DATABASE_NAME_PATTERN: str = 'symlink_video_{category}.db'
DATABASE_NAME_FILMS: str = 'symlink_video_Films.db'

# =============================================================================
# SEUILS DE RÉSOLUTION VIDÉO
# =============================================================================

# Seuils de résolution pour la détection de qualité (largeur, hauteur)
RESOLUTION_THRESHOLDS: Dict[str, Tuple[int, int]] = {
    '2160p': (3800, 2100),
    '1080p': (1900, 1000),
    '720p': (1200, 700),
    'DVDRip': (700, 500),
}

# =============================================================================
# CONSTANTES API
# =============================================================================

# TMDB
TMDB_BASE_URL: str = 'https://api.themoviedb.org/3'
TMDB_SEARCH_MOVIE_ENDPOINT: str = '/search/movie'
TMDB_SEARCH_TV_ENDPOINT: str = '/search/tv'
TMDB_DEFAULT_LANGUAGE: str = 'fr-FR'
TMDB_USER_AGENT: str = (
    'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) '
    'Gecko/20100101 Firefox/24.0'
)

# TVDB
TVDB_LANGUAGES: List[str] = ['fr', 'en']
TVDB_DEFAULT_LANGUAGE: str = 'fr'

# =============================================================================
# NORMALISATION DE TEXTE
# =============================================================================

# Articles à supprimer des titres (français et anglais)
ARTICLES: List[str] = [
    "L'", "Les ", "Le ", "La ", "Un ", "Une ",
    "Des ", "Du ", "De ", "D'", "Au ", "Aux ",
    "The ", "A ", "An ", "À "
]

# Mapping des caractères accentués vers ASCII
ACCENT_MAP: Dict[str, str] = {
    'à': 'a', 'â': 'a', 'ä': 'a', 'á': 'a',
    'è': 'e', 'ê': 'e', 'ë': 'e', 'é': 'e',
    'ì': 'i', 'î': 'i', 'ï': 'i', 'í': 'i',
    'ò': 'o', 'ô': 'o', 'ö': 'o', 'ó': 'o',
    'ù': 'u', 'û': 'u', 'ü': 'u', 'ú': 'u',
    'ÿ': 'y', 'ý': 'y',
    'ñ': 'n', 'ç': 'c',
}

# Ligatures à remplacer
LIGATURE_MAP: Dict[str, str] = {
    'œ': 'o',
    'æ': 'a',
}

# Caractères spéciaux à remplacer dans les noms de fichiers
SPECIAL_CHAR_REPLACEMENTS: Dict[str, str] = {
    ':': ', ',
    '?': '...',
    '/': ' - ',
}

# Longueur minimale pour détecter un article au début d'un titre
ARTICLE_DETECTION_MIN_LENGTH: int = 6

# =============================================================================
# NORMALISATION DES LANGUES ET CODECS
# =============================================================================

# Mapping de normalisation des langues
LANGUAGE_MAPPING: Dict[str, str] = {
    "vostfr": "VOSTFR",
    "multi": "MULTi",
    "french": "FR",
    "truefrench": "TrueFrench",
    "vo": "VO",
    "en": "VO",
    "fr": "FR",
}

# Mapping de normalisation des codecs
CODEC_MAPPING: Dict[str, str] = {
    "h264": "x264",
    "x265": "HEVC",
    "av1": "AV1",
}

# =============================================================================
# PATTERNS REGEX POUR LA DÉTECTION DE MÉTADONNÉES
# =============================================================================

# Patterns de résolution
RESOLUTION_PATTERNS: str = r'\b(1080p|720p|480p|2160p|4K|UHD)\b'

# Patterns de source/qualité
SOURCE_PATTERNS: str = r'\b(WEB|BluRay|BDRip|DVDRip|WEBRip|HDTV|WEB-DL)\b'

# Patterns de codec audio
AUDIO_CODEC_PATTERNS: str = r'\b(AC3|DTS|AAC|MP3|DD|DDPlus|Atmos)\b'

# Patterns de codec vidéo
VIDEO_CODEC_PATTERNS: str = r'\b(x264|x265|HEVC|H264|H265|AV1)\b'

# =============================================================================
# CONSTANTES D'INTERFACE UTILISATEUR
# =============================================================================

# Marqueur pour les fichiers non détectés
GENRE_UNDETECTED: str = 'Non détecté'

# Chemin des fichiers non détectés par catégorie
UNDETECTED_PATHS: Dict[str, str] = {
    'Films': 'Films/non détectés',
    'Séries': 'Séries/non détectés',
}

# Nombre maximum de fichiers à afficher par dossier
MAX_FILES_PER_FOLDER: int = 5

# Format du dossier de saison
SEASON_FOLDER_FORMAT: str = 'Saison {season:02d}'
SEASON_FOLDER_REGEX: str = r'Saison \d{2}'

# Texte d'aide pour les prompts interactifs
INTERACTIVE_HELP_TEXT: str = 'm=manuel | v=visionner | s=skip | r=retry'

# Valeur par défaut pour année inconnue
YEAR_NOT_AVAILABLE: str = 'N/A'

# Labels de langues pour l'affichage
LANGUAGE_LABELS: Dict[str, str] = {
    'fr': 'français',
    'en': 'anglais',
}

# =============================================================================
# LECTEURS VIDÉO PAR PLATEFORME
# =============================================================================

VIDEO_PLAYERS: Dict[str, List[str]] = {
    'linux': ['mpv', 'vlc', 'mplayer', 'totem', 'xdg-open'],
    'darwin': ['open', 'mpv', 'vlc'],
    'windows': ['start', 'vlc', 'mpv'],
}

# =============================================================================
# SOUS-CATÉGORIES D'ANIMATION
# =============================================================================

ANIMATION_SUBCATEGORIES: Dict[str, str] = {
    'adult': 'Animation/Adultes',
    'children': 'Animation/Animation Enfant',
}

# Combinaisons de genres spéciales
COMEDY_DRAMA_GENRE: str = 'Comédie dramatique'

# =============================================================================
# GESTION DE L'ÉTAT DE L'APPLICATION
# =============================================================================

# Nombre de jours par défaut pour la recherche de fichiers récents
DEFAULT_DAYS_BACK: int = 3

# Secondes correspondant à DEFAULT_DAYS_BACK (3 jours = 259200 secondes)
DEFAULT_SECONDS_BACK: int = DEFAULT_DAYS_BACK * 86400

# Nom de la table pour l'état de l'application
APP_STATE_TABLE: str = 'app_state'

# Clé pour la dernière exécution
LAST_EXEC_KEY: str = 'last_exec'
