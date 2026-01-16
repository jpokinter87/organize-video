"""Tests unitaires pour le module video_list.

Note: Les tests pour load_last_exec et get_last_exec_readonly sont dans
test_app_state.py car ces fonctions utilisent maintenant le stockage SQLite.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from organize.pipeline.video_list import (
    load_last_exec,
    get_last_exec_readonly,
)
from organize.utils.app_state import AppStateManager
from organize.config import DEFAULT_SECONDS_BACK


class TestLoadLastExec:
    """Tests pour la fonction load_last_exec (via app_state)."""

    def test_cree_base_si_inexistante(self, tmp_path, monkeypatch):
        """Crée la base de données si elle n'existe pas."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        result = load_last_exec()

        # Doit retourner un timestamp valide (environ 3 jours avant)
        assert result > 0
        expected = time.time() - DEFAULT_SECONDS_BACK
        assert abs(result - expected) < 5

        # La base doit exister maintenant
        assert (tmp_path / "cache.db").exists()

    def test_lit_fichier_existant(self, tmp_path, monkeypatch):
        """Lit la date depuis une base existante."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        # Créer une valeur dans la base
        test_time = time.time() - 86400  # 1 jour avant
        with AppStateManager(tmp_path / "cache.db") as manager:
            manager.set_last_exec(test_time)

        # Réinitialiser pour forcer la relecture
        app_state_module._app_state = None

        result = load_last_exec()

        assert result == test_time

    def test_met_a_jour_fichier(self, tmp_path, monkeypatch):
        """Met à jour la base avec la date actuelle."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        before = time.time()
        load_last_exec()
        after = time.time()

        # Vérifier que la base contient une date récente
        with AppStateManager(tmp_path / "cache.db") as manager:
            saved_time = manager.get_last_exec()
        assert before <= saved_time <= after

    def test_gere_fichier_invalide(self, tmp_path, monkeypatch):
        """Retourne la valeur par défaut pour une nouvelle base."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        result = load_last_exec()

        # Doit retourner un timestamp par défaut (3 jours avant)
        expected = time.time() - DEFAULT_SECONDS_BACK
        assert abs(result - expected) < 5


class TestGetLastExecReadonly:
    """Tests pour la fonction get_last_exec_readonly (via app_state)."""

    def test_ne_modifie_pas_fichier(self, tmp_path, monkeypatch):
        """Ne modifie pas la base de données."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        # Créer une valeur dans la base
        test_time = time.time() - 86400
        with AppStateManager(tmp_path / "cache.db") as manager:
            manager.set_last_exec(test_time)

        # Réinitialiser pour forcer la relecture
        app_state_module._app_state = None

        # Appeler la fonction readonly
        result = get_last_exec_readonly()

        # Vérifier que la valeur n'a pas changé
        with AppStateManager(tmp_path / "cache.db") as manager:
            stored_time = manager.get_last_exec()
        assert stored_time == test_time
        assert result == test_time

    def test_retourne_defaut_si_inexistant(self, tmp_path, monkeypatch):
        """Retourne une date par défaut si aucune valeur n'est stockée."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        result = get_last_exec_readonly()

        # Doit retourner environ 3 jours avant
        expected = time.time() - DEFAULT_SECONDS_BACK
        assert abs(result - expected) < 5
