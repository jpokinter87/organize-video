"""Configuration settings and constants for the organize package."""

from pathlib import Path
from typing import Set, Dict

# Video file extensions
EXT_VIDEO: Set[str] = {
    "mkv", "avi", "wmv", "mpeg", "mpg", "m4v", "mp4", "flv", "ts", "rm", "rmvb", "mov"
}

ALL_EXTENSIONS: Set[str] = {
    ".mkv", ".avi", ".wmv", ".mpeg", ".mpg", ".m4v", ".mp4", ".flv", ".ts", ".rm", ".rmvb",
    ".mov", ".mp3", ".flac", ".wav", ".wma", ".cbr", ".cbz", ".pdf", ".epub", ".txt", ".odt",
    ".doc"
}

# Video categories
CATEGORIES: Set[str] = {'Séries', 'Films', 'Animation', 'Docs#1', 'Docs'}
FILMANIM: Set[str] = {'Films', 'Animation'}
FILMSERIE: Set[str] = {'Films', 'Séries'}
NOT_DOC: Set[str] = {'Films', 'Séries', 'Animation'}

# Default directories
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

# Genres that take priority in classification
PRIORITY_GENRES: Set[str] = {
    'Western', 'Historique', 'SF', 'Films pour enfants', 'Comédie dramatique'
}

# Cache expiration time in seconds (24 hours)
CACHE_EXPIRATION_SECONDS: int = 86400

# Request timeout in seconds
REQUEST_TIMEOUT_SECONDS: int = 10

# Maximum cleanup iterations
MAX_CLEANUP_ITERATIONS: int = 10

# Sentinel value for "process all files"
PROCESS_ALL_FILES_DAYS: float = 100000000.0
