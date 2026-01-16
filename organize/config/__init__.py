"""Configuration and CLI handling."""

from organize.config.settings import (
    # Extensions
    EXT_VIDEO,
    ALL_EXTENSIONS,
    # Catégories
    CATEGORIES,
    FILMANIM,
    FILMSERIE,
    NOT_DOC,
    # Répertoires par défaut
    DEFAULT_SEARCH_DIR,
    DEFAULT_STORAGE_DIR,
    DEFAULT_SYMLINKS_DIR,
    DEFAULT_TEMP_SYMLINKS_DIR,
    # Genres
    GENRES,
    PRIORITY_GENRES,
    SUPPORTED_GENRES,
    GENRE_MAPPING,
    GENRE_UNDETECTED,
    COMEDY_DRAMA_GENRE,
    # Cache et timeouts
    CACHE_EXPIRATION_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_CLEANUP_ITERATIONS,
    PROCESS_ALL_FILES_DAYS,
    # Hachage
    SMALL_FILE_THRESHOLD,
    PARTIAL_HASH_CHUNK_SIZE,
    HASH_FILE_POSITION_DIVISOR,
    # Cache et base de données
    MAX_CACHE_SIZE,
    CACHE_DB_FILENAME,
    DATABASE_NAME_PATTERN,
    DATABASE_NAME_FILMS,
    # Résolution vidéo
    RESOLUTION_THRESHOLDS,
    # API
    TMDB_BASE_URL,
    TMDB_SEARCH_MOVIE_ENDPOINT,
    TMDB_SEARCH_TV_ENDPOINT,
    TMDB_DEFAULT_LANGUAGE,
    TMDB_USER_AGENT,
    TVDB_LANGUAGES,
    TVDB_DEFAULT_LANGUAGE,
    # Normalisation de texte
    ARTICLES,
    ACCENT_MAP,
    LIGATURE_MAP,
    SPECIAL_CHAR_REPLACEMENTS,
    ARTICLE_DETECTION_MIN_LENGTH,
    # Normalisation langues/codecs
    LANGUAGE_MAPPING,
    CODEC_MAPPING,
    # Patterns regex
    RESOLUTION_PATTERNS,
    SOURCE_PATTERNS,
    AUDIO_CODEC_PATTERNS,
    VIDEO_CODEC_PATTERNS,
    # Interface utilisateur
    UNDETECTED_PATHS,
    MAX_FILES_PER_FOLDER,
    SEASON_FOLDER_FORMAT,
    SEASON_FOLDER_REGEX,
    INTERACTIVE_HELP_TEXT,
    YEAR_NOT_AVAILABLE,
    LANGUAGE_LABELS,
    # Lecteurs vidéo
    VIDEO_PLAYERS,
    # Animation
    ANIMATION_SUBCATEGORIES,
    # État de l'application
    DEFAULT_DAYS_BACK,
    DEFAULT_SECONDS_BACK,
    APP_STATE_TABLE,
    LAST_EXEC_KEY,
)
from organize.config.context import (
    ExecutionContext,
    get_context,
    set_context,
    execution_context,
)
from organize.config.cli import (
    CLIArgs,
    create_parser,
    parse_arguments,
    validate_directories,
    args_to_cli_args,
)
from organize.config.manager import (
    ConfigurationManager,
    ValidationResult,
)

__all__ = [
    # Extensions
    "EXT_VIDEO",
    "ALL_EXTENSIONS",
    # Catégories
    "CATEGORIES",
    "FILMANIM",
    "FILMSERIE",
    "NOT_DOC",
    # Répertoires
    "DEFAULT_SEARCH_DIR",
    "DEFAULT_STORAGE_DIR",
    "DEFAULT_SYMLINKS_DIR",
    "DEFAULT_TEMP_SYMLINKS_DIR",
    # Genres
    "GENRES",
    "PRIORITY_GENRES",
    "SUPPORTED_GENRES",
    "GENRE_MAPPING",
    "GENRE_UNDETECTED",
    "COMEDY_DRAMA_GENRE",
    # Cache et timeouts
    "CACHE_EXPIRATION_SECONDS",
    "REQUEST_TIMEOUT_SECONDS",
    "MAX_CLEANUP_ITERATIONS",
    "PROCESS_ALL_FILES_DAYS",
    # Hachage
    "SMALL_FILE_THRESHOLD",
    "PARTIAL_HASH_CHUNK_SIZE",
    "HASH_FILE_POSITION_DIVISOR",
    # Cache et base de données
    "MAX_CACHE_SIZE",
    "CACHE_DB_FILENAME",
    "DATABASE_NAME_PATTERN",
    "DATABASE_NAME_FILMS",
    # Résolution vidéo
    "RESOLUTION_THRESHOLDS",
    # API
    "TMDB_BASE_URL",
    "TMDB_SEARCH_MOVIE_ENDPOINT",
    "TMDB_SEARCH_TV_ENDPOINT",
    "TMDB_DEFAULT_LANGUAGE",
    "TMDB_USER_AGENT",
    "TVDB_LANGUAGES",
    "TVDB_DEFAULT_LANGUAGE",
    # Normalisation de texte
    "ARTICLES",
    "ACCENT_MAP",
    "LIGATURE_MAP",
    "SPECIAL_CHAR_REPLACEMENTS",
    "ARTICLE_DETECTION_MIN_LENGTH",
    # Normalisation langues/codecs
    "LANGUAGE_MAPPING",
    "CODEC_MAPPING",
    # Patterns regex
    "RESOLUTION_PATTERNS",
    "SOURCE_PATTERNS",
    "AUDIO_CODEC_PATTERNS",
    "VIDEO_CODEC_PATTERNS",
    # Interface utilisateur
    "UNDETECTED_PATHS",
    "MAX_FILES_PER_FOLDER",
    "SEASON_FOLDER_FORMAT",
    "SEASON_FOLDER_REGEX",
    "INTERACTIVE_HELP_TEXT",
    "YEAR_NOT_AVAILABLE",
    "LANGUAGE_LABELS",
    # Lecteurs vidéo
    "VIDEO_PLAYERS",
    # Animation
    "ANIMATION_SUBCATEGORIES",
    # État de l'application
    "DEFAULT_DAYS_BACK",
    "DEFAULT_SECONDS_BACK",
    "APP_STATE_TABLE",
    "LAST_EXEC_KEY",
    # Contexte d'exécution
    "ExecutionContext",
    "get_context",
    "set_context",
    "execution_context",
    # CLI
    "CLIArgs",
    "create_parser",
    "parse_arguments",
    "validate_directories",
    "args_to_cli_args",
    # Configuration
    "ConfigurationManager",
    "ValidationResult",
]
