"""Tests unitaires pour le module video_list."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.pipeline.video_list import (
    load_last_exec,
    get_last_exec_readonly,
)


class TestLoadLastExec:
    """Tests pour la fonction load_last_exec."""

    def test_cree_fichier_si_inexistant(self, tmp_path, monkeypatch):
        """Crée le fichier last_exec_video s'il n'existe pas."""
        monkeypatch.chdir(tmp_path)

        result = load_last_exec()

        # Doit retourner un timestamp valide (environ 3 jours avant)
        assert result > 0
        expected_min = time.time() - 260000  # Un peu plus que 3 jours
        expected_max = time.time() - 259000  # Un peu moins que 3 jours
        assert expected_min < result < expected_max

        # Le fichier doit exister maintenant
        assert (tmp_path / "last_exec_video").exists()

    def test_lit_fichier_existant(self, tmp_path, monkeypatch):
        """Lit la date depuis un fichier existant."""
        monkeypatch.chdir(tmp_path)

        # Créer le fichier avec une date spécifique
        test_time = time.time() - 86400  # 1 jour avant
        (tmp_path / "last_exec_video").write_text(str(test_time))

        result = load_last_exec()

        assert result == test_time

    def test_met_a_jour_fichier(self, tmp_path, monkeypatch):
        """Met à jour le fichier avec la date actuelle."""
        monkeypatch.chdir(tmp_path)

        before = time.time()
        load_last_exec()
        after = time.time()

        # Vérifier que le fichier contient une date récente
        saved_time = float((tmp_path / "last_exec_video").read_text())
        assert before <= saved_time <= after

    def test_gere_fichier_invalide(self, tmp_path, monkeypatch):
        """Gère un fichier avec contenu invalide."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "last_exec_video").write_text("invalid content")

        result = load_last_exec()

        # Doit retourner un timestamp par défaut (3 jours avant)
        assert result > 0


class TestGetLastExecReadonly:
    """Tests pour la fonction get_last_exec_readonly."""

    def test_ne_modifie_pas_fichier(self, tmp_path, monkeypatch):
        """Ne modifie pas le fichier last_exec_video."""
        monkeypatch.chdir(tmp_path)

        # Créer le fichier avec une date spécifique
        test_time = time.time() - 86400
        (tmp_path / "last_exec_video").write_text(str(test_time))

        # Récupérer le contenu original
        original_content = (tmp_path / "last_exec_video").read_text()

        # Appeler la fonction readonly
        result = get_last_exec_readonly()

        # Vérifier que le fichier n'a pas changé
        assert (tmp_path / "last_exec_video").read_text() == original_content
        assert result == test_time

    def test_retourne_defaut_si_inexistant(self, tmp_path, monkeypatch):
        """Retourne une date par défaut si le fichier n'existe pas."""
        monkeypatch.chdir(tmp_path)

        result = get_last_exec_readonly()

        # Doit retourner environ 3 jours avant
        expected_min = time.time() - 260000
        expected_max = time.time() - 259000
        assert expected_min < result < expected_max

        # Le fichier ne doit PAS avoir été créé
        assert not (tmp_path / "last_exec_video").exists()
