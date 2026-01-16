"""Gestion de l'état de l'application via SQLite.

Ce module fournit une interface pour stocker et récupérer l'état de l'application
(comme la date de dernière exécution) dans une base de données SQLite existante.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from organize.config import (
    CACHE_DB_FILENAME,
    DEFAULT_SECONDS_BACK,
    APP_STATE_TABLE,
    LAST_EXEC_KEY,
)


class AppStateManager:
    """
    Gestionnaire d'état de l'application basé sur SQLite.

    Utilise la base de données cache existante pour stocker l'état de l'application
    de manière atomique et sans conditions de concurrence.

    Attributs :
        db_path: Chemin vers la base de données SQLite.
        conn: Connexion active à la base de données, ou None si fermée.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Initialise le gestionnaire d'état.

        Arguments :
            db_path: Chemin vers la base SQLite. Utilise cache.db par défaut.
        """
        self.db_path = db_path or Path(CACHE_DB_FILENAME)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Établit la connexion et crée la table si nécessaire."""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=10.0)
            self._create_table()
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données : {e}")

    def _create_table(self) -> None:
        """Crée la table d'état si elle n'existe pas."""
        if not self.conn:
            return

        cursor = self.conn.cursor()
        try:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {APP_STATE_TABLE} (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at INTEGER
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la création de la table : {e}")

    def get_last_exec(self) -> float:
        """
        Récupère la date de dernière exécution.

        Retourne :
            Timestamp de la dernière exécution, ou (now - 3 jours) si non trouvé.
        """
        if not self.conn:
            return time.time() - DEFAULT_SECONDS_BACK

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                f"SELECT value FROM {APP_STATE_TABLE} WHERE key = ?",
                (LAST_EXEC_KEY,)
            )
            row = cursor.fetchone()
            if row:
                return float(row[0])
        except (sqlite3.Error, ValueError) as e:
            logger.warning(f"Erreur lors de la lecture de last_exec : {e}")

        return time.time() - DEFAULT_SECONDS_BACK

    def set_last_exec(self, timestamp: Optional[float] = None) -> bool:
        """
        Enregistre la date de dernière exécution.

        Arguments :
            timestamp: Timestamp à enregistrer. Utilise time.time() par défaut.

        Retourne :
            True si l'enregistrement a réussi, False sinon.
        """
        if not self.conn:
            return False

        if timestamp is None:
            timestamp = time.time()

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                f"""INSERT OR REPLACE INTO {APP_STATE_TABLE}
                    (key, value, updated_at) VALUES (?, ?, ?)""",
                (LAST_EXEC_KEY, str(timestamp), int(time.time()))
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.warning(f"Erreur lors de l'écriture de last_exec : {e}")
            return False

    def get_last_exec_and_update(self) -> float:
        """
        Récupère la date de dernière exécution et la met à jour atomiquement.

        Cette méthode combine la lecture et l'écriture en une seule transaction
        pour éviter les conditions de concurrence.

        Retourne :
            Timestamp de la dernière exécution (avant mise à jour).
        """
        if not self.conn:
            return time.time() - DEFAULT_SECONDS_BACK

        cursor = self.conn.cursor()
        try:
            # Transaction atomique
            cursor.execute("BEGIN IMMEDIATE")

            # Lire la valeur actuelle
            cursor.execute(
                f"SELECT value FROM {APP_STATE_TABLE} WHERE key = ?",
                (LAST_EXEC_KEY,)
            )
            row = cursor.fetchone()
            last_exec = float(row[0]) if row else time.time() - DEFAULT_SECONDS_BACK

            # Mettre à jour avec le timestamp actuel
            cursor.execute(
                f"""INSERT OR REPLACE INTO {APP_STATE_TABLE}
                    (key, value, updated_at) VALUES (?, ?, ?)""",
                (LAST_EXEC_KEY, str(time.time()), int(time.time()))
            )

            self.conn.commit()
            return last_exec

        except (sqlite3.Error, ValueError) as e:
            logger.warning(f"Erreur lors de get_last_exec_and_update : {e}")
            if self.conn:
                self.conn.rollback()
            return time.time() - DEFAULT_SECONDS_BACK

    def close(self) -> None:
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "AppStateManager":
        """Support du context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ferme la connexion à la sortie du context manager."""
        self.close()


# Instance globale pour utilisation simplifiée
_app_state: Optional[AppStateManager] = None


def get_app_state(db_path: Optional[Path] = None) -> AppStateManager:
    """
    Retourne l'instance globale du gestionnaire d'état.

    Arguments :
        db_path: Chemin vers la base SQLite (optionnel).

    Retourne :
        Instance AppStateManager.
    """
    global _app_state
    if _app_state is None or _app_state.conn is None:
        _app_state = AppStateManager(db_path)
    return _app_state


def load_last_exec(db_path: Optional[Path] = None) -> float:
    """
    Charge la date de dernière exécution et met à jour le fichier.

    Fonction de compatibilité avec l'ancienne API basée sur fichier texte.

    Arguments :
        db_path: Chemin vers la base SQLite (optionnel).

    Retourne :
        Timestamp de la dernière exécution.
    """
    state = get_app_state(db_path)
    return state.get_last_exec_and_update()


def get_last_exec_readonly(db_path: Optional[Path] = None) -> float:
    """
    Lit la date de dernière exécution sans la modifier.

    Utilisé en mode simulation pour ne pas modifier l'état.

    Arguments :
        db_path: Chemin vers la base SQLite (optionnel).

    Retourne :
        Timestamp de la dernière exécution.
    """
    state = get_app_state(db_path)
    return state.get_last_exec()
