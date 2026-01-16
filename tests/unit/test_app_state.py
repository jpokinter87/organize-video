"""Tests unitaires pour le module app_state."""

import pytest
import time
from pathlib import Path

from organize.utils.app_state import (
    AppStateManager,
    get_app_state,
    load_last_exec,
    get_last_exec_readonly,
)
from organize.config import DEFAULT_SECONDS_BACK


class TestAppStateManager:
    """Tests pour la classe AppStateManager."""

    def test_initialisation_cree_table(self, tmp_path):
        """L'initialisation crée la table app_state."""
        db_path = tmp_path / "test_state.db"

        manager = AppStateManager(db_path)

        # Vérifier que la table existe
        cursor = manager.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'"
        )
        assert cursor.fetchone() is not None
        manager.close()

    def test_get_last_exec_defaut(self, tmp_path):
        """Retourne la valeur par défaut si non défini."""
        db_path = tmp_path / "test_state.db"

        with AppStateManager(db_path) as manager:
            result = manager.get_last_exec()

        # Doit retourner environ 3 jours avant
        expected = time.time() - DEFAULT_SECONDS_BACK
        assert abs(result - expected) < 5  # Tolérance de 5 secondes

    def test_set_et_get_last_exec(self, tmp_path):
        """set_last_exec et get_last_exec fonctionnent ensemble."""
        db_path = tmp_path / "test_state.db"
        test_time = time.time() - 86400  # 1 jour avant

        with AppStateManager(db_path) as manager:
            success = manager.set_last_exec(test_time)
            result = manager.get_last_exec()

        assert success is True
        assert result == test_time

    def test_get_last_exec_and_update_atomique(self, tmp_path):
        """get_last_exec_and_update lit et met à jour atomiquement."""
        db_path = tmp_path / "test_state.db"
        test_time = time.time() - 86400  # 1 jour avant

        with AppStateManager(db_path) as manager:
            # Définir une valeur initiale
            manager.set_last_exec(test_time)

            before = time.time()
            # Appeler get_last_exec_and_update
            old_value = manager.get_last_exec_and_update()
            after = time.time()

            # Doit retourner l'ancienne valeur
            assert old_value == test_time

            # La nouvelle valeur doit être le timestamp actuel
            new_value = manager.get_last_exec()
            assert before <= new_value <= after

    def test_context_manager(self, tmp_path):
        """Le context manager ferme correctement la connexion."""
        db_path = tmp_path / "test_state.db"

        with AppStateManager(db_path) as manager:
            assert manager.conn is not None

        assert manager.conn is None

    def test_set_last_exec_timestamp_auto(self, tmp_path):
        """set_last_exec utilise time.time() si pas de timestamp fourni."""
        db_path = tmp_path / "test_state.db"

        before = time.time()
        with AppStateManager(db_path) as manager:
            manager.set_last_exec()  # Sans argument
            result = manager.get_last_exec()
        after = time.time()

        assert before <= result <= after


class TestLoadLastExec:
    """Tests pour la fonction load_last_exec."""

    def test_cree_base_si_inexistante(self, tmp_path, monkeypatch):
        """Crée la base de données si elle n'existe pas."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        result = load_last_exec()

        # Doit retourner un timestamp valide
        assert result > 0
        expected = time.time() - DEFAULT_SECONDS_BACK
        assert abs(result - expected) < 5

    def test_lit_valeur_existante(self, tmp_path, monkeypatch):
        """Lit la date depuis une base existante."""
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

        result = load_last_exec()

        assert result == test_time

    def test_met_a_jour_apres_lecture(self, tmp_path, monkeypatch):
        """Met à jour la base avec la date actuelle après lecture."""
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


class TestGetLastExecReadonly:
    """Tests pour la fonction get_last_exec_readonly."""

    def test_ne_modifie_pas_base(self, tmp_path, monkeypatch):
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

        # La base ne doit pas avoir été modifiée
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


class TestGetAppState:
    """Tests pour la fonction get_app_state."""

    def test_retourne_instance_singleton(self, tmp_path, monkeypatch):
        """Retourne la même instance à chaque appel."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        state1 = get_app_state()
        state2 = get_app_state()

        assert state1 is state2

    def test_cree_nouvelle_instance_si_fermee(self, tmp_path, monkeypatch):
        """Crée une nouvelle instance si la précédente est fermée."""
        monkeypatch.chdir(tmp_path)

        # Réinitialiser l'état global
        import organize.utils.app_state as app_state_module
        app_state_module._app_state = None

        state1 = get_app_state()
        state1.close()

        state2 = get_app_state()

        assert state1 is not state2
        assert state2.conn is not None
