"""Tests unitaires pour le module orchestrator."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.pipeline.orchestrator import (
    ProcessingStats,
    PipelineContext,
    PipelineOrchestrator,
)
from organize.config import GENRE_UNDETECTED


class TestProcessingStats:
    """Tests pour la classe ProcessingStats."""

    def test_initialisation_defaut(self):
        """Initialise avec des valeurs par défaut."""
        stats = ProcessingStats()
        assert stats.films == 0
        assert stats.series == 0
        assert stats.animation == 0
        assert stats.docs == 0
        assert stats.undetected == 0
        assert stats.total == 0

    def test_from_videos_films(self):
        """Calcule les statistiques pour les films."""
        video = MagicMock()
        video.is_film.return_value = True
        video.is_serie.return_value = False
        video.is_animation.return_value = False
        video.is_film_anim.return_value = True
        video.type_file = "Films"
        video.title_fr = "Mon Film"
        video.genre = "Action"

        stats = ProcessingStats.from_videos([video])

        assert stats.films == 1
        assert stats.total == 1

    def test_from_videos_series(self):
        """Calcule les statistiques pour les séries."""
        video = MagicMock()
        video.is_film.return_value = False
        video.is_serie.return_value = True
        video.is_animation.return_value = False
        video.is_film_anim.return_value = False
        video.type_file = "Séries"
        video.title_fr = "Ma Série"

        stats = ProcessingStats.from_videos([video])

        assert stats.series == 1
        assert stats.total == 1

    def test_from_videos_undetected(self):
        """Compte les fichiers non détectés."""
        video = MagicMock()
        video.is_film.return_value = True
        video.is_serie.return_value = False
        video.is_animation.return_value = False
        video.is_film_anim.return_value = True
        video.type_file = "Films"
        video.title_fr = ""  # Non détecté
        video.genre = GENRE_UNDETECTED

        stats = ProcessingStats.from_videos([video])

        assert stats.undetected == 1

    def test_from_videos_multiple(self):
        """Calcule les statistiques pour plusieurs vidéos."""
        film = MagicMock()
        film.is_film.return_value = True
        film.is_serie.return_value = False
        film.is_animation.return_value = False
        film.is_film_anim.return_value = True
        film.type_file = "Films"
        film.title_fr = "Film"
        film.genre = "Drame"

        serie = MagicMock()
        serie.is_film.return_value = False
        serie.is_serie.return_value = True
        serie.is_animation.return_value = False
        serie.is_film_anim.return_value = False
        serie.type_file = "Séries"
        serie.title_fr = "Série"

        animation = MagicMock()
        animation.is_film.return_value = False
        animation.is_serie.return_value = False
        animation.is_animation.return_value = True
        animation.is_film_anim.return_value = True
        animation.type_file = "Animation"
        animation.title_fr = "Animation"
        animation.genre = "Animation/Enfant"

        stats = ProcessingStats.from_videos([film, serie, animation])

        assert stats.films == 1
        assert stats.series == 1
        assert stats.animation == 1
        assert stats.total == 3


class TestPipelineContext:
    """Tests pour la classe PipelineContext."""

    def test_creation_avec_chemins(self, tmp_path):
        """Crée un contexte avec les chemins requis."""
        context = PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
        )

        assert context.search_dir == tmp_path / "search"
        assert context.dry_run is False
        assert context.force_mode is False

    def test_creation_avec_options(self, tmp_path):
        """Crée un contexte avec les options."""
        context = PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
            dry_run=True,
            force_mode=True,
            days_to_process=7,
        )

        assert context.dry_run is True
        assert context.force_mode is True
        assert context.days_to_process == 7


class TestPipelineOrchestrator:
    """Tests pour la classe PipelineOrchestrator."""

    @pytest.fixture
    def context(self, tmp_path):
        """Crée un contexte de test."""
        return PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
        )

    def test_initialisation(self, context):
        """Initialise l'orchestrateur."""
        orchestrator = PipelineOrchestrator(context)

        assert orchestrator.context == context
        assert orchestrator._title_cache == {}

    def test_apply_cached_metadata(self, context):
        """Applique les métadonnées depuis le cache."""
        orchestrator = PipelineOrchestrator(context)

        # Ajouter au cache
        orchestrator._title_cache["Test"] = (
            "Titre FR",
            2020,
            "Drame",
            Path("/symlinks/Drame"),
            Path("Films/Drame"),
            "1080p MULTi"
        )

        video = MagicMock()
        video.title = "Test"
        video.spec = ""

        orchestrator._apply_cached_metadata(video, "Test")

        assert video.title_fr == "Titre FR"
        assert video.date_film == 2020
        assert video.genre == "Drame"
        assert video.spec == "1080p MULTi"

    def test_apply_cached_keeps_spec_if_present(self, context):
        """Conserve le spec original si déjà renseigné."""
        orchestrator = PipelineOrchestrator(context)

        orchestrator._title_cache["Test"] = (
            "Titre FR",
            2020,
            "Drame",
            Path("/symlinks/Drame"),
            Path("Films/Drame"),
            "1080p MULTi"
        )

        video = MagicMock()
        video.title = "Test"
        video.spec = "4K HDR HEVC DTS"  # 4 parties, > 3

        orchestrator._apply_cached_metadata(video, "Test")

        # Le spec original doit être conservé
        assert video.spec == "4K HDR HEVC DTS"

    @patch('organize.pipeline.orchestrator.tqdm')
    def test_process_videos_empty_list(self, mock_tqdm, context):
        """Traite une liste vide."""
        mock_tqdm.return_value.__iter__ = lambda self: iter([])
        mock_tqdm.return_value.__enter__ = lambda self: self
        mock_tqdm.return_value.__exit__ = lambda *args: None

        orchestrator = PipelineOrchestrator(context)
        stats = orchestrator.process_videos([])

        assert stats.total == 0

    def test_process_series_titles_no_series(self, context):
        """Ne fait rien si pas de séries."""
        orchestrator = PipelineOrchestrator(context)

        video = MagicMock()
        video.is_serie.return_value = False

        # Ne doit pas lever d'erreur
        orchestrator.process_series_titles([video])

    def test_process_series_titles_with_series(self, context, tmp_path):
        """Traite les titres des séries."""
        with patch('organize.pipeline.add_episodes_titles') as mock_add, \
             patch('organize.filesystem.cleanup_work_directory'):
            context.work_dir = tmp_path / "work"
            context.work_dir.mkdir()

            orchestrator = PipelineOrchestrator(context)

            video = MagicMock()
            video.is_serie.return_value = True
            video.title_fr = "Ma Série"
            video.season = 1

            orchestrator.process_series_titles([video])

            mock_add.assert_called_once()

    def test_finalize_copie_et_verifie(self, context, tmp_path):
        """Finalise en copiant et vérifiant."""
        with patch('organize.filesystem.copy_tree') as mock_copy, \
             patch('organize.filesystem.verify_symlinks') as mock_verify:
            context.work_dir = tmp_path / "work"
            context.work_dir.mkdir()
            (context.work_dir / "file.txt").touch()

            orchestrator = PipelineOrchestrator(context)
            orchestrator.finalize()

            mock_copy.assert_called_once()
            mock_verify.assert_called_once()

    def test_finalize_dry_run_pas_de_verification(self, context, tmp_path):
        """En mode dry_run, ne vérifie pas les symlinks."""
        with patch('organize.filesystem.copy_tree') as mock_copy, \
             patch('organize.filesystem.verify_symlinks') as mock_verify:
            context.work_dir = tmp_path / "work"
            context.work_dir.mkdir()
            (context.work_dir / "file.txt").touch()
            context.dry_run = True

            orchestrator = PipelineOrchestrator(context)
            orchestrator.finalize()

            mock_copy.assert_called_once()
            mock_verify.assert_not_called()


class TestProcessSingleVideo:
    """Tests pour la méthode _process_single_video."""

    @pytest.fixture
    def context(self, tmp_path):
        """Crée un contexte de test."""
        return PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
        )

    def test_traitement_documentaire(self, context):
        """Les documentaires suivent un chemin simplifié."""
        orchestrator = PipelineOrchestrator(context)

        video = MagicMock()
        video.type_file = "Docs"

        rename_fn = MagicMock()
        move_fn = MagicMock()

        orchestrator._process_single_video(
            video,
            rename_fn,
            move_fn,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        rename_fn.assert_called_once()
        move_fn.assert_called_once()

    def test_utilise_cache_si_present(self, context):
        """Utilise le cache pour les titres répétés."""
        orchestrator = PipelineOrchestrator(context)

        orchestrator._title_cache["Mon Film"] = (
            "Mon Film FR",
            2020,
            "Drame",
            Path("/symlinks/Drame"),
            Path("Films/Drame"),
            "1080p"
        )

        video = MagicMock()
        video.type_file = "Films"
        video.title = "Mon Film"
        video.spec = ""

        process_video_fn = MagicMock(return_value=video)
        rename_fn = MagicMock()
        move_fn = MagicMock()

        orchestrator._process_single_video(
            video,
            rename_fn,
            move_fn,
            process_video_fn,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        # La vidéo doit avoir reçu les données du cache
        assert video.title_fr == "Mon Film FR"


class TestProcessNewVideo:
    """Tests pour la méthode _process_new_video."""

    @pytest.fixture
    def context(self, tmp_path):
        """Crée un contexte de test."""
        return PipelineContext(
            search_dir=tmp_path / "search",
            storage_dir=tmp_path / "storage",
            symlinks_dir=tmp_path / "symlinks",
            output_dir=tmp_path / "output",
            work_dir=tmp_path / "work",
            temp_dir=tmp_path / "temp",
            original_dir=tmp_path / "original",
            waiting_folder=tmp_path / "waiting",
        )

    def test_traitement_video_detectee(self, context):
        """Traite une vidéo détectée normalement."""
        orchestrator = PipelineOrchestrator(context)

        video = MagicMock()
        video.title = "Test"
        video.title_fr = "Test FR"
        video.is_film_anim.return_value = True
        video.spec = "1080p"

        set_fr_title_fn = MagicMock(return_value=video)
        find_symlink_fn = MagicMock(return_value=(Path("/symlinks"), Path("Films/Drame")))
        media_info_fn = MagicMock(return_value=None)

        orchestrator._process_new_video(
            video,
            set_fr_title_fn,
            MagicMock(),
            find_symlink_fn,
            media_info_fn,
            MagicMock(),
        )

        # La vidéo doit être dans le cache
        assert video.title in orchestrator._title_cache

    def test_traitement_video_non_detectee(self, context):
        """Gère une vidéo non détectée."""
        orchestrator = PipelineOrchestrator(context)

        video = MagicMock()
        video.title = "Test"
        video.title_fr = ""  # Non détecté
        video.is_film_anim.return_value = True
        video.spec = "1080p"

        set_fr_title_fn = MagicMock(return_value=video)
        find_directory_fn = MagicMock(return_value=Path("/symlinks/non_detectes"))
        format_undetected_fn = MagicMock(return_value="undetected_file.mkv")

        orchestrator._process_new_video(
            video,
            set_fr_title_fn,
            find_directory_fn,
            MagicMock(),
            MagicMock(),
            format_undetected_fn,
        )

        assert video.genre == GENRE_UNDETECTED
        format_undetected_fn.assert_called_once()
