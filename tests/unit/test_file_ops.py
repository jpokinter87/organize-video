"""Tests unitaires pour organize.filesystem.file_ops."""

import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.filesystem.file_ops import (
    move_file,
    copy_tree,
    ensure_unique_destination,
    setup_working_directories,
    aplatir_repertoire_series,
    rename_video,
    move_file_new_nas,
    cleanup_directories,
    cleanup_work_directory,
)


class TestMoveFile:
    """Tests for move_file function."""

    def test_moves_file(self, tmp_path):
        """Moves file to destination."""
        source = tmp_path / "source.mkv"
        source.write_text("video content")
        dest = tmp_path / "subdir" / "dest.mkv"

        move_file(source, dest)

        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "video content"

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if needed."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "a" / "b" / "c" / "dest.mkv"

        move_file(source, dest)

        assert dest.exists()

    def test_dry_run_does_not_move(self, tmp_path):
        """Dry run does not move file."""
        source = tmp_path / "source.mkv"
        source.touch()
        dest = tmp_path / "dest.mkv"

        move_file(source, dest, dry_run=True)

        assert source.exists()
        assert not dest.exists()

    def test_handles_same_size_duplicate(self, tmp_path):
        """Removes source when destination has same size."""
        source = tmp_path / "source.mkv"
        source.write_text("content")
        dest = tmp_path / "dest.mkv"
        dest.write_text("content")

        move_file(source, dest)

        assert not source.exists()
        assert dest.exists()

    def test_returns_false_for_missing_source(self, tmp_path):
        """Returns False when source doesn't exist."""
        source = tmp_path / "nonexistent.mkv"
        dest = tmp_path / "dest.mkv"

        result = move_file(source, dest)

        assert result is False


class TestCopyTree:
    """Tests for copy_tree function."""

    def test_copies_directory_tree(self, tmp_path):
        """Copies entire directory tree."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").touch()
        (source / "subdir").mkdir()
        (source / "subdir" / "file2.txt").touch()
        dest = tmp_path / "dest"

        copy_tree(source, dest)

        assert dest.exists()
        assert (dest / "file1.txt").exists()
        assert (dest / "subdir" / "file2.txt").exists()

    def test_dry_run_does_not_copy(self, tmp_path):
        """Dry run does not copy."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").touch()
        dest = tmp_path / "dest"

        copy_tree(source, dest, dry_run=True)

        assert not dest.exists()

    def test_skips_empty_source(self, tmp_path):
        """Skips copy when source is empty."""
        source = tmp_path / "source"
        source.mkdir()
        dest = tmp_path / "dest"

        copy_tree(source, dest)

        assert not dest.exists()

    def test_replaces_existing_destination(self, tmp_path):
        """Replaces existing destination directory."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "new.txt").touch()
        dest = tmp_path / "dest"
        dest.mkdir()
        (dest / "old.txt").touch()

        copy_tree(source, dest)

        assert (dest / "new.txt").exists()
        assert not (dest / "old.txt").exists()


class TestEnsureUniqueDestination:
    """Tests for ensure_unique_destination function."""

    def test_returns_same_path_if_not_exists(self, tmp_path):
        """Returns same path if it doesn't exist."""
        dest = tmp_path / "file.mkv"

        result = ensure_unique_destination(dest)

        assert result == dest

    def test_adds_counter_if_exists(self, tmp_path):
        """Adds counter suffix if file exists."""
        dest = tmp_path / "file.mkv"
        dest.touch()

        result = ensure_unique_destination(dest)

        assert result == tmp_path / "file_1.mkv"

    def test_increments_counter_for_multiple(self, tmp_path):
        """Increments counter for multiple existing files."""
        (tmp_path / "file.mkv").touch()
        (tmp_path / "file_1.mkv").touch()
        (tmp_path / "file_2.mkv").touch()

        result = ensure_unique_destination(tmp_path / "file.mkv")

        assert result == tmp_path / "file_3.mkv"


class TestSetupWorkingDirectories:
    """Tests for setup_working_directories function."""

    def test_returns_directory_paths(self, tmp_path):
        """Returns correct directory paths."""
        work, temp, original, waiting = setup_working_directories(tmp_path)

        assert work == tmp_path.parent / "work"
        assert temp == tmp_path.parent / "tmp"
        assert original == tmp_path.parent / "original"
        assert waiting == tmp_path.parent / "_a_virer"

    def test_dry_run_does_not_create(self, tmp_path):
        """Dry run does not create directories."""
        # Use a nested path that doesn't exist
        nested = tmp_path / "nested" / "deep"
        work, temp, original, waiting = setup_working_directories(nested, dry_run=True)

        # The returned paths should not be created in dry_run mode
        assert not work.exists()
        assert not temp.exists()


class TestAplatirRepertoireSeries:
    """Tests pour aplatir_repertoire_series."""

    def test_aplatit_structures_imbriquees(self, tmp_path):
        """Aplatit les structures de séries imbriquées."""
        series_dir = tmp_path / "Séries"
        series_dir.mkdir()
        show_dir = series_dir / "ShowName"
        show_dir.mkdir()
        nested = show_dir / "nested_folder"
        nested.mkdir()
        (nested / "episode.mkv").touch()

        aplatir_repertoire_series(tmp_path)

        assert (show_dir / "episode.mkv").exists()

    def test_gere_repertoire_manquant(self, tmp_path):
        """Gère l'absence du répertoire Séries sans erreur."""
        # Ne devrait pas lever d'exception
        aplatir_repertoire_series(tmp_path)

    def test_gere_plusieurs_niveaux(self, tmp_path):
        """Aplatit les fichiers des sous-répertoires vers le niveau parent."""
        series_dir = tmp_path / "Séries"
        series_dir.mkdir()
        show_dir = series_dir / "Breaking Bad"
        show_dir.mkdir()
        season_dir = show_dir / "Saison 01"
        season_dir.mkdir()
        (season_dir / "S01E01.mkv").touch()
        (season_dir / "S01E02.mkv").touch()

        aplatir_repertoire_series(tmp_path)

        # Les fichiers devraient être remontés au niveau show_dir
        assert (show_dir / "S01E01.mkv").exists()
        assert (show_dir / "S01E02.mkv").exists()


class TestRenameVideo:
    """Tests pour rename_video."""

    def test_dry_run_definit_chemin_sans_deplacer(self):
        """Mode dry_run définit le chemin sans déplacer le fichier."""
        video = MagicMock()
        video.is_serie.return_value = False
        video.is_not_doc.return_value = True
        video.destination_file = Path("/tmp/test.mkv")
        video.formatted_filename = "Test (2020) MULTI x264 1080p.mkv"

        rename_video(video, {}, "Films", Path("/tmp/work"), dry_run=True)

        assert video.complete_path_temp_links is not None

    def test_cree_repertoire_destination(self, tmp_path):
        """Crée le répertoire de destination si nécessaire."""
        source = tmp_path / "source.mkv"
        source.touch()
        work_dir = tmp_path / "work"

        video = MagicMock()
        video.is_serie.return_value = False
        video.is_not_doc.return_value = True
        video.destination_file = source
        video.formatted_filename = "Test.mkv"

        rename_video(video, {}, "Films", work_dir, dry_run=False)

        assert (work_dir / "Films").exists()

    def test_gere_series_avec_cache(self, tmp_path):
        """Gère les séries avec le cache de titres."""
        source = tmp_path / "source.mkv"
        source.touch()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        video = MagicMock()
        video.is_serie.return_value = True
        video.is_not_doc.return_value = True
        video.destination_file = source
        video.title_fr = "Breaking Bad"
        video.date_film = 2008
        video.formatted_filename = "Breaking Bad S01E01.mkv"

        dic_serie = {
            "Breaking Bad": (
                "Breaking Bad", 2008, "Drama",
                Path("/symlinks/series"), Path("Séries/b-c/Breaking Bad (2008)")
            )
        }

        rename_video(video, dic_serie, "Séries", work_dir, dry_run=True)

        assert video.complete_path_temp_links is not None


class TestMoveFileNewNas:
    """Tests pour move_file_new_nas."""

    def test_dry_run_ne_deplace_pas(self, tmp_path):
        """Mode dry_run log uniquement sans déplacer le fichier."""
        source = tmp_path / "source.mkv"
        source.touch()

        video = MagicMock()
        video.complete_path_original = source
        video.complete_path_temp_links = tmp_path / "work" / "Films" / "test.mkv"

        move_file_new_nas(video, tmp_path / "storage", dry_run=True)

        assert source.exists()

    def test_deplace_vers_stockage(self, tmp_path):
        """Déplace le fichier vers le stockage NAS."""
        source = tmp_path / "source.mkv"
        source.write_text("contenu video")
        storage = tmp_path / "storage"
        work_dir = tmp_path / "work"

        video = MagicMock()
        video.complete_path_original = source
        video.complete_path_temp_links = work_dir / "Films" / "test.mkv"
        video.complete_path_temp_links.parent.mkdir(parents=True, exist_ok=True)

        move_file_new_nas(video, storage, dry_run=False)

        assert not source.exists()

    def test_gere_fichier_existant_meme_taille(self, tmp_path):
        """Gère les doublons de même taille en supprimant la source."""
        source = tmp_path / "source.mkv"
        source.write_text("contenu")
        storage = tmp_path / "storage"
        dest = storage / "Films" / "test.mkv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("contenu")  # Même taille

        video = MagicMock()
        video.complete_path_original = source
        video.complete_path_temp_links = tmp_path / "work" / "Films" / "test.mkv"
        video.complete_path_temp_links.parent.mkdir(parents=True, exist_ok=True)

        move_file_new_nas(video, storage, dry_run=False)

        assert not source.exists()
        assert dest.exists()


class TestCleanupDirectories:
    """Tests pour cleanup_directories."""

    def test_supprime_repertoires_non_vides(self, tmp_path):
        """Supprime les répertoires non vides."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "file.txt").touch()

        cleanup_directories(dir1)

        assert not dir1.exists()

    def test_gere_repertoires_inexistants(self, tmp_path):
        """Gère les répertoires inexistants sans erreur."""
        non_existent = tmp_path / "nonexistent"

        # Ne devrait pas lever d'exception
        cleanup_directories(non_existent)

    def test_nettoie_plusieurs_repertoires(self, tmp_path):
        """Nettoie plusieurs répertoires en une seule fois."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "file1.txt").touch()
        (dir2 / "file2.txt").touch()

        cleanup_directories(dir1, dir2)

        assert not dir1.exists()
        assert not dir2.exists()

    def test_ignore_repertoire_vide(self, tmp_path):
        """Ignore les répertoires vides."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        cleanup_directories(empty_dir)

        # Un répertoire vide ne devrait pas être supprimé
        # (la fonction vérifie any(directory.iterdir()))
        assert empty_dir.exists()


class TestCleanupWorkDirectory:
    """Tests pour cleanup_work_directory."""

    def test_gere_repertoire_inexistant(self, tmp_path):
        """Gère les répertoires inexistants sans erreur."""
        non_existent = tmp_path / "nonexistent"

        # Ne devrait pas lever d'exception
        cleanup_work_directory(non_existent)

    def test_supprime_saisons_imbriquees(self, tmp_path):
        """Supprime les dossiers Saison imbriqués et remonte les fichiers."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        saison_dir = work_dir / "Saison 01"
        saison_dir.mkdir()
        nested_saison = saison_dir / "Saison 01"
        nested_saison.mkdir()
        (nested_saison / "episode.mkv").touch()

        cleanup_work_directory(work_dir)

        # Le fichier devrait être remonté au niveau supérieur
        assert (saison_dir / "episode.mkv").exists()
        assert not nested_saison.exists()

    def test_preserve_structure_normale(self, tmp_path):
        """Préserve la structure normale sans doublons."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        saison_dir = work_dir / "Saison 01"
        saison_dir.mkdir()
        (saison_dir / "episode.mkv").touch()

        cleanup_work_directory(work_dir)

        assert (saison_dir / "episode.mkv").exists()

    def test_gere_plusieurs_saisons_imbriquees(self, tmp_path):
        """Gère plusieurs saisons avec imbrication."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        # Saison 01 avec imbrication
        saison01 = work_dir / "Saison 01"
        saison01.mkdir()
        nested01 = saison01 / "Saison 01"
        nested01.mkdir()
        (nested01 / "S01E01.mkv").touch()

        # Saison 02 sans imbrication
        saison02 = work_dir / "Saison 02"
        saison02.mkdir()
        (saison02 / "S02E01.mkv").touch()

        cleanup_work_directory(work_dir)

        assert (saison01 / "S01E01.mkv").exists()
        assert not nested01.exists()
        assert (saison02 / "S02E01.mkv").exists()
