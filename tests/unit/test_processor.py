"""Tests for video processor functions."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.pipeline.processor import (
    create_video_from_file,
    should_skip_duplicate,
    VideoProcessingResult,
)


class TestCreateVideoFromFile:
    """Tests for create_video_from_file function."""

    def test_creates_video_with_path(self):
        """Creates Video with complete_path_original set."""
        file_path = Path("/Films/Movie.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Films"):
                video = create_video_from_file(file_path)

        assert video.complete_path_original == file_path
        assert video.hash == "abc123"
        assert video.type_file == "Films"

    def test_sets_extended_sub_for_series(self):
        """Sets extended_sub correctly for series."""
        file_path = Path("/Séries/Show/episode.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Séries"):
                video = create_video_from_file(file_path)

        assert "Séries TV" in str(video.extended_sub)

    def test_extended_sub_empty_for_films(self):
        """extended_sub is empty for films."""
        file_path = Path("/Films/Movie.mkv")

        with patch('organize.pipeline.processor.checksum_md5', return_value="abc123"):
            with patch('organize.pipeline.processor.type_of_video', return_value="Films"):
                video = create_video_from_file(file_path)

        assert str(video.extended_sub) == "" or str(video.extended_sub) == "."


class TestShouldSkipDuplicate:
    """Tests for should_skip_duplicate function."""

    def test_skip_in_dry_run(self):
        """Should not skip in dry run mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=True,
            hash_exists_fn=lambda h: True
        )
        assert result is False

    def test_skip_in_force_mode(self):
        """Should not skip in force mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=True,
            dry_run=False,
            hash_exists_fn=lambda h: True
        )
        assert result is False

    def test_skip_when_hash_exists(self):
        """Should skip when hash exists in normal mode."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=False,
            hash_exists_fn=lambda h: True
        )
        assert result is True

    def test_no_skip_when_hash_not_exists(self):
        """Should not skip when hash doesn't exist."""
        result = should_skip_duplicate(
            hash_value="abc123",
            force_mode=False,
            dry_run=False,
            hash_exists_fn=lambda h: False
        )
        assert result is False


class TestVideoProcessingResult:
    """Tests for VideoProcessingResult dataclass."""

    def test_success_result(self):
        """Creates success result."""
        video = MagicMock()
        result = VideoProcessingResult(success=True, video=video)

        assert result.success is True
        assert result.video is video
        assert result.error is None
        assert result.skipped is False

    def test_error_result(self):
        """Creates error result."""
        result = VideoProcessingResult(success=False, error="File not found")

        assert result.success is False
        assert result.video is None
        assert result.error == "File not found"

    def test_skipped_result(self):
        """Creates skipped result."""
        result = VideoProcessingResult(success=True, skipped=True, skip_reason="Duplicate")

        assert result.success is True
        assert result.skipped is True
        assert result.skip_reason == "Duplicate"

    def test_skip_without_hash(self):
        """Ne devrait pas échouer si hash est None."""
        result = should_skip_duplicate(
            hash_value=None,
            force_mode=False,
            dry_run=False,
            hash_exists_fn=lambda h: True
        )
        assert result is False


class TestProcessVideoMetadata:
    """Tests pour la fonction process_video_metadata."""

    @patch('organize.classification.type_detector.extract_file_infos')
    def test_extrait_metadonnees(self, mock_extract):
        """Extrait correctement les métadonnées du fichier."""
        from organize.pipeline.processor import process_video_metadata
        from organize.models.video import Video

        mock_extract.return_value = (
            "My Movie",       # title
            2020,             # date_film
            "",               # sequence
            0,                # season
            0,                # episode
            "1080p MULTi"     # spec
        )

        video = Video()
        video.complete_path_original = Path("/test/My.Movie.2020.mkv")

        result = process_video_metadata(video)

        assert result.title == "My Movie"
        assert result.date_film == 2020
        assert result.spec == "1080p MULTi"

    @patch('organize.classification.type_detector.extract_file_infos')
    def test_extrait_metadonnees_serie(self, mock_extract):
        """Extrait les métadonnées d'une série."""
        from organize.pipeline.processor import process_video_metadata
        from organize.models.video import Video

        mock_extract.return_value = (
            "My Show",
            2018,
            "- S01E05 -",
            1,
            5,
            "FR"
        )

        video = Video()
        video.complete_path_original = Path("/test/My.Show.S01E05.mkv")

        result = process_video_metadata(video)

        assert result.title == "My Show"
        assert result.season == 1
        assert result.episode == 5


class TestProcessSingleVideoFile:
    """Tests pour la fonction process_single_video_file."""

    @patch('organize.pipeline.processor.create_video_from_file')
    @patch('organize.pipeline.processor.process_video_metadata')
    def test_traite_fichier_simple(self, mock_metadata, mock_create):
        """Traite un fichier vidéo simple."""
        from organize.pipeline.processor import process_single_video_file

        video = MagicMock()
        video.hash = "abc123"
        mock_create.return_value = video
        mock_metadata.return_value = video

        result = process_single_video_file(Path("/test/movie.mkv"))

        assert result.success is True
        assert result.video is not None

    @patch('organize.pipeline.processor.create_video_from_file')
    def test_skip_duplicate(self, mock_create):
        """Ignore les doublons."""
        from organize.pipeline.processor import process_single_video_file

        video = MagicMock()
        video.hash = "abc123"
        mock_create.return_value = video

        result = process_single_video_file(
            Path("/test/movie.mkv"),
            hash_exists_fn=lambda h: True
        )

        assert result.success is True
        assert result.skipped is True

    @patch('organize.pipeline.processor.create_video_from_file')
    @patch('organize.pipeline.processor.process_video_metadata')
    def test_dry_run_pas_de_skip(self, mock_metadata, mock_create):
        """En mode dry_run, n'ignore pas les doublons."""
        from organize.pipeline.processor import process_single_video_file

        video = MagicMock()
        video.hash = "abc123"
        mock_create.return_value = video
        mock_metadata.return_value = video

        result = process_single_video_file(
            Path("/test/movie.mkv"),
            dry_run=True,
            hash_exists_fn=lambda h: True
        )

        assert result.success is True
        assert result.skipped is False

    @patch('organize.pipeline.processor.create_video_from_file')
    def test_gere_erreur(self, mock_create):
        """Gère les erreurs lors du traitement."""
        from organize.pipeline.processor import process_single_video_file

        mock_create.side_effect = Exception("Test error")

        result = process_single_video_file(Path("/test/movie.mkv"))

        assert result.success is False
        assert "Test error" in result.error


class TestCreatePaths:
    """Tests pour la fonction create_paths."""

    def test_creation_chemin_film(self, tmp_path):
        """Crée correctement le chemin pour un film."""
        from organize.pipeline.processor import create_paths
        from organize.models.video import Video

        with patch('organize.filesystem.symlinks.create_symlink'):
            video = Video()
            video.complete_path_original = tmp_path / "movie.mkv"
            video.type_file = "Films"
            (tmp_path / "movie.mkv").touch()

            create_paths(video.complete_path_original, video, tmp_path)

            assert video.destination_file is not None
            assert "Films" in str(video.destination_file)

    def test_dry_run_pas_de_creation(self, tmp_path):
        """En mode dry_run, ne crée pas de liens."""
        from organize.pipeline.processor import create_paths
        from organize.models.video import Video

        video = Video()
        video.complete_path_original = tmp_path / "movie.mkv"
        video.type_file = "Films"
        (tmp_path / "movie.mkv").touch()

        create_paths(video.complete_path_original, video, tmp_path, dry_run=True)

        assert video.destination_file is not None
        # En dry_run, le lien n'est pas vraiment créé

    def test_creation_chemin_animation(self, tmp_path):
        """Crée correctement le chemin pour une animation."""
        from organize.pipeline.processor import create_paths
        from organize.models.video import Video

        with patch('organize.filesystem.symlinks.create_symlink'):
            video = Video()
            video.complete_path_original = tmp_path / "animation.mkv"
            video.type_file = "Animation"
            (tmp_path / "animation.mkv").touch()

            create_paths(video.complete_path_original, video, tmp_path)

            assert video.destination_file is not None
            assert "Films" in str(video.destination_file)
            assert "Animation" in str(video.destination_file)


class TestProcessVideo:
    """Tests pour la fonction process_video."""

    @patch('organize.filesystem.paths.find_similar_file')
    def test_retourne_video_si_pas_similar(self, mock_find):
        """Retourne la vidéo si pas de fichier similaire."""
        from organize.pipeline.processor import process_video

        mock_find.return_value = None

        video = MagicMock()
        video.is_film_anim.return_value = True

        result = process_video(
            video,
            Path("/wait"),
            Path("/storage"),
            Path("/symlinks")
        )

        assert result == video

    @patch('organize.filesystem.paths.find_similar_file')
    @patch('organize.filesystem.file_ops.handle_similar_file')
    def test_gere_fichier_similaire(self, mock_handle, mock_find):
        """Gère correctement un fichier similaire."""
        from organize.pipeline.processor import process_video

        mock_find.return_value = Path("/storage/similar.mkv")
        mock_handle.return_value = Path("/storage/new.mkv")

        video = MagicMock()
        video.is_film_anim.return_value = True
        video.complete_path_original = Path("/test/movie.mkv")

        result = process_video(
            video,
            Path("/wait"),
            Path("/storage"),
            Path("/symlinks")
        )

        assert result.complete_path_original == Path("/storage/new.mkv")

    @patch('organize.filesystem.paths.find_similar_file')
    @patch('organize.filesystem.file_ops.handle_similar_file')
    def test_retourne_none_si_garde_ancien(self, mock_handle, mock_find):
        """Retourne None si l'utilisateur garde l'ancien fichier."""
        from organize.pipeline.processor import process_video

        similar = Path("/storage/similar.mkv")
        mock_find.return_value = similar
        mock_handle.return_value = similar  # Garde l'ancien

        video = MagicMock()
        video.is_film_anim.return_value = True

        result = process_video(
            video,
            Path("/wait"),
            Path("/storage"),
            Path("/symlinks")
        )

        assert result is None

    def test_serie_pas_de_verification(self):
        """Les séries ne sont pas vérifiées pour similarité."""
        from organize.pipeline.processor import process_video

        video = MagicMock()
        video.is_film_anim.return_value = False

        result = process_video(
            video,
            Path("/wait"),
            Path("/storage"),
            Path("/symlinks")
        )

        assert result == video
