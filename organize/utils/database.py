"""Utilitaires de base de données pour la gestion des hashes de fichiers vidéo."""

import sqlite3
from pathlib import Path
from typing import Optional

from loguru import logger

from organize.classification.type_detector import type_of_video


def select_db(file: Path, storage_dir: Path) -> Path:
    """
    Sélectionne la base de données appropriée selon le type de vidéo.

    Args:
        file: Chemin du fichier vidéo.
        storage_dir: Répertoire de stockage contenant les bases de données.

    Returns:
        Chemin vers la base de données correspondante.
    """
    type_video = type_of_video(file)
    if type_video in {'Films', 'Animation'}:
        return storage_dir / 'symlink_video_Films.db'
    else:
        return storage_dir / f'symlink_video_{type_video}.db'


def add_hash_to_db(file: Path, hash_value: str, storage_dir: Path) -> bool:
    """
    Ajoute un hash à la base de données.

    Args:
        file: Chemin du fichier vidéo.
        hash_value: Valeur MD5 du fichier.
        storage_dir: Répertoire de stockage contenant les bases de données.

    Returns:
        True si l'ajout a réussi, False sinon.
    """
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
        return True
    except Exception as e:
        logger.warning(f"Exception {e} - problème avec la base {db_path}")
        return False


def hash_exists_in_db(database: Path, hash_value: str) -> bool:
    """
    Vérifie si le hash existe dans la base de données.

    Args:
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à vérifier.

    Returns:
        True si le hash existe, False sinon.
    """
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM file_hashes WHERE hash = ?', (hash_value,))
            return c.fetchone() is not None
    except Exception as e:
        logger.warning(f'Exception {e} - Base de données {database} inaccessible')
        return False


def remove_hash_from_db(database: Path, hash_value: str) -> bool:
    """
    Supprime un hash de la base de données.

    Args:
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à supprimer.

    Returns:
        True si la suppression a réussi, False sinon.
    """
    try:
        with sqlite3.connect(str(database)) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM file_hashes WHERE hash = ?', (hash_value,))
            conn.commit()
            return c.rowcount > 0
    except Exception as e:
        logger.warning(f'Exception {e} - Impossible de supprimer le hash de {database}')
        return False


def get_hash_info(database: Path, hash_value: str) -> Optional[dict]:
    """
    Récupère les informations associées à un hash.

    Args:
        database: Chemin vers la base de données.
        hash_value: Valeur MD5 à rechercher.

    Returns:
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
    except Exception as e:
        logger.warning(f'Exception {e} - Impossible de lire les infos du hash de {database}')
        return None
