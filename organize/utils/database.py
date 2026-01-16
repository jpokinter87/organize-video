"""Utilitaires de base de données pour la gestion des hashes de fichiers vidéo."""

import sqlite3
from pathlib import Path
from typing import Optional

from loguru import logger

from organize.classification.type_detector import type_of_video
from organize.config import FILMANIM, DATABASE_NAME_FILMS, DATABASE_NAME_PATTERN


def select_db(file: Path, storage_dir: Path) -> Path:
    """
    Sélectionne la base de données appropriée selon le type de vidéo.

    Arguments :
        file: Chemin du fichier vidéo.
        storage_dir: Répertoire de stockage contenant les bases de données.

    Retourne :
        Chemin vers la base de données correspondante.
    """
    type_video = type_of_video(file)
    if type_video in FILMANIM:
        return storage_dir / DATABASE_NAME_FILMS
    else:
        return storage_dir / DATABASE_NAME_PATTERN.format(category=type_video)


def add_hash_to_db(file: Path, hash_value: str, storage_dir: Path) -> bool:
    """
    Ajoute un hash à la base de données.

    Arguments :
        file: Chemin du fichier vidéo.
        hash_value: Valeur MD5 du fichier.
        storage_dir: Répertoire de stockage contenant les bases de données.

    Retourne :
        True si l'ajout a réussi, False sinon.
    """
    db_path = select_db(file, storage_dir)
    try:
        file_size = file.stat().st_size
    except OSError as e:
        logger.warning(f"Impossible de lire la taille du fichier {file}: {e}")
        return False

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Création de la table si elle n'existe pas
            cursor.execute('''CREATE TABLE IF NOT EXISTS file_hashes
                             (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')

            file_str = str(file)

            cursor.execute('SELECT 1 FROM file_hashes WHERE hash = ?', (hash_value,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO file_hashes (hash, filepath, filename, file_size) VALUES (?, ?, ?, ?)',
                    (hash_value, file_str, file.name, file_size)
                )

            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.warning(f"Erreur SQLite avec la base {db_path}: {e}")
        return False


def hash_exists_in_db(database: Path, hash_value: str) -> bool:
    """
    Vérifie si le hash existe dans la base de données.

    Arguments :
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à vérifier.

    Retourne :
        True si le hash existe, False sinon.
    """
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM file_hashes WHERE hash = ?', (hash_value,))
            return c.fetchone() is not None
    except sqlite3.Error as e:
        logger.warning(f'Erreur SQLite - Base de données {database} inaccessible: {e}')
        return False


def remove_hash_from_db(database: Path, hash_value: str) -> bool:
    """
    Supprime un hash de la base de données.

    Arguments :
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à supprimer.

    Retourne :
        True si la suppression a réussi, False sinon.
    """
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM file_hashes WHERE hash = ?', (hash_value,))
            conn.commit()
            return c.rowcount > 0
    except sqlite3.Error as e:
        logger.warning(f'Erreur SQLite - Impossible de supprimer le hash de {database}: {e}')
        return False


def get_hash_info(database: Path, hash_value: str) -> Optional[dict]:
    """
    Récupère les informations associées à un hash.

    Arguments :
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à rechercher.

    Retourne :
        Dictionnaire avec les informations du fichier, ou None si non trouvé.
    """
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute(
                'SELECT filepath, filename, file_size FROM file_hashes WHERE hash = ?',
                (hash_value,)
            )
            row = c.fetchone()
            if row:
                return {
                    'filepath': row[0],
                    'filename': row[1],
                    'file_size': row[2],
                    'hash': hash_value
                }
            return None
    except sqlite3.Error as e:
        logger.warning(f'Erreur SQLite - Impossible de lire les infos du hash de {database}: {e}')
        return None
