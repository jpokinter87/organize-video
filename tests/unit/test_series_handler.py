"""Tests for series episode handling."""

import pytest
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from organize.pipeline.series_handler import (
    format_season_folder,
    find_series_folder,
    build_episode_filename,
    should_create_season_folder,
)


class TestFormatSeasonFolder:
    """Tests for format_season_folder function."""

    def test_formats_single_digit(self):
        """Formats single digit season with leading zero."""
        result = format_season_folder(1)
        assert result == "Saison 01"

    def test_formats_double_digit(self):
        """Formats double digit season."""
        result = format_season_folder(10)
        assert result == "Saison 10"

    def test_zero_returns_empty(self):
        """Zero season returns empty string."""
        result = format_season_folder(0)
        assert result == ""


class TestFindSeriesFolder:
    """Tests for find_series_folder function."""

    def test_finds_folder_with_year(self):
        """Finds folder ending with (YYYY)."""
        path = Path("/work/Séries/Breaking Bad (2008)/Saison 01/episode.mkv")
        result = find_series_folder(path)
        assert result.name == "Breaking Bad (2008)"

    def test_returns_parent_when_no_year_found(self):
        """Returns immediate parent when no year pattern found."""
        path = Path("/work/Séries/episode.mkv")
        result = find_series_folder(path)
        assert result == path.parent

    def test_handles_nested_structure(self):
        """Handles deeply nested paths."""
        path = Path("/storage/nas/work/Séries/Show Name (2020)/extras/episode.mkv")
        result = find_series_folder(path)
        assert result.name == "Show Name (2020)"


class TestBuildEpisodeFilename:
    """Tests for build_episode_filename function."""

    def test_builds_complete_filename(self):
        """Builds filename with all components."""
        result = build_episode_filename(
            series_title="Breaking Bad",
            year=2008,
            sequence="- S01E05 -",
            episode_title="Gray Matter",
            spec="MULTi HEVC 1080p",
            extension=".mkv"
        )

        assert "Breaking Bad" in result
        assert "2008" in result
        assert "S01E05" in result
        assert "Gray Matter" in result
        assert "MULTi" in result
        assert ".mkv" in result

    def test_handles_no_episode_title(self):
        """Handles missing episode title."""
        result = build_episode_filename(
            series_title="Show",
            year=2020,
            sequence="- S01E01 -",
            episode_title="",
            spec="FR",
            extension=".mkv"
        )

        assert "Show" in result
        assert "2020" in result
        assert ".mkv" in result

    def test_handles_special_characters(self):
        """Handles special characters in title."""
        result = build_episode_filename(
            series_title="Grey's Anatomy",
            year=2005,
            sequence="- S01E01 -",
            episode_title="Pilot",
            spec="FR",
            extension=".mkv"
        )

        assert "Grey's Anatomy" in result


class TestShouldCreateSeasonFolder:
    """Tests for should_create_season_folder function."""

    def test_returns_true_when_not_in_season(self):
        """Returns True when not already in season folder."""
        current_path = Path("/work/Séries/Show (2020)/episode.mkv")
        result = should_create_season_folder(current_path, 1)
        assert result is True

    def test_returns_false_when_in_season(self):
        """Returns False when already in correct season folder."""
        current_path = Path("/work/Séries/Show (2020)/Saison 01/episode.mkv")
        result = should_create_season_folder(current_path, 1)
        assert result is False

    def test_returns_false_for_zero_season(self):
        """Returns False for season 0."""
        current_path = Path("/work/Séries/Show (2020)/episode.mkv")
        result = should_create_season_folder(current_path, 0)
        assert result is False

    def test_returns_true_for_different_season(self):
        """Returns True when in different season folder."""
        current_path = Path("/work/Séries/Show (2020)/Saison 01/episode.mkv")
        result = should_create_season_folder(current_path, 2)
        assert result is True


class TestOrganizeEpisodeBySeason:
    """Tests pour la fonction organize_episode_by_season."""

    def test_returns_current_path_for_season_zero(self):
        """Retourne le chemin actuel si saison est 0."""
        from organize.pipeline.series_handler import organize_episode_by_season

        current_path = Path("/test/episode.mkv")
        result = organize_episode_by_season(current_path, "episode.mkv", 0)
        assert result == current_path

    def test_dry_run_does_not_create_folder(self, tmp_path):
        """En mode dry_run, ne crée pas de dossiers."""
        from organize.pipeline.series_handler import organize_episode_by_season

        series_dir = tmp_path / "Show (2020)"
        series_dir.mkdir()
        episode = series_dir / "episode.mkv"
        episode.touch()

        result = organize_episode_by_season(episode, "episode.mkv", 1, dry_run=True)

        # Le dossier Saison 01 ne doit pas exister
        season_folder = series_dir / "Saison 01"
        assert not season_folder.exists()
        # Le résultat doit être le nouveau chemin prévu
        assert "Saison 01" in str(result)

    def test_creates_season_folder(self, tmp_path):
        """Crée le dossier saison et déplace le fichier."""
        from organize.pipeline.series_handler import organize_episode_by_season

        series_dir = tmp_path / "Show (2020)"
        series_dir.mkdir()
        episode = series_dir / "episode.mkv"
        episode.touch()

        result = organize_episode_by_season(episode, "new_episode.mkv", 1, dry_run=False)

        # Le dossier Saison 01 doit exister
        season_folder = series_dir / "Saison 01"
        assert season_folder.exists()
        # Le fichier doit avoir été déplacé
        assert (season_folder / "new_episode.mkv").exists()
        assert not episode.exists()

    def test_keeps_in_season_if_already_there(self, tmp_path):
        """Ne déplace pas si déjà dans le bon dossier saison."""
        from organize.pipeline.series_handler import organize_episode_by_season

        series_dir = tmp_path / "Show (2020)"
        season_folder = series_dir / "Saison 01"
        season_folder.mkdir(parents=True)
        episode = season_folder / "episode.mkv"
        episode.touch()

        result = organize_episode_by_season(episode, "new_episode.mkv", 1, dry_run=False)

        # Le fichier doit être renommé dans le même dossier
        assert result.parent == season_folder
        assert (season_folder / "new_episode.mkv").exists()


class TestFormatAndRename:
    """Tests pour la fonction _format_and_rename."""

    def test_does_nothing_for_season_zero(self):
        """Ne fait rien si saison est 0."""
        from organize.pipeline.series_handler import _format_and_rename

        video = MagicMock()
        video.season = 0

        _format_and_rename(video)

        # Aucune modification attendue

    def test_creates_season_folder_when_needed(self, tmp_path):
        """Crée le dossier saison quand nécessaire."""
        from organize.pipeline.series_handler import _format_and_rename

        series_dir = tmp_path / "Ma Série (2020)"
        series_dir.mkdir()
        episode = series_dir / "episode.mkv"
        episode.touch()

        video = MagicMock()
        video.season = 1
        video.complete_path_temp_links = episode
        video.formatted_filename = "Ma Série (2020) - S01E01 - Pilote - FR.mkv"

        _format_and_rename(video, dry_run=False)

        season_folder = series_dir / "Saison 01"
        assert season_folder.exists()

    def test_dry_run_does_not_modify_filesystem(self, tmp_path):
        """En mode dry_run, ne modifie pas le système de fichiers."""
        from organize.pipeline.series_handler import _format_and_rename

        series_dir = tmp_path / "Ma Série (2020)"
        series_dir.mkdir()
        episode = series_dir / "episode.mkv"
        episode.touch()

        video = MagicMock()
        video.season = 1
        video.complete_path_temp_links = episode
        video.formatted_filename = "Ma Série (2020) - S01E01 - Pilote - FR.mkv"

        _format_and_rename(video, dry_run=True)

        # Le fichier original doit toujours exister
        assert episode.exists()
        # Le dossier saison ne doit pas exister
        assert not (series_dir / "Saison 01").exists()


class TestGetEpisodeTitleFromTvdb:
    """Tests pour la fonction _get_episode_title_from_tvdb."""

    @patch.dict('os.environ', {'TVDB_API_KEY': ''})
    def test_returns_unchanged_without_api_key(self):
        """Retourne la vidéo inchangée si pas de clé API."""
        from organize.pipeline.series_handler import _get_episode_title_from_tvdb

        video = MagicMock()
        video.title_fr = "Test Series"

        result_video, serial = _get_episode_title_from_tvdb(video, 0)

        assert result_video == video
        assert serial == 0

    @patch.dict('os.environ', {'TVDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    def test_uses_cached_data(self, mock_cache_class):
        """Utilise les données en cache si disponibles."""
        from organize.pipeline.series_handler import _get_episode_title_from_tvdb

        mock_cache = MagicMock()
        mock_cache_class.return_value.__enter__.return_value = mock_cache
        mock_cache.get_tvdb.return_value = {"episodeName": "Titre Caché"}

        video = MagicMock()
        video.title_fr = "Test Series"
        video.date_film = 2020
        video.season = 1
        video.episode = 1
        video.sequence = "- S01E01 -"
        video.spec = "FR"
        video.complete_path_original = Path("/test/video.mkv")

        result_video, serial = _get_episode_title_from_tvdb(video, 12345)

        assert "Titre Caché" in result_video.formatted_filename
        mock_cache.get_tvdb.assert_called_once()


class TestAddEpisodesTitles:
    """Tests pour la fonction add_episodes_titles."""

    def test_does_nothing_if_no_series(self):
        """Ne fait rien si pas de séries dans la liste."""
        from organize.pipeline.series_handler import add_episodes_titles

        video = MagicMock()
        video.is_serie.return_value = False

        # Ne doit pas lever d'erreur
        add_episodes_titles([video], Path("/test"))

    def test_skips_season_zero(self):
        """Ignore les épisodes avec saison 0."""
        from organize.pipeline.series_handler import add_episodes_titles

        video = MagicMock()
        video.is_serie.return_value = True
        video.season = 0

        # Ne doit pas lever d'erreur
        add_episodes_titles([video], Path("/test"))

    @patch.dict('os.environ', {'TVDB_API_KEY': 'test_key'})
    @patch('organize.api.CacheDB')
    @patch('organize.pipeline.series_handler._format_and_rename')
    def test_processes_series_with_season(self, mock_rename, mock_cache_class):
        """Traite les séries avec saison > 0."""
        from organize.pipeline.series_handler import add_episodes_titles

        mock_cache = MagicMock()
        mock_cache_class.return_value.__enter__.return_value = mock_cache
        mock_cache.get_tvdb.return_value = {"episodeName": "Pilote"}

        video = MagicMock()
        video.is_serie.return_value = True
        video.season = 1
        video.episode = 1
        video.title_fr = "Test Series"
        video.date_film = 2020
        video.sequence = "- S01E01 -"
        video.spec = "FR"
        video.complete_path_original = Path("/test/video.mkv")

        add_episodes_titles([video], Path("/test"), dry_run=True)

        mock_rename.assert_called_once()
