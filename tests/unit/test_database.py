"""Tests unitaires pour les utilitaires de base de données."""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.utils.database import (
    select_db,
    add_hash_to_db,
    hash_exists_in_db,
    remove_hash_from_db,
    get_hash_info,
)


class TestSelectDb:
    """Tests pour la fonction select_db."""

    def test_selectionne_db_films(self, tmp_path):
        """Retourne la base Films pour les fichiers du dossier Films."""
        file = tmp_path / "Films" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.touch()

        result = select_db(file, tmp_path)

        assert result == tmp_path / 'symlink_video_Films.db'

    def test_selectionne_db_animation(self, tmp_path):
        """Retourne la base Films pour les fichiers du dossier Animation."""
        file = tmp_path / "Animation" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.touch()

        result = select_db(file, tmp_path)

        assert result == tmp_path / 'symlink_video_Films.db'

    def test_selectionne_db_series(self, tmp_path):
        """Retourne la base Séries pour les fichiers du dossier Séries."""
        file = tmp_path / "Séries" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.touch()

        result = select_db(file, tmp_path)

        assert result == tmp_path / 'symlink_video_Séries.db'

    def test_selectionne_db_docs(self, tmp_path):
        """Retourne la base Docs pour les fichiers du dossier Docs."""
        file = tmp_path / "Docs" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.touch()

        result = select_db(file, tmp_path)

        assert result == tmp_path / 'symlink_video_Docs.db'


class TestAddHashToDb:
    """Tests pour la fonction add_hash_to_db."""

    def test_ajoute_hash_nouveau_fichier(self, tmp_path):
        """Ajoute un hash pour un nouveau fichier."""
        # Créer un fichier de test
        file = tmp_path / "Films" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.write_bytes(b"test content")

        result = add_hash_to_db(file, "abc123", tmp_path)

        assert result is True

        # Vérifier que le hash est dans la base
        db_path = tmp_path / 'symlink_video_Films.db'
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT hash, filename FROM file_hashes WHERE hash = ?', ("abc123",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "abc123"
        assert row[1] == "Test.mkv"

    def test_ne_duplique_pas_hash_existant(self, tmp_path):
        """Ne duplique pas un hash déjà existant."""
        file = tmp_path / "Films" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.write_bytes(b"test content")

        # Ajouter deux fois
        add_hash_to_db(file, "abc123", tmp_path)
        add_hash_to_db(file, "abc123", tmp_path)

        # Vérifier qu'il n'y a qu'une entrée
        db_path = tmp_path / 'symlink_video_Films.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_hashes WHERE hash = ?', ("abc123",))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_gere_erreur_base_inaccessible(self, tmp_path):
        """Gère gracieusement une base inaccessible."""
        file = tmp_path / "Films" / "Test.mkv"
        file.parent.mkdir(parents=True)
        file.write_bytes(b"test content")

        # Créer un fichier de base de données en lecture seule
        db_path = tmp_path / 'symlink_video_Films.db'
        db_path.touch()

        with patch('sqlite3.connect', side_effect=sqlite3.Error("DB Error")):
            result = add_hash_to_db(file, "abc123", tmp_path)
            assert result is False


class TestHashExistsInDb:
    """Tests pour la fonction hash_exists_in_db."""

    def test_trouve_hash_existant(self, tmp_path):
        """Trouve un hash existant dans la base."""
        # Créer la base et ajouter un hash
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        cursor.execute(
            'INSERT INTO file_hashes (hash, filepath, filename, file_size) VALUES (?, ?, ?, ?)',
            ("abc123", "/test/path", "test.mkv", 1000)
        )
        conn.commit()
        conn.close()

        result = hash_exists_in_db(db_path, "abc123")

        assert result is True

    def test_retourne_false_hash_inexistant(self, tmp_path):
        """Retourne False pour un hash inexistant."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        conn.commit()
        conn.close()

        result = hash_exists_in_db(db_path, "nonexistent")

        assert result is False

    def test_retourne_false_base_inexistante(self, tmp_path):
        """Retourne False si la base n'existe pas."""
        db_path = tmp_path / "nonexistent.db"

        result = hash_exists_in_db(db_path, "abc123")

        assert result is False

    def test_gere_erreur_base(self, tmp_path):
        """Gère gracieusement une erreur de base."""
        db_path = tmp_path / "test.db"

        with patch('sqlite3.connect', side_effect=sqlite3.Error("DB Error")):
            result = hash_exists_in_db(db_path, "abc123")
            assert result is False


class TestRemoveHashFromDb:
    """Tests pour la fonction remove_hash_from_db."""

    def test_supprime_hash_existant(self, tmp_path):
        """Supprime un hash existant."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        cursor.execute(
            'INSERT INTO file_hashes (hash, filepath, filename, file_size) VALUES (?, ?, ?, ?)',
            ("abc123", "/test/path", "test.mkv", 1000)
        )
        conn.commit()
        conn.close()

        result = remove_hash_from_db(db_path, "abc123")

        assert result is True

        # Vérifier que le hash n'existe plus
        assert hash_exists_in_db(db_path, "abc123") is False

    def test_retourne_false_hash_inexistant(self, tmp_path):
        """Retourne False si le hash n'existe pas."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        conn.commit()
        conn.close()

        result = remove_hash_from_db(db_path, "nonexistent")

        assert result is False


class TestGetHashInfo:
    """Tests pour la fonction get_hash_info."""

    def test_retourne_info_hash_existant(self, tmp_path):
        """Retourne les informations d'un hash existant."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        cursor.execute(
            'INSERT INTO file_hashes (hash, filepath, filename, file_size) VALUES (?, ?, ?, ?)',
            ("abc123", "/test/path/test.mkv", "test.mkv", 1000)
        )
        conn.commit()
        conn.close()

        result = get_hash_info(db_path, "abc123")

        assert result is not None
        assert result['hash'] == "abc123"
        assert result['filepath'] == "/test/path/test.mkv"
        assert result['filename'] == "test.mkv"
        assert result['file_size'] == 1000

    def test_retourne_none_hash_inexistant(self, tmp_path):
        """Retourne None pour un hash inexistant."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE file_hashes
                         (hash TEXT PRIMARY KEY, filepath TEXT, filename TEXT, file_size INTEGER)''')
        conn.commit()
        conn.close()

        result = get_hash_info(db_path, "nonexistent")

        assert result is None
