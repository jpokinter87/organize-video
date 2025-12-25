import re
import os
import argparse
import shutil
import hashlib
import requests
import urllib.parse
import unicodedata
import tvdb_api
import time
import babelfish
import sqlite3
import json
import multiprocessing
import sys
import tty
import termios
import select
import subprocess

from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv
from dataclasses import dataclass, field
from rapidfuzz import fuzz
from guessit import guessit
from pymediainfo import MediaInfo
from pathlib import Path
from tqdm import tqdm
from typing import Union, Generator, Tuple, Any, Dict, Optional, List, Set
from loguru import logger
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.align import Align



# Configuration du logger
logger.add("organize.log", rotation="100 MB")
console = Console()

# Chargement des variables d'environnement
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TVDB_API_KEY = os.getenv("TVDB_API_KEY")

# Constantes
EXT_VIDEO: Set[str] = {"mkv", "avi", "wmv", "mpeg", "mpg", "m4v", "mp4", "flv", "ts", "rm", "rmvb", "mov"}
ALL_EXTENSIONS: Set[str] = {".mkv", ".avi", ".wmv", ".mpeg", ".mpg", ".m4v", ".mp4", ".flv", ".ts", ".rm", ".rmvb",
                            ".mov", ".mp3", ".flac", ".wav", ".wma", ".cbr", ".cbz", ".pdf", ".epub", ".txt", ".odt",
                            ".doc"}

CATEGORIES: Set[str] = {'Séries', 'Films', 'Animation', 'Docs#1', 'Docs'}
FILMANIM: Set[str] = {'Films', 'Animation'}
FILMSERIE: Set[str] = {'Films', 'Séries'}
NOT_DOC: Set[str] = {'Films', 'Séries', 'Animation'}

# Répertoires par défaut
DEFAULT_SEARCH_DIR = Path('/media/NAS64/temp')
DEFAULT_STORAGE_DIR = Path('/media/NAS64')
DEFAULT_SYMLINKS_DIR = Path('/media/Serveur/test')
DEFAULT_TEMP_SYMLINKS_DIR = Path('/media/Serveur/LAF/liens_à_faire')

GENRES = {
    28: "Action & Aventure", 12: "Action & Aventure", 16: "Animation", 35: "Comédie", 80: "Policier", 99: "Docs",
    18: "Drame", 10751: "Films pour enfants", 14: "Fantastique", 36: "Historique", 27: "Horreur",
    10402: "Musique", 9648: "Thriller", 10749: "Romance", 878: "SF", 10770: "Téléfilm", 53: "Thriller",
    10752: "Guerre & espionnage", 37: "Western", 10765: "SF", 10759: "Action & Aventure",
    10768: "War & Politics", 10762: "Séries pour enfants", 0: "N/A",

    # 🆕 Ajout de genres supplémentaires souvent rencontrés
    9648: "Thriller", 10402: "Musique", 10749: "Romance", 10770: "Téléfilm"
}
PRIORITY_GENRES = {'Western', 'Historique', 'SF', 'Films pour enfants', 'Comédie dramatique'}


@dataclass
class Video:
    complete_path_original: Path = field(default_factory=Path)
    complete_path_temp_links: Path = field(default_factory=Path)
    complete_dir_symlinks: Path = field(default_factory=Path)
    destination_file: Path = field(default_factory=Path)
    extended_sub: Path = field(default_factory=Path)
    sub_directory: Path = field(default_factory=Path)
    title: str = ''
    title_fr: str = ''
    date_film: int = 0
    sequence: str = ''
    season: int = 0
    episode: int = 0
    spec: str = ''
    genre: str = ''
    list_genres: List[str] = field(default_factory=list)
    formatted_filename: str = ''
    name_without_article: str = ''
    type_file: str = ''
    hash: str = ''

    def format_name(self, title: str) -> str:
        # Cas spécial pour les fichiers non détectés
        if not title or title.strip() == '' or not self.title_fr:
            return format_undetected_filename(self)

        if self.is_serie():
            result = f'{title} ({self.date_film}) {self.sequence} {self.spec}'
        else:
            result = f'{title} ({self.date_film}) {self.spec}'

        result = normalize(result)
        file_ext = self.complete_path_original.suffix
        if file_ext == '.ts':
            file_ext = '.mp4'
        result += file_ext
        return result


    def find_initial(self) -> str:
        return remove_article(self.title_fr).lower()

    def is_film(self) -> bool:
        return self.type_file == 'Films'

    def is_serie(self) -> bool:
        return self.type_file == 'Séries'

    def is_animation(self) -> bool:
        return self.type_file == 'Animation'

    def is_film_serie(self) -> bool:
        return self.type_file in FILMSERIE

    def is_film_anim(self) -> bool:
        return self.type_file in FILMANIM

    def is_not_doc(self) -> bool:
        return self.type_file in NOT_DOC


class SubfolderCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value


subfolder_cache = SubfolderCache()
series_subfolder_cache = SubfolderCache()


class Tmdb:
    def __init__(self):
        self.base = 'https://api.themoviedb.org/3'
        self.api_key = TMDB_API_KEY
        self.search_movie_endpoint = '/search/movie'
        self.search_tv_endpoint = '/search/tv'
        self.lang = 'fr-FR'

    def build_url(self, query: str, content_type: str = 'Films') -> str:
        endpoint = self.search_movie_endpoint if content_type in FILMANIM else self.search_tv_endpoint
        query_params = urllib.parse.urlencode({
            'api_key': self.api_key,
            'language': self.lang,
            'query': query
        })
        return f'{self.base}{endpoint}?{query_params}'

    def find_content(self, name: str, content_type: str = 'Films') -> Optional[Dict]:
        if not self.api_key:
            logger.warning("Clé API TMDB manquante")
            return None

        url = self.build_url(name, content_type)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0'}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erreur lors de la requête API : {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.warning(f"Erreur de requête : {e}")
            return None


class CacheDB:
    def __init__(self, db_path: Path = Path("cache.db")):
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données : {e}")

    def create_tables(self):
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS tmdb_cache (
                    query TEXT PRIMARY KEY,
                    result TEXT,
                    timestamp INTEGER
                );

                CREATE TABLE IF NOT EXISTS tvdb_cache (
                    series_id INTEGER,
                    season INTEGER,
                    episode INTEGER,
                    result TEXT,
                    timestamp INTEGER,
                    PRIMARY KEY (series_id, season, episode)
                );
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la création des tables : {e}")

    def get_tmdb(self, query: str, expiration: int = 86400) -> dict:
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT result, timestamp FROM tmdb_cache WHERE query = ?", (query,))
            row = cursor.fetchone()
            if row and (time.time() - row[1] < expiration):
                return json.loads(row[0])
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Erreur lors de la récupération du cache TMDB : {e}")
        return {}

    def set_tmdb(self, query: str, result: dict):
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO tmdb_cache (query, result, timestamp) VALUES (?, ?, ?)",
                (query, json.dumps(result), int(time.time()))
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache TMDB : {e}")

    def get_tvdb(self, series_id: int, season: int, episode: int, expiration: int = 86400) -> dict:
        if not self.conn:
            return {}

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT result, timestamp FROM tvdb_cache WHERE series_id = ? AND season = ? AND episode = ?",
                (series_id, season, episode)
            )
            row = cursor.fetchone()
            if row and (time.time() - row[1] < expiration):
                return json.loads(row[0])
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Erreur lors de la récupération du cache TVDB : {e}")
        return {}

    def set_tvdb(self, series_id: int, season: int, episode: int, result: dict):
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO tvdb_cache (series_id, season, episode, result, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (series_id, season, episode, json.dumps(result), int(time.time()))
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache TVDB : {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


def launch_video_player(video_path: Path) -> bool:
    """
    Lance le lecteur vidéo par défaut pour visualiser le fichier.
    Retourne True si le lancement réussit, False sinon.
    """
    try:
        # Détection du système et des lecteurs disponibles
        video_players = []

        if sys.platform.startswith('linux'):
            # Linux - ordre de préférence
            potential_players = ['mpv', 'vlc', 'mplayer', 'totem', 'xdg-open']
        elif sys.platform == 'darwin':
            # macOS
            potential_players = ['open', 'vlc', 'mpv']
        elif sys.platform.startswith('win'):
            # Windows
            potential_players = ['vlc', 'wmplayer', 'start']
        else:
            potential_players = ['mpv', 'vlc', 'xdg-open']

        # Chercher le premier lecteur disponible
        for player in potential_players:
            if shutil.which(player):
                video_players.append(player)

        if not video_players:
            console.print("[red]❌ Aucun lecteur vidéo trouvé[/red]")
            console.print("[dim]Lecteurs supportés: VLC, MPV, MPlayer, etc.[/dim]")
            return False

        # Lancer avec le premier lecteur disponible
        player = video_players[0]
        console.print(f"[blue]🎬 Lancement de {player} pour visualiser le fichier...[/blue]")

        if sys.platform.startswith('win') and player == 'start':
            # Windows avec start
            subprocess.Popen(['start', str(video_path)], shell=True)
        elif sys.platform == 'darwin' and player == 'open':
            # macOS avec open
            subprocess.Popen(['open', str(video_path)])
        else:
            # Linux et autres lecteurs
            subprocess.Popen([player, str(video_path)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)

        console.print("[green]✅ Lecteur vidéo lancé[/green]")
        console.print("[dim]Appuyez sur une touche pour continuer après avoir visionné...[/dim]")
        return True

    except subprocess.SubprocessError as e:
        console.print(f"[red]❌ Erreur lors du lancement du lecteur : {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Erreur inattendue : {e}[/red]")
        return False


def parse_arg():
    parser = argparse.ArgumentParser(
        prog='organize_video',
        description="""
        Parcourt le répertoire et organise les fichiers vidéo en créant des liens symboliques
        dans une structure organisée par genre et ordre alphabétique.
        """)

    groupe_day = parser.add_mutually_exclusive_group()

    groupe_day.add_argument(
        '-a', '--all',
        action='store_true',
        help='traite tous les fichiers sans distinction de date')

    groupe_day.add_argument(
        '-d', '--day', type=float, default=0,
        help='ne traite que les fichiers récents (de moins de DAY jours)')

    parser.add_argument(
        '-i', '--input',
        default=str(DEFAULT_SEARCH_DIR),
        help=f"répertoire d'origine (défaut: {DEFAULT_SEARCH_DIR})")

    parser.add_argument(
        '-o', '--output',
        default=str(DEFAULT_TEMP_SYMLINKS_DIR),
        help=f"répertoire de destination provisoire des symlinks (défaut: {DEFAULT_TEMP_SYMLINKS_DIR})")

    parser.add_argument(
        '-s', '--symlinks',
        default=str(DEFAULT_SYMLINKS_DIR),
        help=f"répertoire de destination définitif des liens symboliques (défaut: {DEFAULT_SYMLINKS_DIR})")

    parser.add_argument(
        '--storage',
        default=str(DEFAULT_STORAGE_DIR),
        help=f"répertoire de stockage final des fichiers (défaut: {DEFAULT_STORAGE_DIR})")

    parser.add_argument(
        '--force', action='store_true',
        help="ignore la vérification des hash (mode développement)")

    # 🆕 Nouvelle option dry-run
    parser.add_argument(
        '--dry-run', action='store_true',
        help="mode simulation - aucune modification de fichier (recommandé pour les tests)")

    parser.add_argument(
        '--debug', action='store_true',
        help="mode debug activé")

    parser.add_argument(
        '--tag', nargs='?', default='',
        help="tag à rechercher si mode debug activé")

    args = parser.parse_args()

    if args.all:
        traite = 100000000.0
    elif args.day != 0:
        traite = args.day
    else:
        traite = 0

    rep_recherche = Path(args.input)
    rep_destination = Path(args.output)
    rep_symlinks = Path(args.symlinks)
    rep_storage = Path(args.storage)

    # Validation des répertoires
    if not rep_recherche.exists():
        logger.error(f"Le répertoire d'entrée {rep_recherche} n'existe pas")
        exit(1)

    # Création des répertoires de destination si nécessaire (sauf en mode dry-run)
    if not args.dry_run:
        for rep in [rep_destination, rep_symlinks, rep_storage]:
            rep.mkdir(parents=True, exist_ok=True)

    # Gestion du mode debug
    debug = args.debug
    tag = args.tag if args.debug else ''
    force = args.force
    dry_run = args.dry_run  # 🆕

    return rep_recherche, rep_destination, rep_symlinks, rep_storage, traite, debug, tag, force, dry_run


def format_undetected_filename(video: Video) -> str:
    """Formate le nom de fichier pour les vidéos non détectées."""

    # Extraction du titre à partir du nom de fichier original
    original_name = video.complete_path_original.stem

    # Patterns de nettoyage plus complets et précis
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
        r'-[A-Z0-9]+$', r'\b[A-Z0-9]{4,}$',  # SHADOW, Slay3R, etc.

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
    cleaned_title = re.sub(r'[.\-_]+', ' ', cleaned_title)  # Remplace points, tirets, underscores par espaces
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title)  # Supprime les espaces multiples
    cleaned_title = cleaned_title.strip()  # Supprime les espaces en début/fin

    # Nettoyage supplémentaire des mots isolés problématiques
    problematic_words = ['vfq', 'mkv', 'avi', 'mp4', 'dd5', '10bit', '1', 'slay3r']
    words = cleaned_title.split()
    cleaned_words = [word for word in words if word.lower() not in problematic_words]
    cleaned_title = ' '.join(cleaned_words)

    # Capitalisation du titre
    cleaned_title = cleaned_title.title()

    # Si le titre est vide après nettoyage, essayer une approche plus conservative
    if not cleaned_title or len(cleaned_title) < 3:
        # Extraction du titre avant le premier pattern technique détecté
        conservative_clean = original_name

        # Chercher le premier élément technique pour couper avant
        tech_patterns = [r'\b\d{4}\b', r'\bMULTI\b', r'\bVFQ\b', r'\b1080p\b', r'\bWEB\b']
        for pattern in tech_patterns:
            match = re.search(pattern, conservative_clean, re.IGNORECASE)
            if match:
                cleaned_title = conservative_clean[:match.start()].strip()
                break

        if not cleaned_title:
            cleaned_title = original_name.split('.')[0]  # Prendre juste le premier segment

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

def normalize(string: str) -> str:
    """Normalise une chaîne en supprimant les accents et en corrigeant les caractères spéciaux."""
    if not string:
        return ""

    result = string
    if 'œ' in string or 'æ' in string:
        translate = {'œ': 'o', 'æ': 'a'}
        result = ''.join(translate.get(char, char) for char in string)

    result = result.replace(" .", ".")
    result = result.replace(':', ', ').replace('?', '...').replace('/', ' - ')
    result = result.replace(' , ', ', ').replace('  ', ' ')
    return result.strip()


def remove_article(title: str) -> str:
    """Supprime les articles du début d'un titre et normalise les accents."""
    if not title:
        return ""

    articles = ["L'", "Les ", "Le ", "La ", "Une ", "Un ", "Des ", "De l'",
                "De la ", "De ", "Du ", "D'un ", "D'une ", "A la ", "A l'",
                "À la ", "À l'", "Au ", "Aux ", "The ", "A ", "L ", "An "]

    title = title.strip()
    seg_f = title[:6]

    for article in articles:
        if article in seg_f and title.startswith(article):
            title = title[len(article):]
            break

    # ✅ Normalisation des accents APRÈS suppression de l'article
    title = normalize_accents(title)
    return normalize(title).strip()


def normalize_accents(text: str) -> str:
    """Normalise les accents pour le classement alphabétique."""
    import unicodedata

    # Dictionnaire de correspondances spécifiques
    accent_map = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ý': 'y', 'ÿ': 'y',
        'ç': 'c', 'ñ': 'n',
        'œ': 'oe', 'æ': 'ae'
    }

    # Application des correspondances manuelles
    for accented, normal in accent_map.items():
        text = text.replace(accented, normal)
        text = text.replace(accented.upper(), normal.upper())

    # Normalisation Unicode pour les cas non couverts
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    return text


def load_last_exec() -> float:
    """Charge la date de dernière exécution."""
    try:
        with open("last_exec_video", "r") as last_exec_file:
            last_exec = float(last_exec_file.read().strip())
    except (FileNotFoundError, ValueError):
        last_exec = time.time() - 259200  # 3 jours avant

    # Sauvegarde la date actuelle
    try:
        with open("last_exec_video", "w") as last_exec_file:
            last_exec_file.write(str(time.time()))
    except IOError as e:
        logger.warning(f"Impossible de sauvegarder la date d'exécution : {e}")

    return last_exec


def get_available_categories(directory: Path) -> List[Path]:
    """Retourne la liste des catégories disponibles dans le répertoire."""
    available_categories = []
    for category in CATEGORIES:
        category_path = directory / category
        if category_path.exists() and category_path.is_dir():
            available_categories.append(category_path)
    return available_categories


def get_file(directory: Path) -> Generator[Path, None, None]:
    """
    Génère tous les fichiers vidéo du répertoire qui se trouvent dans les catégories autorisées.
    """
    available_categories = get_available_categories(directory)

    if not available_categories:
        logger.warning(f"Aucune catégorie trouvée dans {directory}")
        return

    logger.info(f"Catégories trouvées: {[cat.name for cat in available_categories]}")

    try:
        for category_path in available_categories:
            logger.debug(f"Parcours de: {category_path}")
            file_count = 0
            for file in category_path.rglob("*"):
                if file.is_file() and file.suffix.lower() in ALL_EXTENSIONS:
                    file_count += 1
                    yield file
            logger.debug(f"  → {file_count} fichiers trouvés dans {category_path.name}")
    except Exception as e:
        logger.warning(f"Erreur lors du parcours de {directory} : {e}")


def count_videos(rep_recherche: Path) -> int:
    """Compte le nombre de fichiers vidéo à traiter dans les catégories autorisées."""
    available_categories = get_available_categories(rep_recherche)

    if not available_categories:
        return 0

    video_count = 0
    try:
        for category_path in available_categories:
            category_count = 0
            for file in category_path.rglob("*"):
                if file.is_file() and file.suffix.lower() in ALL_EXTENSIONS:
                    category_count += 1
            video_count += category_count
            logger.debug(f"{category_count} fichiers dans {category_path.name}")
    except Exception as e:
        logger.warning(f"Erreur lors du comptage : {e}")

    console.print(f"[blue]📁 Répartition par catégorie :[/blue]")
    for category_path in available_categories:
        count = sum(1 for f in category_path.rglob("*")
                    if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS)
        console.print(f"  • {category_path.name}: [cyan]{count}[/cyan] fichiers")

    return video_count

def checksum_md5(filename: Path) -> str:
    """Calcule le hash MD5 d'un fichier."""
    if not filename.exists():
        return 'no_md5_hash'

    md5 = hashlib.md5()
    try:
        with open(filename, 'rb') as f:
            size = filename.stat().st_size
            if size < 650000:
                md5.update(f.read())
            else:
                f.seek(size // 8)
                md5.update(f.read(524288))
        return md5.hexdigest()
    except Exception as e:
        logger.debug(f'Exception {e} dans le calcul du hash md5')
        return 'no_md5_hash'


def select_db(file: Path, storage_dir: Path) -> Path:
    """Sélectionne la base de données appropriée selon le type de vidéo."""
    type_video = type_of_video(file)
    if type_video in {'Films', 'Animation'}:
        return storage_dir / 'symlink_video_Films.db'
    else:
        return storage_dir / f'symlink_video_{type_video}.db'


def add_hash_to_db(file: Path, hash_value: str, storage_dir: Path):
    """Ajoute un hash à la base de données."""
    db_path = select_db(file, storage_dir)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Création de la table si elle n'existe pas
        cursor.execute('''CREATE TABLE IF NOT EXISTS file_hashes 
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')

        file_str = str(file)
        file_size = file.stat().st_size

        cursor.execute('SELECT 1 FROM file_hashes WHERE hash = ?', (hash_value,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO file_hashes (hash, filepath, filename, file_size) VALUES (?, ?, ?, ?)',
                (hash_value, file_str, file.name, file_size)
            )

        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Exception {e} - problème avec la base {db_path}")


def hash_exists_in_db(database: Path, hash_value: str) -> bool:
    """Vérifie si le hash existe dans la base de données."""
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM file_hashes WHERE hash = ?', (hash_value,))
            return c.fetchone() is not None
    except Exception as e:
        logger.warning(f'Exception {e} - Base de données {database} inaccessible')
        return False


def type_of_video(fichier: Path) -> str:
    """Détermine le type de vidéo selon son chemin."""
    return next((cat for cat in CATEGORIES if cat in fichier.parts), '')


def extract_file_infos(video: Video) -> Tuple[str, int, str, int, int, str]:
    """Extrait les informations d'un fichier vidéo avec guessit."""

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
    infos = guessit(file)

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

    # Création de la spécification
    spec = ' '.join(filter(None, [lang, codec, resol]))
    spec = ' '.join(spec.split())

    if not title:
        logger.warning(f'Pas de titre détecté pour {video.complete_path_original.name}')

    return title, year, season_episode, season, episode, spec


def handle_unsupported_genres(video: Video, detected_genres: List[str]) -> Video:
    """
    Gère les cas où des genres détectés ne sont pas supportés par la vidéothèque.
    """
    # Genres supportés par la vidéothèque
    supported_genres = {
        "Action & Aventure", "Animation", "Comédie", "Comédie dramatique",
        "Policier", "Drame", "Films pour enfants", "Fantastique",
        "Historique", "Horreur", "SF", "Thriller", "Western",
        "Guerre & espionnage"
    }

    # Vérifier si on a des genres supportés
    valid_genres = [genre for genre in detected_genres if genre in supported_genres]
    unsupported_genres = [genre for genre in detected_genres if genre not in supported_genres]

    # Si on a au moins un genre supporté, on continue normalement
    if valid_genres:
        video.list_genres = valid_genres
        if unsupported_genres:
            logger.info(f"Genres ignorés (non supportés): {', '.join(unsupported_genres)}")
        return video

    # Si tous les genres sont non supportés, demander à l'utilisateur
    if unsupported_genres:
        console.print(f"\n[yellow]⚠️  Genres détectés non supportés par la vidéothèque :[/yellow]")
        console.print(f"[dim]{', '.join(unsupported_genres)}[/dim]")

        # Proposer des correspondances intelligentes
        suggested_genre = suggest_genre_mapping(unsupported_genres)
        if suggested_genre:
            console.print(
                f"\n[cyan]💡 Suggestion basée sur '{unsupported_genres[0]}' :[/cyan] [bold]{suggested_genre}[/bold]")

            # Demander confirmation de la suggestion
            choice = input("➤ Accepter cette suggestion ? (Entrée=oui, n=choisir manuellement) : ").strip().lower()

            if choice != 'n' and choice != 'non':
                video.list_genres = [suggested_genre]
                video.genre = suggested_genre
                console.print(f"[green]✓ Genre assigné : {suggested_genre}[/green]")
                return video

        # Choix manuel si suggestion refusée ou inexistante
        console.print(f"\n[bold cyan]📂 Quel genre attribuer à '{video.title_fr}' ?[/bold cyan]")
        selected_genre = choose_genre_manually("Films")

        if selected_genre:
            video.list_genres = [selected_genre]
            video.genre = selected_genre
            console.print(f"[green]✓ Genre assigné manuellement : {selected_genre}[/green]")
        else:
            # Si aucun genre choisi, marquer comme non détecté
            video.list_genres = ["Non détecté"]
            video.genre = "Non détecté"
            console.print("[yellow]⚠️  Aucun genre sélectionné, marqué comme 'Non détecté'[/yellow]")

    return video


def suggest_genre_mapping(unsupported_genres: List[str]) -> str:
    """
    Suggère un genre supporté basé sur les genres non supportés détectés.
    """
    # Mapping des genres non supportés vers des genres supportés
    genre_mapping = {
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

        # Crime (différent de Policier)
        'crime': 'Policier',
        'criminal': 'Policier',

        # Mystery
        'mystery': 'Thriller',
        'mystère': 'Thriller',
        'mysterious': 'Thriller',

        # Adventure (si pas combiné avec Action)
        'adventure': 'Action & Aventure',
        'aventure': 'Action & Aventure',

        # Family
        'family': 'Films pour enfants',
        'famille': 'Films pour enfants',

        # Biography/Documentary
        'biography': 'Drame',
        'biographical': 'Drame',
        'biographie': 'Drame',

        # Sport
        'sport': 'Drame',
        'sports': 'Drame',

        # News (peu probable mais au cas où)
        'news': 'Drame',
        'actualités': 'Drame',
    }

    # Chercher le premier genre mappé
    for genre in unsupported_genres:
        genre_lower = genre.lower()
        if genre_lower in genre_mapping:
            return genre_mapping[genre_lower]

        # Recherche partielle (pour gérer les variations)
        for unsupported, supported in genre_mapping.items():
            if unsupported in genre_lower or genre_lower in unsupported:
                return supported

    # Si aucune correspondance, retourner Drame par défaut pour les genres narratifs
    narrative_indicators = ['drama', 'story', 'film', 'movie', 'drame', 'histoire']
    for genre in unsupported_genres:
        for indicator in narrative_indicators:
            if indicator in genre.lower():
                return 'Drame'

    # Aucune suggestion
    return ""


def query_movie_database(name: str, date: int, no_date: bool,
                         complete_name: str, type_video: str, video_file_path: Path = None,
                         occurence: int = 1) -> Tuple[str, List[str], int]:
    """
    Interroge une base de données de films/séries avec gestion de la visualisation.
    """

    def handle_error(full_name: str, date_: int, no_date_: bool,
                     video_type: str, occur: int) -> Tuple[str, List[str], int]:
        """Gère les cas où aucun résultat n'est trouvé avec option de conservation du nom."""
        if occur < 4:
            console.print(f"\n[bold red]❌ '{name}' n'a pas été trouvé dans la base[/bold red]")
            console.print(f"[yellow]Fichier original :[/yellow] [dim]{full_name}[/dim]")
            console.print(f"[yellow]Tentative {occur}/3[/yellow]")

            # Options étendues
            console.print("\n[bold cyan]Que souhaitez-vous faire ?[/bold cyan]")

            options_text = (
                "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow] du titre\n"
                "[bold blue]k[/bold blue] = [blue]GARDER LE NOM[/blue] et choisir le genre\n"  # 🆕 Nouvelle option
            )

            # Ajouter l'option de visualisation si le fichier existe
            if video_file_path and video_file_path.exists():
                options_text += "[bold magenta]v[/bold magenta] = [magenta]VISIONNER[/magenta] le fichier\n"

            options_text += (
                "[bold red]s[/bold red] = [red]SKIP[/red] (ignorer ce fichier)\n"
                "[bold dim]r[/bold dim] = [dim]RETRY[/dim] avec le même titre"
            )

            console.print(Panel.fit(
                options_text,
                title="🎛️  Options disponibles",
                border_style="cyan"
            ))

            while True:
                try:
                    response = input("➤ Votre choix : ").strip().lower()

                    if response == 'm' or response == 'manual' or response == 'manuel':
                        # Saisie manuelle
                        console.print("\n[bold yellow]📝 SAISIE MANUELLE[/bold yellow]")
                        console.print("[dim]Tapez 'cancel' pour annuler, 'skip' pour ignorer[/dim]")

                        while True:
                            new_name = input('➤ Titre exact du film/série : ').strip()

                            if new_name.lower() == 'cancel':
                                console.print("[yellow]Retour aux options[/yellow]")
                                break
                            elif new_name.lower() == 'skip':
                                logger.info(f"Fichier ignoré par l'utilisateur : {full_name}")
                                return '', [], date_
                            elif new_name:
                                console.print(f"[green]✓ Nouvelle recherche avec : '{new_name}'[/green]")
                                occur += 1
                                return query_movie_database(new_name, date_, no_date_, full_name, video_type,
                                                            video_file_path, occur)
                            else:
                                console.print("[red]Veuillez saisir un titre valide, 'cancel' ou 'skip'[/red]")

                        # Retour aux options après cancel
                        console.print(f"\n[bold cyan]'{name}' non trouvé - Que faire ?[/bold cyan]")
                        console.print("[dim]m=manuel | v=visionner | s=skip | r=retry[/dim]")
                        continue

                    elif response == 'k' or response == 'keep' or response == 'garder':
                        # 🆕 Nouvelle option : Garder le nom et choisir le genre
                        console.print("\n[bold blue]📝 CONSERVATION DU NOM ORIGINAL[/bold blue]")

                        # Extraction du titre et de l'année depuis le nom du fichier
                        file_stem = Path(full_name).stem

                        # Essayer d'extraire le titre proprement
                        clean_title = extract_title_from_filename(file_stem)

                        console.print(f"[green]Titre extrait :[/green] [bold]{clean_title['title']}[/bold]")
                        if clean_title['year']:
                            console.print(f"[blue]Année détectée :[/blue] [bold]{clean_title['year']}[/bold]")

                        # Demander confirmation du titre
                        title_ok = input(
                            f"➤ Confirmer le titre '{clean_title['title']}' ? (Entrée=oui, autre=modifier) : ").strip()

                        if title_ok:
                            # Modifier le titre
                            clean_title['title'] = input("➤ Nouveau titre : ").strip()
                            if not clean_title['title']:
                                console.print("[red]Titre obligatoire, retour aux options[/red]")
                                continue

                        # Demander l'année si pas détectée
                        if not clean_title['year']:
                            year_input = input("➤ Année du film (optionnel) : ").strip()
                            if year_input and year_input.isdigit():
                                clean_title['year'] = int(year_input)

                        # Choisir le genre
                        selected_genre = choose_genre_manually(video_type)
                        if not selected_genre:
                            console.print("[yellow]Aucun genre sélectionné, retour aux options[/yellow]")
                            continue

                        console.print(f"[green]✓ Fichier conservé avec le genre '{selected_genre}'[/green]")
                        return clean_title['title'], [selected_genre], clean_title['year'] or date_

                    # ... autres options existantes (v, s, r) ...
                    elif response == 'v' or response == 'view' or response == 'visionner':
                        # Visualisation
                        if not video_file_path or not video_file_path.exists():
                            console.print("[red]❌ Fichier vidéo non accessible pour la visualisation[/red]")
                            continue

                        if launch_video_player(video_file_path):
                            wait_for_user_after_viewing()

                            # Options après visionnage
                            console.print(f"\n[bold cyan]Après visionnage, quel est le titre ?[/bold cyan]")
                            manual_title = input("➤ Titre exact (ou 'skip' pour ignorer) : ").strip()

                            if manual_title.lower() == 'skip' or not manual_title:
                                return '', [], date_
                            else:
                                occur += 1
                                return query_movie_database(manual_title, date_, no_date_, full_name, video_type,
                                                            video_file_path, occur)
                        else:
                            console.print("[yellow]Échec du lancement, retour aux options...[/yellow]")
                            continue

                    elif response == 's' or response == 'skip':
                        # Skip
                        console.print("[red]⏭️  Fichier ignoré[/red]")
                        logger.info(f"Fichier ignoré par l'utilisateur : {full_name}")
                        return '', [], date_

                    elif response == 'r' or response == 'retry' or response == '':
                        # Retry avec le même titre
                        console.print("[dim]🔄 Nouvelle tentative avec le même titre[/dim]")
                        occur += 1
                        return query_movie_database(name, date_, no_date_, full_name, video_type, video_file_path,
                                                    occur)

                    else:
                        console.print(f"[yellow]⚠️  Réponse '{response}' non reconnue[/yellow]")
                        console.print("[dim]Options valides : m, v, s, r[/dim]")
                        continue

                except (KeyboardInterrupt, EOFError):
                    console.print("\n[red]Interruption par l'utilisateur[/red]")
                    return '', [], date_
                except Exception as e:
                    logger.warning(f"Erreur lors de la saisie : {e}")
                    return '', [], date_

        # Après 3 tentatives
        console.print(f"[red]❌ Impossible d'identifier '{name}' après 3 tentatives[/red]")
        console.print(f"[yellow]Le fichier sera placé dans 'non détectés'[/yellow]")
        return '', [], date_

    # Reste de la fonction query_movie_database (fonctions imbriquées et code principal)
    def get_release_date(movie_: dict) -> int:
        release_date = movie_.get("release_date") or movie_.get("first_air_date", '')
        return int(release_date[:4]) if release_date else 0

    def is_match(total_results: int, date_: int, found_date_: int, no_date_: bool) -> bool:
        return total_results == 1 or date_ == found_date_ or no_date_ or found_date_ == 0

    def get_movie_name(movie_: dict, video_type: str) -> str:
        return movie_["title"] if video_type in FILMANIM else (movie_["name"] or movie_["original_name"])

    def get_unique_genres(movie_: dict) -> List[str]:
        return list(dict.fromkeys(GENRES.get(int(g), "N/A") for g in movie_.get("genre_ids", [])))

    # Code principal de query_movie_database...
    if not TMDB_API_KEY:
        logger.error("Clé API TMDB manquante. Impossible de continuer.")
        exit(1)

    cache = CacheDB()
    cache_key = f"{type_video}-{name}-{date}"
    cached_data = cache.get_tmdb(cache_key)

    if cached_data:
        json_data = cached_data
    else:
        base = Tmdb()
        json_data = base.find_content(name, type_video)
        if json_data is None:
            logger.error("Impossible de se connecter à l'API TMDB. Arrêt du script.")
            cache.close()
            exit(1)
        if json_data:
            cache.set_tmdb(cache_key, json_data)

    cache.close()

    if not json_data or json_data['total_results'] == 0:
        return handle_error(complete_name, date, no_date, type_video, occurence)

    # Parcourir les résultats
    for movie in json_data['results']:
        found_date = get_release_date(movie)

        if is_match(json_data['total_results'], date, found_date, no_date):
            temp_name = get_movie_name(movie, type_video)
            temp_list_genre = get_unique_genres(movie)

            user_response = user_confirms_match(complete_name, temp_name, found_date, temp_list_genre, video_file_path)

            if user_response is True:
                return temp_name, temp_list_genre, found_date
            elif isinstance(user_response, str):
                console.print(f"[blue]🔄 Nouvelle recherche avec le titre manuel : '{user_response}'[/blue]")
                return query_movie_database(user_response, date, no_date, complete_name, type_video, video_file_path,
                                            occurence + 1)

    return handle_error(complete_name, date, no_date, type_video, occurence)

def user_confirms_match(complete_name_: str, tmp_name: str, found_date_: int, tmp_list_genre: List[str],
                        video_file_path: Path = None) -> Union[bool, str]:
    """
    Version classique avec input() - Plus fiable et permet Alt+Tab.
    """

    console.rule("[bold blue]Vérification de correspondance[/bold blue]")

    # Fichier original
    console.print(Panel(
        f"[yellow]{complete_name_}[/yellow]",
        title="📁 Fichier original",
        border_style="yellow"
    ))

    # Correspondance trouvée
    genres_str = ", ".join(tmp_list_genre) if tmp_list_genre else "Aucun genre"
    console.print(Panel(
        f"[green]🎬 Titre :[/green] [bold]{tmp_name}[/bold]\n"
        f"[blue]📅 Année :[/blue] [bold]{found_date_ if found_date_ else 'N/A'}[/bold]\n"
        f"[purple]🎭 Genres :[/purple] [italic]{genres_str}[/italic]",
        title="✅ Correspondance trouvée",
        border_style="green"
    ))

    # Options de choix
    console.print("\n[bold cyan]Cette correspondance est-elle correcte ?[/bold cyan]")

    options_text = (
        "[bold green]Entrée[/bold green] = [green]ACCEPTER[/green]\n"
        "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow]\n"
    )

    # Ajouter l'option de visualisation si le fichier existe
    if video_file_path and video_file_path.exists():
        options_text += "[bold magenta]v[/bold magenta] = [magenta]VISIONNER[/magenta]\n"

    options_text += "[bold red]n[/bold red] = [red]NON[/red] (chercher le suivant)"

    console.print(Panel.fit(
        options_text,
        title="🎛️  Options disponibles",
        border_style="cyan"
    ))

    while True:
        try:
            response = input("➤ Votre choix : ").strip().lower()

            if response == '' or response == 'y' or response == 'yes' or response == 'oui':
                # Entrée ou confirmation explicite = Accepter
                console.print("[green]✓ Correspondance acceptée[/green]")
                console.rule()
                return True

            elif response == 'm' or response == 'manual' or response == 'manuel':
                # Mode manuel
                console.print("\n[bold yellow]📝 MODE SAISIE MANUELLE[/bold yellow]")
                console.print("[dim]Tapez 'cancel' pour annuler et revenir aux suggestions[/dim]")

                while True:
                    manual_title = input("➤ Titre exact du film/série : ").strip()

                    if manual_title.lower() == 'cancel':
                        console.print("[yellow]Retour aux suggestions automatiques[/yellow]")
                        break
                    elif manual_title:
                        console.print(f"[green]✓ Titre manuel accepté : '{manual_title}'[/green]")
                        console.rule()
                        return manual_title
                    else:
                        console.print("[red]Veuillez saisir un titre valide ou 'cancel'[/red]")

                # Retour aux options après cancel
                console.print(f"\n[bold cyan]Correspondance pour '{tmp_name}' ?[/bold cyan]")
                console.print("[dim]Entrée=accepter | m=manuel | v=visionner | n=non[/dim]")
                continue

            elif response == 'v' or response == 'view' or response == 'visionner':
                # Mode visualisation
                if not video_file_path or not video_file_path.exists():
                    console.print("[red]❌ Fichier vidéo non accessible pour la visualisation[/red]")
                    console.print("[dim]Retour aux options...[/dim]")
                    continue

                if launch_video_player(video_file_path):
                    wait_for_user_after_viewing()

                    # Proposer les options après visionnage
                    console.print(f"\n[bold cyan]Après visionnage, '{tmp_name}' correspond-il ?[/bold cyan]")
                    console.print(Panel.fit(
                        "[bold green]Entrée[/bold green] = [green]ACCEPTER[/green]\n"
                        "[bold yellow]m[/bold yellow] = [yellow]SAISIE MANUELLE[/yellow]\n"
                        "[bold red]n[/bold red] = [red]NON[/red]",
                        title="🎛️  Après visionnage",
                        border_style="cyan"
                    ))
                    continue
                else:
                    console.print("[yellow]Échec du lancement du lecteur, retour aux options...[/yellow]")
                    continue

            elif response == 'n' or response == 'no' or response == 'non' or response == 'next':
                # Refuser et chercher le suivant
                console.print("[red]✗ Correspondance refusée - Recherche du suivant[/red]")
                console.rule()
                return False

            else:
                # Réponse non reconnue
                console.print(f"[yellow]⚠️  Réponse '{response}' non reconnue[/yellow]")
                console.print("[dim]Options valides : Entrée, m, v, n[/dim]")
                continue

        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Interruption par l'utilisateur[/red]")
            console.rule()
            return False
        except Exception as e:
            logger.warning(f"Erreur lors de la saisie : {e}")
            console.print("[red]Erreur de saisie, veuillez réessayer[/red]")
            continue


def wait_for_user_after_viewing():
    """Version simplifiée de l'attente après visionnage."""
    console.print("\n[bold yellow]📺 Visionnage en cours...[/bold yellow]")
    input("[dim]Appuyez sur Entrée quand vous avez terminé le visionnage[/dim]")
    console.print("[green]✅ Visionnage terminé[/green]")


def extract_title_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extrait le titre et l'année d'un nom de fichier en nettoyant les specs techniques.
    Retourne un dictionnaire avec 'title' et 'year'.
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


def choose_genre_manually(video_type: str) -> str:
    """
    Permet à l'utilisateur de choisir manuellement un genre.
    """
    if video_type not in FILMANIM:
        # Pour les séries, pas de genre nécessaire
        return ""

    # Liste des genres disponibles pour les films
    available_genres = [
        "Action & Aventure", "Animation", "Comédie", "Comédie dramatique",
        "Policier", "Drame", "Films pour enfants", "Fantastique",
        "Historique", "Horreur", "SF", "Thriller", "Western",
        "Guerre & espionnage", "Non détecté"
    ]

    console.print("\n[bold cyan]📂 Sélection du genre :[/bold cyan]")

    # Affichage en colonnes pour plus de clarté
    from rich.columns import Columns
    from rich.panel import Panel

    genre_panels = []
    for i, genre in enumerate(available_genres, 1):
        color = "green" if genre not in ["Non détecté"] else "yellow"
        genre_panels.append(Panel(f"[{color}]{i:2d}. {genre}[/{color}]", expand=False))

    console.print(Columns(genre_panels, equal=False, expand=False))

    while True:
        try:
            choice = input(f"\n➤ Choisissez un genre (1-{len(available_genres)}, ou nom du genre) : ").strip()

            if not choice:
                console.print("[yellow]Aucun choix, veuillez sélectionner un genre[/yellow]")
                continue

            # Choix par numéro
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(available_genres):
                    selected = available_genres[num - 1]
                    console.print(f"[green]✓ Genre sélectionné : {selected}[/green]")
                    return selected
                else:
                    console.print(f"[red]Numéro invalide. Choisissez entre 1 et {len(available_genres)}[/red]")
                    continue

            # Choix par nom (recherche floue)
            choice_lower = choice.lower()
            for genre in available_genres:
                if choice_lower in genre.lower() or genre.lower().startswith(choice_lower):
                    console.print(f"[green]✓ Genre sélectionné : {genre}[/green]")
                    return genre

            console.print(f"[red]Genre '{choice}' non trouvé. Utilisez le numéro ou le nom exact[/red]")

        except (ValueError, KeyboardInterrupt):
            console.print("\n[yellow]Sélection annulée[/yellow]")
            return ""
        except Exception as e:
            logger.warning(f"Erreur lors de la sélection du genre : {e}")
            return ""


def test_user_input():
    """Test simple de la fonction de confirmation."""
    console.print("[bold blue]🧪 Test de la fonction de confirmation[/bold blue]")
    result = user_confirms_match(
        "The.Amateur.2025.MULTi.VF2.1080p.WEBrip.EAC3.5.1.x265-TyHD.mkv",
        "The Amateur",
        2025,
        ["Thriller", "Action & Aventure"]
    )
    console.print(f"[bold]Résultat du test: {'✅ Accepté' if result else '❌ Refusé'}[/bold]")


def media_info(video: Video) -> str:
    """Extrait les informations techniques du fichier via MediaInfo."""
    # ✅ Si les specs existent déjà et semblent complètes, ne pas les remplacer
    if video.spec and len(video.spec.split()) >= 3:
        logger.debug(f"Specs existantes conservées: {video.spec}")
        return video.spec

    def is_french(list_: List[str]) -> bool:
        return any(re.search(r'french', item.lower()) for item in list_)

    try:
        mi = MediaInfo.parse(video.complete_path_original)
    except Exception as e:
        logger.warning(f"Erreur MediaInfo pour {video.complete_path_original}: {e}")
        return video.spec  # ✅ Retourner les specs existantes en cas d'erreur

    if not mi.tracks:
        return video.spec

    nb_audio = mi.tracks[0].count_of_audio_streams
    if not nb_audio:
        return video.spec
    try:
        languages = mi.tracks[0].audio_language_list.lower().split(' / ') if mi.tracks[0].audio_language_list else [
            'french']
    except Exception:
        languages = ['french']

    try:
        subtitles = mi.tracks[0].text_language_list.lower().split(' / ') if mi.tracks[0].text_language_list else []
    except Exception:
        subtitles = []

    # Informations vidéo
    if len(mi.tracks) > 1:
        width = mi.tracks[1].width or 0
        height = mi.tracks[1].height or 0
        codec = mi.tracks[1].format or ''
    else:
        width = height = 0
        codec = ''

    if 'AVC' in codec:
        codec = 'x264'

    spec = ''

    # Détermination de la langue
    if int(nb_audio) > 1:
        if is_french(subtitles):
            if is_french(languages):
                spec += 'MULTi '
            else:
                spec += 'VOSTFR '
        else:
            spec += 'MULTi '
    else:
        if is_french(languages):
            spec += 'FR '
        elif is_french(subtitles):
            spec += 'VOSTFR '
        else:
            spec += 'VO '

    spec += codec

    # Détermination de la résolution
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


def classify_movie(video: Video) -> Video:
    """
    Classifie automatiquement une vidéo en prenant le premier genre approprié.
    """
    if not video.list_genres:
        video.genre = 'Non détecté'
        return video

    # Si déjà marqué comme non détecté, garder tel quel
    if video.list_genres[0] == "Non détecté":
        video.genre = "Non détecté"
        return video

    video_genres = set(video.list_genres)

    # Traitement spécial pour l'animation
    if 'Animation' in video_genres:
        return classify_animation(video)

    # Combinaison spécifique de genres
    if {'Drame', 'Comédie'}.issubset(video_genres):
        video.genre = 'Comédie dramatique'
        return video

    # Priorité de sélection des genres
    matching_genres = PRIORITY_GENRES.intersection(video_genres)
    if matching_genres:
        video.genre = next(iter(matching_genres))
        return video

    # Prendre automatiquement le premier genre (évite les choix manuels répétitifs)
    video.genre = video.list_genres[0]
    logger.info(f"Genre automatiquement sélectionné pour {video.title_fr}: {video.genre}")

    return video


def classify_animation(video: Video) -> Video:
    """Classifie spécifiquement les films d'animation."""
    if len(video.list_genres) == 1:
        video.genre = 'Animation/Adultes'
    elif 'Films pour enfants' in video.list_genres:
        video.genre = 'Animation/Animation Enfant'
    else:
        # Choix automatique basé sur la présence de certains mots-clés
        video.genre = 'Animation/Animation Enfant'
        logger.info(f"Genre animation automatiquement sélectionné: {video.genre}")

    video.list_genres = [video.genre if x == 'Animation' else x for x in video.list_genres]
    return video


def set_fr_title_and_category(video: Video) -> Video:
    """Définit le titre français et la catégorie d'une vidéo."""
    original_spec = video.spec
    original_filename = video.complete_path_original.name

    no_date = not bool(video.date_film)
    name_fr, video.list_genres, date = query_movie_database(
        str(video.title),
        video.date_film,
        no_date,
        original_filename,
        video.type_file,
        video.complete_path_original
    )

    video.list_genres = list(set(video.list_genres))  # Supprime les doublons

    # 🚫 Ne plus supprimer automatiquement les genres "non désirés"
    # unwanted_genres = {'Romance', 'Téléfilm', 'Musique'}
    # video.list_genres = [g for g in video.list_genres if g not in unwanted_genres]

    video.title_fr = normalize(name_fr)
    video.name_without_article = remove_article(video.title_fr).lower()
    video.date_film = date

    # Restaurer les specs originales
    video.spec = original_spec

    if video.is_film_anim():
        # 🆕 Gérer les genres non supportés AVANT la classification
        video = handle_unsupported_genres(video, video.list_genres)

        # Seulement classifier si on a des genres supportés
        if video.list_genres and video.list_genres[0] != "Non détecté":
            video = classify_movie(video)
    else:
        video.genre = ''

    return video


def in_range(value: str, start: str, end: str) -> bool:
    """Vérifie si une valeur est dans une plage alphabétique."""
    return start <= value <= end


def inflate(start: str, end: str, length: int) -> Tuple[str, str]:
    """Étend les chaînes à une longueur donnée pour la comparaison."""
    return start.ljust(length, 'a'), end.ljust(length, 'z')


def find_directory_for_video(video: Video, root_folder: Path) -> Path:
    """Détermine le sous-dossier approprié pour un titre donné."""
    cache_key = (str(video.complete_path_original), str(root_folder))
    cached_result = subfolder_cache.get(cache_key)
    if cached_result:
        return cached_result

    # ✅ Cas spécial pour les FILMS non détectés seulement
    if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
        non_detectes_dir = root_folder / 'non détectés'
        subfolder_cache.set(cache_key, non_detectes_dir)
        return non_detectes_dir

    title = video.name_without_article
    inflated_ranges: Dict[str, Tuple[str, str]] = {}

    def find_deepest_matching_folder(current_folder: Path, remaining_title: str) -> Path:
        best_match = current_folder
        try:
            for item in current_folder.iterdir():
                if not item.is_dir():
                    continue

                item_name_lower = item.name.lower()
                if '-' in item_name_lower and not (' - ' in item_name_lower):
                    start, end = item_name_lower.split('-', 1)
                    compare_length = max(len(start), len(end))
                    if item_name_lower not in inflated_ranges:
                        if compare_length > 1:
                            inflated_ranges[item_name_lower] = inflate(start, end, compare_length)
                        else:
                            inflated_ranges[item_name_lower] = (start, end)
                    start, end = inflated_ranges[item_name_lower]
                    if not in_range(remaining_title[:compare_length], start[:compare_length], end[:compare_length]):
                        continue
                elif not remaining_title.startswith(item.name.lower()):
                    continue

                if video.type_file == 'Séries':
                    series_folder = item / remaining_title
                    if series_folder.exists() and series_folder.is_dir():
                        return series_folder

                deeper_match = find_deepest_matching_folder(item, remaining_title)
                return deeper_match if deeper_match != item else item
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Erreur d'accès au dossier {current_folder}: {e}")

        return best_match

    result = find_deepest_matching_folder(root_folder, title)

    # ✅ Si pas de correspondance trouvée, utiliser "#" pour les séries, "non détectés" pour les films
    if result == root_folder:
        if video.is_film_anim():
            result = root_folder / 'non détectés'
        else:
            result = root_folder / '#'  # Comportement original pour les séries

    subfolder_cache.set(cache_key, result)
    return result

def find_similar_file(video: Video, storage_dir: Path, similarity_threshold: int = 80, year_tolerance: int = 1) -> \
Optional[Path]:
    """Recherche un fichier similaire dans la structure de dossiers."""
    if video.is_animation():
        folder = storage_dir / 'Films'
    else:
        folder = storage_dir / video.type_file

    root_folders = [folder / genre for genre in video.list_genres if genre]

    for root_folder in root_folders:
        if not root_folder.exists():
            continue
        subfolder = find_directory_for_video(video, root_folder)
        similar_file = find_similar_file_in_folder(video, subfolder, similarity_threshold, year_tolerance)
        if similar_file:
            return similar_file
    return None


def find_similar_file_in_folder(video: Video, sub_folder: Path,
                                similarity_threshold: int = 80, year_tolerance: int = 1) -> Optional[Path]:
    """Recherche un fichier similaire dans un dossier spécifique."""

    def extract_title_year(filename: Path) -> Tuple[Optional[str], Optional[int]]:
        filename_str = filename.name
        match = re.match(r"(.+?)\s*\((\d{4})\)", filename_str)
        if match:
            title = match.group(1).strip()
            year = int(match.group(2))
            return title.lower(), year
        return None, None

    if not sub_folder.exists():
        return None

    best_match = None
    highest_similarity = 0
    video_title = video.title_fr.lower()

    try:
        for file in sub_folder.rglob('*'):
            if not file.is_file():
                continue

            file_title, file_year = extract_title_year(file)
            if not file_title or not file_year:
                continue

            similarity = fuzz.ratio(video_title, file_title)
            if similarity <= similarity_threshold or similarity <= highest_similarity:
                continue

            if abs(video.date_film - file_year) > year_tolerance:
                continue

            best_match = file
            highest_similarity = similarity
    except (FileNotFoundError, PermissionError) as e:
        logger.warning(f"Erreur d'accès au dossier {sub_folder}: {e}")

    return best_match


def handle_similar_file(new_file_path: Path, existing_file_path: Path, waiting_folder: Path, storage_dir: Path) -> \
Optional[Path]:
    """Gère le cas où un fichier similaire est trouvé."""
    console.print(f"[yellow]⚠️  Un fichier similaire existe déjà :[/yellow]")
    console.print(f"   [red]Existant:[/red] {'/'.join(existing_file_path.parts[-3:])}")
    console.print(f"   [green]Nouveau:[/green] {new_file_path.name}")

    choice = input("""Que souhaitez-vous faire ?
    1: Garder l'ancien fichier (déplacer le nouveau vers attente)
    2: Remplacer par le nouveau (déplacer l'ancien vers attente)
    3: Conserver les deux
Votre choix (1/2/3): """).strip()

    match choice:
        case "1":
            console.print(f"[blue]→ Déplacement du nouveau fichier vers l'attente[/blue]")
            try:
                # Déplacement vers le NAS puis création du symlink d'attente
                waiting_nas_file = storage_dir / 'waiting' / new_file_path.name
                waiting_nas_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(new_file_path), str(waiting_nas_file))
                create_symlink(waiting_nas_file, waiting_folder / new_file_path.name)
                logger.info(f"Fichier déplacé vers l'attente: {waiting_nas_file}")
            except Exception as e:
                logger.error(f"Erreur lors du déplacement: {e}")
            return existing_file_path

        case "2":
            console.print(f"[blue]→ Remplacement de l'ancien fichier[/blue]")
            try:
                # Déplacement de l'ancien vers l'attente
                waiting_nas_file = storage_dir / 'waiting' / existing_file_path.name
                waiting_nas_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(existing_file_path), str(waiting_nas_file))
                create_symlink(waiting_nas_file, waiting_folder / existing_file_path.name)
                logger.info(f"Ancien fichier déplacé vers l'attente: {waiting_nas_file}")
            except Exception as e:
                logger.error(f"Erreur lors du déplacement de l'ancien fichier: {e}")
            return new_file_path

        case "3":
            console.print("[blue]→ Conservation des deux fichiers[/blue]")
            return None

        case _:
            console.print("[red]Choix non valide. Conservation des deux fichiers par défaut.[/red]")
            return None



def aplatir_repertoire_series(repertoire_initial: Path) -> None:
    """Aplatit l'arborescence des séries en déplaçant les fichiers vers le niveau supérieur."""

    def deplacer_fichiers(repertoire_source: Path, repertoire_destination: Path) -> None:
        try:
            for fichier in repertoire_source.iterdir():
                if fichier.is_file():
                    chemin_destination = repertoire_destination / fichier.name
                    if not chemin_destination.exists():
                        shutil.move(str(fichier), str(chemin_destination))
        except Exception as e:
            logger.warning(f"Erreur lors du déplacement de fichiers: {e}")

    def traiter_sous_repertoires_series(repertoire_series: Path) -> None:
        try:
            for repertoire_premier_niveau in repertoire_series.iterdir():
                if repertoire_premier_niveau.is_dir():
                    for s_rep in repertoire_premier_niveau.iterdir():
                        if s_rep.is_dir():
                            deplacer_fichiers(s_rep, repertoire_premier_niveau)
                            try:
                                s_rep.rmdir()
                            except OSError as e:
                                logger.warning(f"Impossible de supprimer {s_rep}: {e}")
        except Exception as e:
            logger.warning(f"Erreur lors du traitement des séries: {e}")

    try:
        for sous_repertoire in repertoire_initial.glob('**/Séries'):
            traiter_sous_repertoires_series(sous_repertoire)
    except Exception as e:
        logger.warning(f"Erreur lors de l'aplatissement des séries: {e}")


def move_file_new_nas(video: Video, storage_dir: Path, dry_run: bool = False):
    """Déplace le fichier vers le NAS final (ou simule si dry_run)."""
    origine = video.complete_path_original

    try:
        sub_dir = str(video.complete_path_temp_links).split('work/', 1)[1]
    except IndexError:
        sub_dir = str(video.complete_path_temp_links)

    destination = storage_dir / sub_dir

    if dry_run:
        console.print(
            f"[dim]🔍 SIMULATION - Déplacement :[/dim] [yellow]{origine.name}[/yellow] → [cyan]{destination}[/cyan]")
        logger.info(f'SIMULATION - Transfert de {origine.name} vers {destination}')

        # Simulation de la mise à jour du lien symbolique
        logger.debug(f'SIMULATION - Lien symbolique mis à jour: {video.complete_path_temp_links} -> {destination}')
        return

    # Code normal existant...
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        if origine.exists():
            # Vérifier si le fichier de destination existe déjà
            if destination.exists():
                logger.warning(f'Le fichier de destination existe déjà: {destination}')
                if origine.stat().st_size == destination.stat().st_size:
                    logger.info(f'Fichier identique détecté, suppression de la source: {origine}')
                    origine.unlink()
                else:
                    counter = 1
                    base_name = destination.stem
                    extension = destination.suffix
                    while destination.exists():
                        destination = destination.parent / f"{base_name}_{counter}{extension}"
                        counter += 1
                    logger.info(f'Renommage du fichier vers: {destination}')
                    shutil.move(str(origine), str(destination))
            else:
                shutil.move(str(origine), str(destination))
                logger.info(f'Fichier transféré vers le NAS: {destination}')
        else:
            logger.warning(f'Fichier source introuvable: {origine}')
            return

        # Mise à jour du lien symbolique
        try:
            if video.complete_path_temp_links.exists() or video.complete_path_temp_links.is_symlink():
                video.complete_path_temp_links.unlink()
            video.complete_path_temp_links.symlink_to(destination)
            logger.debug(f'Lien symbolique mis à jour: {video.complete_path_temp_links} -> {destination}')
        except Exception as e:
            logger.error(f'Erreur lors de la création du lien symbolique: {e}')

    except Exception as e:
        logger.error(f'Erreur lors du transfert de {origine}: {e}')


def copy_tree(temp_dir: Path, original_dir: Path, dry_run: bool = False):
    """Copie l'arborescence (ou simule si dry_run)."""
    if not temp_dir.exists() or not any(temp_dir.iterdir()):
        logger.warning('Aucun fichier à copier.')
        return

    if dry_run:
        console.print(
            f"[dim]🔍 SIMULATION - Copie arborescence :[/dim] [cyan]{temp_dir}[/cyan] → [cyan]{original_dir}[/cyan]")
        logger.info(f'SIMULATION - Copie de {temp_dir} vers {original_dir}')
        return

    # Code normal existant...
    try:
        if original_dir.exists():
            shutil.rmtree(original_dir, ignore_errors=True)
        shutil.copytree(temp_dir, original_dir, symlinks=True)
        logger.info(f"Copie effectuée de {temp_dir} vers {original_dir}")
    except Exception as e:
        logger.error(f"Erreur lors de la copie : {e}")
        exit(1)


def create_symlink(source: Path, destination: Path, dry_run: bool = False) -> None:
    """Crée un lien symbolique (ou simule si dry_run)."""
    if dry_run:
        logger.debug(f'SIMULATION - Lien symbolique : {source} -> {destination}')
        return

    # Code normal existant...
    try:
        if source.is_symlink():
            source = source.resolve()

        if destination.exists() or destination.is_symlink():
            destination.unlink()

        destination.symlink_to(source)
        logger.debug(f'Lien symbolique créé : {source} -> {destination}')

    except Exception as e:
        logger.warning(f"Erreur lors de la création du lien {source} -> {destination} : {e}")


def setup_working_directories(destination_dir: Path, dry_run: bool = False) -> Tuple[Path, Path, Path, Path]:
    """Configure et nettoie les répertoires de travail (ou simule si dry_run)."""
    work_dir = destination_dir.parent / "work"
    temp_dir = destination_dir.parent / "tmp"
    original_dir = destination_dir.parent / "original"
    waiting_folder = destination_dir.parent / "_a_virer"

    if dry_run:
        console.print(f"[dim]🔍 SIMULATION - Configuration des répertoires de travail[/dim]")
        return work_dir, temp_dir, original_dir, waiting_folder

    # Nettoyage des répertoires existants
    cleanup_directories(work_dir, temp_dir, original_dir)

    # Création du dossier d'attente
    waiting_folder.mkdir(exist_ok=True)

    return work_dir, temp_dir, original_dir, waiting_folder


def create_paths(file: Path, video: Video, temp_dir: Path, dry_run: bool = False):
    """Crée les chemins et liens symboliques temporaires (ou simule si dry_run)."""

    def reps_pattern(filename: Path, pattern: str) -> Tuple[Path, Path]:
        reps = filename.parts
        if 'Animation' in filename.parts:
            index = reps.index('Animation')
            pattern = '/'.join(reps[index - 1:index + 1])
        filename_str = str(filename)
        pattern = f'/{pattern}/'
        if pattern in filename_str:
            before, after = filename_str.split(pattern, 1)
            return Path(before), Path(after)
        else:
            logger.warning(f'Pattern {pattern} non trouvé dans {filename_str}')
            return Path(''), Path('')

    if video.is_film():
        temp_path = temp_dir / video.type_file
    elif video.is_animation():
        temp_path = temp_dir / 'Films' / video.type_file
    else:
        b_rep, s_rep = reps_pattern(video.complete_path_original, video.type_file)
        temp_path = temp_dir / video.type_file / s_rep.parent

    if dry_run:
        logger.debug(f'SIMULATION - Création du répertoire: {temp_path}')
        name = video.complete_path_original.name
        video.destination_file = temp_path / name
        logger.debug(f'SIMULATION - Nouveau lien: {file} -> {video.destination_file}')
        return

    temp_path.mkdir(parents=True, exist_ok=True)

    name = video.complete_path_original.name
    video.destination_file = temp_path / name
    create_symlink(file, video.destination_file)
    logger.debug(f'Nouveau lien créé: {video.destination_file}')


def rename_video(video: Video, dic_serie: dict, sub: str = '', work_dir: Path = None, dry_run: bool = False):
    """Renomme et déplace les vidéos dans le répertoire de travail (ou simule si dry_run)."""
    if not work_dir:
        work_dir = video.destination_file.parent.parent / "work"

    all_path = work_dir / sub if sub else work_dir

    if video.is_serie():
        items_serie = dic_serie.get(video.title_fr, '')
        if items_serie:
            all_path = all_path.parent / items_serie[4].stem / f'{items_serie[0]} ({items_serie[1]})'
        else:
            all_path = all_path / f'{video.title_fr} ({video.date_film})'

    if dry_run:
        if video.is_not_doc():
            video.complete_path_temp_links = all_path / video.formatted_filename
        else:
            _, end_path = str(video.complete_path_original).split(video.type_file, 1)
            video.complete_path_temp_links = all_path / end_path.lstrip('/')

        logger.debug(f"SIMULATION - Déplacement: {video.destination_file} -> {video.complete_path_temp_links}")
        return

    # Code normal existant...
    logger.debug(f"Déplacement vers: {all_path}")

    try:
        if video.is_not_doc():
            video.complete_path_temp_links = all_path / video.formatted_filename
        else:
            _, end_path = str(video.complete_path_original).split(video.type_file, 1)
            video.complete_path_temp_links = all_path / end_path.lstrip('/')

        video.complete_path_temp_links.parent.mkdir(parents=True, exist_ok=True)

        if video.destination_file.exists():
            if video.complete_path_temp_links.exists():
                logger.warning(f"Le fichier de destination existe déjà: {video.complete_path_temp_links}")
                video.complete_path_temp_links.unlink()

            video.destination_file.rename(video.complete_path_temp_links)
            logger.debug(f"Fichier renommé: {video.destination_file} -> {video.complete_path_temp_links}")
        else:
            logger.warning(f"Fichier source introuvable: {video.destination_file}")

    except Exception as e:
        logger.warning(f"Erreur lors du renommage de {video.formatted_filename}: {e}")


def cleanup_work_directory(work_dir: Path) -> None:
    """Nettoie les structures récursives dans le répertoire de travail."""
    if not work_dir.exists():
        return

    console.print("[blue]🧹 Nettoyage préventif du répertoire de travail...[/blue]")

    def remove_nested_saisons(path: Path) -> int:
        """Supprime les dossiers Saison imbriqués de manière récursive."""
        removed = 0

        try:
            for item in list(path.iterdir()):
                if item.is_dir():
                    # Si c'est un dossier Saison qui contient un autre dossier Saison
                    if re.match(r'Saison \d{2}', item.name):
                        for sub_item in list(item.iterdir()):
                            if sub_item.is_dir() and re.match(r'Saison \d{2}', sub_item.name):
                                # Déplacer les fichiers du sous-dossier vers le dossier parent
                                for file in sub_item.iterdir():
                                    if file.is_file():
                                        new_path = item / file.name
                                        file.rename(new_path)
                                        logger.debug(f"Fichier déplacé: {file} -> {new_path}")

                                # Supprimer le dossier Saison imbriqué
                                shutil.rmtree(sub_item)
                                removed += 1
                                logger.info(f"Dossier Saison imbriqué supprimé: {sub_item}")

                    # Récursion
                    removed += remove_nested_saisons(item)
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Erreur lors du nettoyage de {path}: {e}")

        return removed

    removed_count = remove_nested_saisons(work_dir)
    if removed_count > 0:
        console.print(f"[green]✅ {removed_count} dossiers Saison imbriqués supprimés[/green]")
    else:
        logger.debug("Aucun dossier Saison imbriqué trouvé")


def add_episodes_titles(list_of_videos: List[Video], rep_destination: Path, dry_run: bool = False) -> None:
    """Ajoute les titres d'épisodes et organise par saisons."""

    def format_and_rename(video_obj: Video, dry_run: bool = False) -> None:
        """Crée le sous-répertoire Saison XX seulement si nécessaire."""
        if video_obj.season == 0:
            return

        # Vérifier si on est déjà dans un dossier Saison
        current_path = video_obj.complete_path_temp_links
        current_parent = current_path.parent

        sequence_season = f'Saison {video_obj.season:02d}'

        # Si le parent ne contient pas déjà "Saison", on le crée
        if sequence_season not in str(current_parent):
            # Remonter jusqu'au dossier de la série (celui avec l'année)
            serie_folder = current_parent
            while serie_folder.parent and not re.search(r'\(\d{4}\)$', serie_folder.name):
                serie_folder = serie_folder.parent

            # Créer le dossier saison dans le dossier série
            complete_path_with_season = serie_folder / sequence_season
            new_file_path = complete_path_with_season / video_obj.formatted_filename

            if dry_run:
                logger.debug(f"SIMULATION - Création saison: {complete_path_with_season}")
                video_obj.complete_path_temp_links = new_file_path
            else:
                complete_path_with_season.mkdir(exist_ok=True)
                if current_path.exists():
                    current_path.rename(new_file_path)
                    video_obj.complete_path_temp_links = new_file_path
                    logger.debug(f"Fichier déplacé vers saison: {new_file_path}")
                else:
                    video_obj.complete_path_temp_links = new_file_path
        else:
            # On est déjà dans le bon dossier Saison, juste mettre à jour le nom
            if not dry_run and current_path.exists():
                new_path = current_parent / video_obj.formatted_filename
                if new_path != current_path:
                    current_path.rename(new_path)
                    video_obj.complete_path_temp_links = new_path

    def name_episode_with_real_search(video_obj: Video, serial: int, dry_run: bool = False) -> Tuple[Video, int]:
        """Version qui recherche les vrais titres même en simulation."""
        if not TVDB_API_KEY:
            logger.warning("Clé API TVDB manquante, impossible de récupérer les titres d'épisodes")
            return video_obj, serial

        cache = CacheDB()

        # Vérifier le cache d'abord
        cached_data = cache.get_tvdb(serial, video_obj.season, video_obj.episode)
        if cached_data and cached_data.get("episodeName"):
            episode_name = cached_data["episodeName"]
            ext = video_obj.complete_path_original.suffix
            video_obj.formatted_filename = (
                f"{video_obj.title_fr} ({video_obj.date_film}) {video_obj.sequence} "
                f"{episode_name} - {video_obj.spec}{ext}"
            )
            if dry_run:
                logger.debug(f"SIMULATION - Titre épisode (cache): {episode_name}")
            cache.close()
            return video_obj, serial

        # Recherche réelle même en dry_run pour avoir les vrais titres
        if dry_run:
            console.print(
                f"[dim]🔍 Recherche du titre pour {video_obj.title_fr} S{video_obj.season:02d}E{video_obj.episode:02d}"
                f"...[/dim]")

        databases = [
            tvdb_api.Tvdb(apikey=TVDB_API_KEY, language='fr', interactive=False),
            tvdb_api.Tvdb(apikey=TVDB_API_KEY, language='en', interactive=False)
        ]

        for lang_index, data_serie in enumerate(databases):
            try:
                if not serial:
                    try:
                        serial = data_serie[video_obj.title_fr]['id']
                        if dry_run:
                            logger.debug(f"SIMULATION - Série trouvée avec ID: {serial}")
                    except (tvdb_api.tvdb_shownotfound, KeyError):
                        logger.debug(
                            f"Série {video_obj.title_fr} non trouvée en {'français' if lang_index == 0 else 'anglais'}")
                        continue

                data_episode = data_serie[serial][video_obj.season][video_obj.episode]
                titre_episode = data_episode.get('episodeName', '')

                if titre_episode:
                    titre_episode = normalize(titre_episode)
                    ext = video_obj.complete_path_original.suffix
                    video_obj.formatted_filename = (
                        f'{video_obj.title_fr} ({video_obj.date_film}) {video_obj.sequence} '
                        f'{titre_episode} - {video_obj.spec}{ext}'
                    )

                    # Sauvegarder en cache
                    cache.set_tvdb(serial, video_obj.season, video_obj.episode, {"episodeName": titre_episode})

                    if dry_run:
                        console.print(f"[dim]✅ Trouvé: {titre_episode}[/dim]")
                    break

            except (tvdb_api.tvdb_shownotfound, tvdb_api.tvdb_episodenotfound,
                    tvdb_api.tvdb_seasonnotfound) as e:
                logger.warning(f'{video_obj.title_fr}: {type(e).__name__}')
                continue
            except Exception as e:
                logger.warning(f'Erreur TVDB pour {video_obj.title_fr}: {e}')
                continue

        cache.close()
        return video_obj, serial

    # Traitement des séries avec barre de progression
    done = {}
    series_to_process = [video for video in list_of_videos if video.is_serie() and video.season > 0]

    if not series_to_process:
        return

    mode_text = "SIMULATION - " if dry_run else ""
    with tqdm(series_to_process, desc=f"{mode_text}Titres d'épisodes", unit="épisode") as pbar:
        for video in pbar:
            pbar.set_postfix_str(f"{video.title_fr} S{video.season:02d}E{video.episode:02d}")

            num_serie = done.get(video.title_fr, 0)
            video, num_serie = name_episode_with_real_search(video, num_serie, dry_run)
            done[video.title_fr] = num_serie
            format_and_rename(video, dry_run)

def cleanup_recursive_symlinks(directory: Path) -> None:
    """Nettoie les liens symboliques récursifs et les dossiers vides."""
    if not directory.exists():
        return

    def remove_recursive_folders(path: Path, parent_name: str = None) -> bool:
        """Supprime les dossiers qui se répètent de manière récursive."""
        if not path.is_dir():
            return False

        removed_something = False

        for item in list(path.iterdir()):
            if item.is_dir():
                # Si le nom du dossier est identique au parent, c'est probablement récursif
                if parent_name and item.name == parent_name:
                    logger.warning(f"Suppression du dossier récursif: {item}")
                    try:
                        shutil.rmtree(item)
                        removed_something = True
                        continue
                    except Exception as e:
                        logger.error(f"Erreur lors de la suppression de {item}: {e}")

                # Récursion sur les sous-dossiers
                if remove_recursive_folders(item, item.name):
                    removed_something = True

        # Suppression du dossier s'il est vide après nettoyage
        try:
            if not any(path.iterdir()):
                path.rmdir()
                logger.debug(f"Dossier vide supprimé: {path}")
                removed_something = True
        except (OSError, FileNotFoundError):
            pass

        return removed_something

    console.print("[blue]🧹 Nettoyage des liens récursifs...[/blue]")

    # Répéter le nettoyage jusqu'à ce qu'il n'y ait plus rien à nettoyer
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        if not remove_recursive_folders(directory):
            break
        iteration += 1

    if iteration >= max_iterations:
        logger.warning("Nettoyage interrompu après 10 itérations (possible récursivité persistante)")
    else:
        logger.info("Nettoyage des liens récursifs terminé")

def process_single_video(args: Tuple[Path, Path, Path, bool, bool]) -> Optional[Video]:
    """Traite un seul fichier vidéo (version pour multiprocessing)."""
    file, temp_dir, storage_dir, force_mode, dry_run = args  # 🆕 Ajout du paramètre dry_run

    try:
        video = Video()
        video.complete_path_original = file
        video.hash = checksum_md5(file)
        video.type_file = type_of_video(file)
        video.extended_sub = Path(video.type_file) / "Séries TV" if video.is_serie() else Path("")

        # Vérification des doublons seulement si pas en mode force
        if not force_mode and not dry_run:  # 🆕 Pas de vérification en dry_run non plus
            video_db = select_db(file, storage_dir)
            if hash_exists_in_db(video_db, video.hash):
                logger.info(f"Hash de {file.name} déjà présent dans {video_db.name}")
                return None
        elif dry_run:
            logger.debug(f"SIMULATION - Vérification hash ignorée pour {file.name}")

        # Extraction des informations
        video.title, video.date_film, video.sequence, video.season, video.episode, video.spec = extract_file_infos(
            video)

        # Ajout à la base de données seulement si pas en mode force ou dry_run
        if not force_mode and not dry_run:
            add_hash_to_db(file, video.hash, storage_dir)
        elif dry_run:
            logger.debug(f"SIMULATION - Ajout hash ignoré pour {file.name}")

        create_paths(file, video, temp_dir, dry_run)  # 🆕 Passage du paramètre dry_run

        return video

    except Exception as e:
        logger.error(f"Erreur lors du traitement de {file}: {e}")
        return None


def create_video_list(search_dir: Path, days_to_manage: float, temp_dir: Path, storage_dir: Path,
                      force_mode: bool = False, dry_run: bool = False, use_multiprocessing: bool = False) -> List[
    Video]:
    """Crée la liste des vidéos à traiter."""
    files_to_process = []

    # Filtrage des fichiers
    if days_to_manage == 100000000.0:
        last_exec = 0
    else:
        if dry_run:
            # En mode simulation, ne pas mettre à jour le fichier last_exec
            try:
                with open("last_exec_video", "r") as last_exec_file:
                    last_exec = float(last_exec_file.read().strip())
            except (FileNotFoundError, ValueError):
                last_exec = time.time() - 259200
        else:
            last_exec = load_last_exec() if not days_to_manage else time.time() - (86400 * days_to_manage)

    for file in get_file(search_dir):
        if file.stat().st_ctime > last_exec or days_to_manage == 100000000.0:
            if any(exclude in file.parts for exclude in ["ISX", "Applications"]):
                continue
            files_to_process.append(file)

    logger.info(f"Nombre de fichiers à traiter: {len(files_to_process)}")

    # Affichage du mode
    if dry_run:
        console.print("[yellow]🧪 MODE SIMULATION - Aucune modification de fichier[/yellow]")
        logger.warning("Mode simulation activé - aucune modification de fichier")
    if force_mode:
        console.print("[yellow]⚠️  Mode FORCE activé - Ignorer la vérification des hash[/yellow]")
        logger.warning("Mode force activé - vérification des hash désactivée")

    if not files_to_process:
        return []

    # Préparation des arguments avec les paramètres force et dry_run
    args_list = [(f, temp_dir, storage_dir, force_mode, dry_run) for f in files_to_process]

    if use_multiprocessing and len(files_to_process) > 10:
        console.print(f"🔄 Traitement en parallèle de {len(files_to_process)} fichiers...")
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            results = list(tqdm(
                executor.map(process_single_video, args_list),
                desc="Traitement des vidéos",
                total=len(args_list)
            ))
    else:
        console.print("🔄 Traitement séquentiel...")
        results = [process_single_video(args) for args in tqdm(args_list, desc="Traitement des vidéos")]

    # Filtrage des résultats valides
    video_list = [video for video in results if video is not None]
    logger.info(f"Nombre de vidéos valides traitées: {len(video_list)}")
    return video_list

def process_video(video: Video, waiting_folder: Path, storage_dir: Path, symlinks_dir: Path,
                  similarity_threshold: int = 80, year_tolerance: int = 1) -> Optional[Video]:
    """Traite une vidéo en vérifiant l'existence de fichiers similaires."""
    if video.is_film_anim():
        similar_file = find_similar_file(video, storage_dir, similarity_threshold, year_tolerance)
        if similar_file:
            result = handle_similar_file(video.complete_path_original, similar_file, waiting_folder, storage_dir)
            if result == similar_file:
                return None  # On garde l'ancien fichier
            elif result:
                video.complete_path_original = result

    return video


def find_symlink_and_sub_dir(video: Video, symlinks_dir: Path) -> Tuple[Path, Path]:
    """Trouve le bon sous-répertoire pour les symlinks."""
    if video.is_film_anim():
        target = symlinks_dir / 'Films' / video.genre
    else:
        target = symlinks_dir / video.extended_sub

    video.complete_dir_symlinks = find_directory_for_video(video, target)

    try:
        # Extraction du chemin relatif à partir du répertoire symlinks
        relative_path = video.complete_dir_symlinks.relative_to(symlinks_dir)
        video.sub_directory = relative_path
    except ValueError as e:
        logger.warning(f'Erreur lors de l\'extraction du chemin relatif: {e}')
        video.sub_directory = Path('')

    return video.complete_dir_symlinks, video.sub_directory


def validate_api_keys():
    """Valide la présence des clés API nécessaires."""
    missing_keys = []

    if not TMDB_API_KEY:
        missing_keys.append("TMDB_API_KEY")
    if not TVDB_API_KEY:
        missing_keys.append("TVDB_API_KEY")

    if missing_keys:
        logger.error(f"Clés API manquantes: {', '.join(missing_keys)}")
        console.print(f"[red]❌ Clés API manquantes: {', '.join(missing_keys)}[/red]")
        console.print("[yellow]Veuillez les ajouter dans le fichier .env[/yellow]")
        return False

    return True


def test_api_connectivity():
    """Teste la connectivité aux APIs."""
    console.print("[blue]🔄 Test de connectivité aux APIs...[/blue]")

    # Test TMDB
    tmdb = Tmdb()
    test_result = tmdb.find_content("test", "Films")
    if test_result is None:
        logger.error("Impossible de se connecter à l'API TMDB")
        console.print("[red]❌ Connexion TMDB échouée[/red]")
        return False

    console.print("[green]✅ Connexion TMDB réussie[/green]")

    # Test TVDB (optionnel car utilisé seulement pour les titres d'épisodes)
    try:
        tvdb_test = tvdb_api.Tvdb(apikey=TVDB_API_KEY, language='fr', interactive=False)
        console.print("[green]✅ Connexion TVDB réussie[/green]")
    except Exception as e:
        logger.warning(f"Problème avec TVDB (non critique): {e}")
        console.print("[yellow]⚠️  TVDB inaccessible (titres d'épisodes indisponibles)[/yellow]")

    return True


def cleanup_directories(*directories):
    """Nettoie les répertoires temporaires."""
    for directory in directories:
        if directory.exists() and any(directory.iterdir()):
            try:
                shutil.rmtree(directory, ignore_errors=True)
                logger.debug(f"Répertoire nettoyé: {directory}")
            except Exception as e:
                logger.warning(f"Impossible de nettoyer {directory}: {e}")


def verify_symlinks(directory: Path) -> None:
    """Vérifie l'intégrité des liens symboliques et répare les liens brisés."""
    broken_links = []

    for item in directory.rglob('*'):
        if item.is_symlink():
            try:
                # Tenter de résoudre le lien
                item.resolve(strict=True)
            except (FileNotFoundError, OSError):
                broken_links.append(item)

    if broken_links:
        logger.warning(f"Liens symboliques brisés détectés: {len(broken_links)}")
        for link in broken_links:
            logger.warning(f"Lien brisé: {link}")
            try:
                link.unlink()
                logger.info(f"Lien brisé supprimé: {link}")
            except Exception as e:
                logger.error(f"Impossible de supprimer le lien brisé {link}: {e}")
    else:
        logger.info("Tous les liens symboliques sont valides")


def generate_simulated_tree(list_of_videos: List[Video], destination_dir: Path) -> Dict[str, List[str]]:
    """Génère une simulation de l'arborescence qui serait créée."""
    tree_structure = {}

    for video in list_of_videos:
        if not video.formatted_filename:
            continue

        # Construction du chemin relatif
        if video.sub_directory:
            relative_path = str(video.sub_directory)
        else:
            if video.is_film_anim():
                if video.genre == "Non détecté":
                    relative_path = "Films/non détectés"
                else:
                    relative_path = f"Films/{video.genre}"
            elif video.is_serie():
                relative_path = "Séries/Séries TV"
            else:
                relative_path = video.type_file

        # Ajout du sous-répertoire de saison pour les séries
        if video.is_serie() and video.season > 0:
            # Utiliser le chemin mis à jour par add_episodes_titles si disponible
            if hasattr(video, 'complete_path_temp_links') and video.complete_path_temp_links:
                # Extraire le chemin relatif depuis complete_path_temp_links
                temp_path_str = str(video.complete_path_temp_links)
                if 'Saison' in temp_path_str:
                    # Construire le chemin avec la saison
                    relative_path += f"/{video.title_fr} ({video.date_film})/Saison {video.season:02d}"
                else:
                    relative_path += f"/{video.title_fr} ({video.date_film})/Saison {video.season:02d}"
            else:
                relative_path += f"/{video.title_fr} ({video.date_film})/Saison {video.season:02d}"

        # Ajout à la structure
        if relative_path not in tree_structure:
            tree_structure[relative_path] = []

        tree_structure[relative_path].append(video.formatted_filename)

    return tree_structure

def display_simulated_tree(tree_structure: Dict[str, List[str]], max_files_per_folder: int = 5):
    """Affiche l'arborescence simulée de manière élégante."""
    from rich.tree import Tree
    from rich.text import Text

    # Création de l'arbre principal
    root_tree = Tree("📁 [bold cyan]Structure simulée des liens symboliques[/bold cyan]")

    # Tri des dossiers
    sorted_folders = sorted(tree_structure.keys())

    for folder_path in sorted_folders:
        files = tree_structure[folder_path]

        # Création du noeud de dossier
        folder_icon = "📁" if "non détectés" not in folder_path else "❓"
        folder_color = "yellow" if "non détectés" in folder_path else "cyan"

        folder_node = root_tree.add(
            f"{folder_icon} [bold {folder_color}]{folder_path}[/bold {folder_color}] "
            f"[dim]({len(files)} fichier{'s' if len(files) > 1 else ''})[/dim]"
        )

        # Ajout des fichiers (limité pour éviter l'encombrement)
        displayed_files = files[:max_files_per_folder]

        for file in displayed_files:
            # Choix de l'icône selon le type
            if file.endswith(('.mkv', '.avi', '.mp4')):
                if 'S0' in file and 'E0' in file:
                    icon = "📺"
                    color = "blue"
                else:
                    icon = "🎬"
                    color = "green"
            else:
                icon = "📄"
                color = "white"

            folder_node.add(f"{icon} [{color}]{file}[/{color}]")

        # Indication s'il y a plus de fichiers
        if len(files) > max_files_per_folder:
            remaining = len(files) - max_files_per_folder
            folder_node.add(
                f"[dim]... et {remaining} autre{'s' if remaining > 1 else ''} "
                f"fichier{'s' if remaining > 1 else ''}[/dim]")

    console.print(root_tree)


def display_detailed_summary(tree_structure: Dict[str, List[str]]):
    """Affiche un résumé détaillé par catégorie."""
    from rich.table import Table

    table = Table(title="📊 Résumé détaillé de la simulation", show_header=True, header_style="bold magenta")
    table.add_column("Catégorie", style="cyan", no_wrap=True)
    table.add_column("Sous-catégorie", style="yellow")
    table.add_column("Nombre de fichiers", justify="right", style="green")
    table.add_column("Exemples", style="dim")

    # Analyse par catégorie
    categories = {}

    for folder_path, files in tree_structure.items():
        path_parts = folder_path.split('/')
        main_category = path_parts[0]
        sub_category = '/'.join(path_parts[1:]) if len(path_parts) > 1 else "Racine"

        if main_category not in categories:
            categories[main_category] = {}

        categories[main_category][sub_category] = files

    for main_cat, sub_cats in sorted(categories.items()):
        first_sub = True
        for sub_cat, files in sorted(sub_cats.items()):
            # Exemples de fichiers (max 2)
            examples = ", ".join(files[:2])
            if len(files) > 2:
                examples += f" (+{len(files) - 2})"

            table.add_row(
                main_cat if first_sub else "",
                sub_cat,
                str(len(files)),
                examples
            )
            first_sub = False

    console.print(table)


def show_renaming_examples(list_of_videos: List[Video], max_examples: int = 10):
    """Affiche des exemples de renommage avant/après."""
    from rich.table import Table

    table = Table(title="🔄 Exemples de renommage", show_header=True, header_style="bold magenta")
    table.add_column("Nom original", style="red", max_width=40)
    table.add_column("➤", justify="center", style="yellow", width=3)
    table.add_column("Nom formaté", style="green", max_width=40)
    table.add_column("Type", style="cyan", width=8)

    # Sélection d'exemples variés
    examples = []

    # Prendre des exemples de chaque type
    films = [v for v in list_of_videos if v.is_film() and v.formatted_filename][:3]
    series = [v for v in list_of_videos if v.is_serie() and v.formatted_filename][:3]
    anims = [v for v in list_of_videos if v.is_animation() and v.formatted_filename][:2]
    non_detectes = [v for v in list_of_videos if v.genre == "Non détecté" and v.formatted_filename][:2]

    examples.extend(films + series + anims + non_detectes)

    for video in examples[:max_examples]:
        original_name = video.complete_path_original.name
        formatted_name = video.formatted_filename

        # Raccourcissement si nécessaire
        if len(original_name) > 40:
            original_name = original_name[:37] + "..."
        if len(formatted_name) > 40:
            formatted_name = formatted_name[:37] + "..."

        # Type de fichier
        if video.is_film():
            file_type = "Film"
        elif video.is_serie():
            file_type = "Série"
        elif video.is_animation():
            file_type = "Anim"
        else:
            file_type = video.type_file

        table.add_row(original_name, "➤", formatted_name, file_type)

    console.print(table)


def display_processing_statistics(list_of_videos: List[Video]):
    """Affiche des statistiques détaillées du traitement."""
    from rich.table import Table

    # Calcul des statistiques
    total_files = len(list_of_videos)

    stats = {
        "Films traités": len([v for v in list_of_videos if v.is_film() and v.title_fr]),
        "Films non détectés": len(
            [v for v in list_of_videos if v.is_film() and (not v.title_fr or v.genre == "Non détecté")]),
        "Séries traitées": len([v for v in list_of_videos if v.is_serie() and v.title_fr]),
        "Séries non détectées": len([v for v in list_of_videos if v.is_serie() and not v.title_fr]),
        "Animations": len([v for v in list_of_videos if v.is_animation()]),
        "Documentaires": len([v for v in list_of_videos if v.type_file in {'Docs', 'Docs#1'}]),
    }

    # Table des statistiques
    table = Table(title="📈 Statistiques de traitement", show_header=True, header_style="bold magenta")
    table.add_column("Catégorie", style="cyan")
    table.add_column("Nombre", justify="right", style="green")
    table.add_column("Pourcentage", justify="right", style="yellow")

    for category, count in stats.items():
        percentage = (count / total_files * 100) if total_files > 0 else 0
        table.add_row(category, str(count), f"{percentage:.1f}%")

    # Ligne de total
    table.add_row("", "", "", style="dim")
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{total_files}[/bold]", "[bold]100.0%[/bold]")

    console.print(table)


def main():
    """Fonction principale du script."""
    try:
        # Validation des clés API
        if not validate_api_keys():
            exit(1)

        # Test de connectivité
        if not test_api_connectivity():
            exit(1)

        # Parsing des arguments avec dry-run
        (search_dir, destination_dir, symlinks_dir, storage_dir, days_to_manage,
         debug, tags_to_debug, force_mode, dry_run) = parse_arg()

        # Affichage spécial pour le mode simulation
        if dry_run:
            console.print(Panel.fit(
                "[bold yellow]🧪 MODE SIMULATION ACTIVÉ[/bold yellow]\n\n"
                "• Aucune modification ne sera apportée aux fichiers\n"
                "• Toutes les opérations seront simulées et loggées\n"
                "• Les fichiers originaux restent intacts\n"
                "• Parfait pour tester le comportement du script",
                title="⚠️  Mode Test",
                border_style="yellow"
            ))

        # Configuration des répertoires de travail
        work_dir, temp_dir, original_dir, waiting_folder = setup_working_directories(destination_dir, dry_run)

        # Affichage de la configuration
        mode_status = ""
        if force_mode:
            mode_status += "[red]FORCE[/red] "
        if dry_run:
            mode_status += "[yellow]SIMULATION[/yellow]"
        if not mode_status:
            mode_status = "[green]Normal[/green]"

        console.print(Panel.fit(
            f"[bold]Configuration du traitement[/bold]\n"
            f"📁 Répertoire source: [cyan]{search_dir}[/cyan]\n"
            f"💾 Répertoire de stockage: [cyan]{storage_dir}[/cyan]\n"
            f"🔗 Répertoire des symlinks: [cyan]{symlinks_dir}[/cyan]\n"
            f"📋 Répertoire temporaire: [cyan]{destination_dir}[/cyan]\n"
            f"⏱️  Période: {'Tous les fichiers' if days_to_manage == 100000000.0 else f'{days_to_manage} '
                                                                                      f'derniers jours'}\n"
            f"🔧 Mode: {mode_status}",
            title="🎬 Organisateur de Vidéothèque"
        ))

        # Validation de la structure des répertoires
        available_categories = get_available_categories(search_dir)
        if not available_categories:
            console.print(f"[red]❌ Aucune catégorie trouvée dans {search_dir}[/red]")
            console.print(f"[yellow]Catégories attendues: {', '.join(CATEGORIES)}[/yellow]")
            exit(1)

        console.print(f"[green]✅ Catégories détectées: {', '.join([cat.name for cat in available_categories])}[/green]")

        # Comptage des vidéos
        nb_videos = count_videos(search_dir)
        if nb_videos == 0:
            console.print("[yellow]ℹ️  Aucune vidéo à traiter[/yellow]")
            return

        console.print(f'\n[bold green]📊 {nb_videos} vidéos détectées[/bold green]')

        # Aplatissement des répertoires séries
        if not dry_run:
            console.print("[blue]🔄 Aplatissement des répertoires séries...[/blue]")
            aplatir_repertoire_series(search_dir)
        else:
            console.print("[dim]🔍 SIMULATION - Aplatissement des répertoires ignoré[/dim]")

        # Traitement des vidéos avec dry_run
        console.print("[blue]🔄 Analyse et création des liens temporaires...[/blue]")
        list_of_videos = create_video_list(search_dir, days_to_manage, temp_dir, storage_dir,
                                           force_mode, dry_run, use_multiprocessing=(nb_videos > 50))

        if not list_of_videos:
            if force_mode:
                console.print("[yellow]ℹ️  Aucune vidéo à traiter (même en mode force)[/yellow]")
            else:
                console.print("[yellow]ℹ️  Aucune nouvelle vidéo à traiter[/yellow]")
            return

        console.print(f"[green]✅ {len(list_of_videos)} vidéos prêtes pour le traitement[/green]")

        # Sauvegarde des liens originaux
        if not dry_run:
            logger.info('Sauvegarde des liens vers les fichiers originaux')
            copy_tree(temp_dir, original_dir, dry_run)

            # Nettoyage et création du répertoire de travail
            cleanup_directories(work_dir)
            work_dir.mkdir(exist_ok=True)
        else:
            console.print("[dim]🔍 SIMULATION - Sauvegarde et nettoyage ignorés[/dim]")

        console.print("[blue]🔄 Formatage des titres et organisation...[/blue]")
        dict_titles = {}  # Cache pour éviter les requêtes répétées

        # Barre de progression pour le traitement principal
        with tqdm(list_of_videos, desc="Traitement des vidéos", unit="fichier") as pbar:
            for video in pbar:
                pbar.set_postfix_str(f"Traitement: {video.complete_path_original.name[:30]}...")

                try:
                    # Traitement des documentaires (sans API)
                    if video.type_file in {'Docs', 'Docs#1'}:
                        rename_video(video, dict_titles, video.type_file, work_dir, dry_run)
                        move_file_new_nas(video, storage_dir, dry_run)
                        continue

                    # Utilisation du cache pour éviter les requêtes répétées
                    cache_key = video.title
                    if cache_key in dict_titles:
                        (video.title_fr, video.date_film, video.genre,
                         video.complete_dir_symlinks, video.sub_directory, cached_spec) = dict_titles[cache_key]

                        # Utilisation du spec mis en cache si le spec actuel est incomplet
                        if not video.spec or len(video.spec.split()) < 3:
                            video.spec = cached_spec

                        # Formatage du nom de fichier
                        video.formatted_filename = video.format_name(video.title_fr)
                        logger.info(f'{video.formatted_filename} ({video.genre}) - formaté (depuis cache)')
                    else:
                        # ✅ Sauvegarder les valeurs originales avant traitement
                        original_spec = video.spec
                        original_formatted_filename = getattr(video, 'formatted_filename', '')

                        # Traitement normal avec API pour TOUS les types (films ET séries)
                        video = set_fr_title_and_category(video)

                        # Vérifier si le traitement API a échoué SEULEMENT pour les FILMS
                        if (not video.title_fr or video.title_fr.strip() == '') and video.is_film_anim():
                            # Gestion "non détectés" UNIQUEMENT pour les films/animations
                            logger.warning(
                                f"Échec de l'identification API pour le film {video.complete_path_original.name}")
                            video.title_fr = ""
                            video.date_film = 0
                            video.genre = "Non détecté"
                            video.list_genres = ["Non détecté"]

                            # ✅ Restaurer les specs originales pour le formatage
                            video.spec = original_spec
                            video.formatted_filename = format_undetected_filename(video)

                            # Répertoire "non détectés" pour films
                            video.sub_directory = Path('Films/non détectés')
                            video.complete_dir_symlinks = find_directory_for_video(video, symlinks_dir / 'Films')

                            logger.info(f'{video.formatted_filename} (Film non détecté après API) - formaté')

                        elif (not video.title_fr or video.title_fr.strip() == '') and video.is_serie():
                            # Gestion spéciale pour les séries non détectées - demander à l'utilisateur
                            logger.warning(
                                f"Échec de l'identification API pour la série {video.complete_path_original.name}")

                            if not dry_run:
                                console.print(
                                    f"\n[yellow]⚠️  Série non identifiée automatiquement :[/yellow] [cyan]"
                                    f"{video.complete_path_original.name}[/cyan]")

                                # Demander le titre à l'utilisateur
                                while True:
                                    user_title = input(
                                        "Veuillez saisir le titre de cette série (ou 'skip' pour ignorer) : ").strip()
                                    if user_title.lower() == 'skip':
                                        logger.info(
                                            f"Série ignorée par l'utilisateur : {video.complete_path_original.name}")
                                        break
                                    elif user_title:
                                        video.title_fr = user_title
                                        video.date_film = video.date_film or 0
                                        video.genre = ""
                                        video.list_genres = []
                                        break
                                    else:
                                        console.print("[red]Veuillez saisir un titre valide ou 'skip'[/red]")

                                if user_title.lower() == 'skip':
                                    continue
                            else:
                                # En mode simulation, simuler une réponse
                                console.print(
                                    f"[dim]🔍 SIMULATION - Série non détectée : "
                                    f"{video.complete_path_original.name}[/dim]")
                                console.print(f"[dim]    (En mode normal, demande du titre à l'utilisateur)[/dim]")
                                video.title_fr = "Série Non Identifiée"
                                video.date_film = 0
                                video.genre = ""
                                video.list_genres = []

                            # Traitement normal pour la série avec le titre fourni
                            video.complete_dir_symlinks, video.sub_directory = find_symlink_and_sub_dir(video,
                                                                                                        symlinks_dir)

                            # ✅ Amélioration des spécifications techniques SI NÉCESSAIRE seulement
                            if not video.spec or len(video.spec.split()) < 3:
                                media_spec = media_info(video)
                                if media_spec:
                                    video.spec = media_spec

                            # Formatage du nom de fichier
                            video.formatted_filename = video.format_name(video.title_fr)
                            logger.info(f'{video.formatted_filename} (Série - titre manuel) - formaté')

                        else:
                            # Succès de l'API ou série avec titre, traitement normal
                            video.complete_dir_symlinks, video.sub_directory = find_symlink_and_sub_dir(video,
                                                                                                        symlinks_dir)

                            # ✅ Amélioration des spécifications techniques SI NÉCESSAIRE seulement
                            if not video.spec or len(video.spec.split()) < 3:
                                media_spec = media_info(video)
                                if media_spec:
                                    video.spec = media_spec

                            # Formatage du nom de fichier
                            video.formatted_filename = video.format_name(video.title_fr)
                            logger.info(
                                f'{video.formatted_filename} ({video.genre if video.genre else "Série"}) - formaté')

                        # Mise en cache seulement pour les fichiers détectés avec titre
                        if video.title_fr and video.title:
                            dict_titles[cache_key] = (video.title_fr, video.date_film, video.genre,
                                                      video.complete_dir_symlinks, video.sub_directory, video.spec)

                    # Vérification des doublons et traitement
                    processed_video = process_video(video, waiting_folder, storage_dir, symlinks_dir)
                    if processed_video:
                        rename_video(processed_video, dict_titles, str(processed_video.sub_directory), work_dir,
                                     dry_run)
                        move_file_new_nas(processed_video, storage_dir, dry_run)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {video.complete_path_original.name}: {e}")
                    continue

                # Traitement spécial pour les séries (ajout des titres d'épisodes)
                series_videos = [v for v in list_of_videos if v.is_serie() and v.title_fr]
                if series_videos:
                    if not dry_run:
                        console.print(
                            f"[blue]🔄 Recherche des titres d'épisodes pour {len(series_videos)} séries...[/blue]")
                        # Nettoyage préventif AVANT le traitement des épisodes
                        cleanup_work_directory(work_dir)
                    else:
                        console.print(
                            f"[yellow]🔍 SIMULATION - Recherche des titres d'épisodes pour "
                            f"{len(series_videos)} séries...[/yellow]")
                        console.print(
                            "[dim]Note: Les requêtes TVDB sont réelles pour obtenir les vrais titres[/dim]")

                    add_episodes_titles(series_videos, work_dir / 'Séries/Séries TV', dry_run)

                    # Nettoyage APRÈS le traitement si nécessaire
                    if not dry_run:
                        cleanup_work_directory(work_dir)

        # Copie finale vers le répertoire de destination
        if work_dir.exists() and any(work_dir.iterdir()):
            console.print("[blue]🔄 Copie finale vers le répertoire de destination...[/blue]")
            copy_tree(work_dir, destination_dir, dry_run)

            if not dry_run:
                # Nettoyage des liens récursifs AVANT la vérification
                cleanup_recursive_symlinks(destination_dir)

                console.print("[blue]🔄 Vérification de l'intégrité des liens symboliques...[/blue]")
                verify_symlinks(destination_dir)
            else:
                console.print("[dim]🔍 SIMULATION - Vérification des liens symboliques ignorée[/dim]")

        # Statistiques finales
        films_count = len([v for v in list_of_videos if v.is_film()])
        series_count = len([v for v in list_of_videos if v.is_serie() and v.title_fr])
        anim_count = len([v for v in list_of_videos if v.is_animation()])
        docs_count = len([v for v in list_of_videos if v.type_file in {'Docs', 'Docs#1'}])
        non_detectes_count = len(
            [v for v in list_of_videos if v.is_film_anim() and (not v.title_fr or v.genre == "Non détecté")])
        series_skipped = len([v for v in list_of_videos if v.is_serie() and not v.title_fr])

        # Affichage final selon le mode
        if dry_run:
            # Génération de l'arborescence simulée
            console.print("\n" + "=" * 80)
            console.print("🔍 RÉCAPITULATIF DE LA SIMULATION", style="bold yellow", justify="center")
            console.print("=" * 80)

            # 1. Statistiques de traitement
            display_processing_statistics(list_of_videos)

            # 2. Exemples de renommage
            console.print()
            show_renaming_examples(list_of_videos)

            # 3. Arborescence simulée
            console.print()
            tree_structure = generate_simulated_tree(list_of_videos, destination_dir)
            display_simulated_tree(tree_structure, max_files_per_folder=3)

            # 4. Résumé détaillé
            console.print()
            display_detailed_summary(tree_structure)

            # Panel final
            console.print()
            console.print(Panel.fit(
                f"[bold yellow]🧪 SIMULATION TERMINÉE[/bold yellow]\n\n"
                f"📊 [bold]Résumé :[/bold]\n"
                f"🎬 Films: [cyan]{films_count}[/cyan] (dont [yellow]{non_detectes_count}[/yellow] non détectés)\n"
                f"📺 Séries: [cyan]{series_count}[/cyan] (dont [dim]{series_skipped}[/dim] ignorées)\n"
                f"🎨 Animation: [cyan]{anim_count}[/cyan]\n"
                f"📚 Documentaires: [cyan]{docs_count}[/cyan]\n\n"
                f"✅ Aucune modification effectuée sur les fichiers\n"
                f"✅ L'arborescence ci-dessus montre le résultat final\n\n"
                f"[dim]Pour appliquer les changements, relancez sans --dry-run[/dim]",
                title="📋 Résumé de la simulation",
                border_style="yellow"
            ))
        else:
            console.print(Panel.fit(
                f"[bold green]✅ Traitement terminé avec succès ![/bold green]\n\n"
                f"📊 [bold]Statistiques:[/bold]\n"
                f"🎬 Films: [cyan]{films_count}[/cyan]\n"
                f"📺 Séries: [cyan]{series_count}[/cyan]\n"
                f"🎨 Animation: [cyan]{anim_count}[/cyan]\n"
                f"📚 Documentaires: [cyan]{docs_count}[/cyan]\n"
                f"❓ Films non détectés: [yellow]{non_detectes_count}[/yellow]\n"
                f"⏭️  Séries ignorées: [dim]{series_skipped}[/dim]\n\n"
                f"📁 Résultats disponibles dans: [yellow]{destination_dir}[/yellow]",
                title="🎉 Résumé du traitement"
            ))

        logger.info(f"Traitement terminé: {len(list_of_videos)} vidéos traitées")

        # Affichage des suggestions pour les fichiers non détectés
        if non_detectes_count > 0 and not dry_run:
            console.print(Panel.fit(
                f"[yellow]⚠️  {non_detectes_count} film(s) non détecté(s)[/yellow]\n\n"
                f"Ces fichiers ont été placés dans le dossier '[bold]non détectés[/bold]'\n"
                f"et formatés avec les informations disponibles.\n\n"
                f"[dim]Conseils pour améliorer la détection :[/dim]\n"
                f"[dim]• Vérifiez l'orthographe des noms de fichiers[/dim]\n"
                f"[dim]• Ajoutez l'année dans le nom si possible[/dim]\n"
                f"[dim]• Consultez les logs pour plus de détails[/dim]",
                title="💡 Suggestions",
                border_style="yellow"
            ))

        # Affichage des informations sur les séries ignorées
        if series_skipped > 0 and not dry_run:
            console.print(Panel.fit(
                f"[dim]ℹ️  {series_skipped} série(s) ignorée(s) par l'utilisateur[/dim]\n\n"
                f"Ces fichiers restent dans leur emplacement d'origine.\n"
                f"Vous pouvez les retraiter plus tard en relançant le script.",
                title="📝 Séries ignorées",
                border_style="dim"
            ))

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interruption par l'utilisateur[/yellow]")
        logger.info("Interruption par l'utilisateur")
    except Exception as e:
        console.print(f"[red]❌ Erreur fatale: {e}[/red]")
        logger.error(f"Erreur fatale: {e}")
        raise
    finally:
        # Nettoyage optionnel des répertoires temporaires
        pass


if __name__ == '__main__':
    main()