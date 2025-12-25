"""Tests for user confirmation functions."""

import pytest
from unittest.mock import MagicMock, patch

from organize.ui.confirmations import (
    parse_user_response,
    get_available_genres,
    validate_genre_selection,
    ConfirmationResult,
)


class TestParseUserResponse:
    """Tests for parse_user_response function."""

    def test_empty_string_is_accept(self):
        """Empty string means accept."""
        result = parse_user_response("")
        assert result == ConfirmationResult.ACCEPT

    def test_y_is_accept(self):
        """'y' means accept."""
        result = parse_user_response("y")
        assert result == ConfirmationResult.ACCEPT

    def test_yes_is_accept(self):
        """'yes' means accept."""
        result = parse_user_response("yes")
        assert result == ConfirmationResult.ACCEPT

    def test_oui_is_accept(self):
        """'oui' means accept."""
        result = parse_user_response("oui")
        assert result == ConfirmationResult.ACCEPT

    def test_n_is_reject(self):
        """'n' means reject."""
        result = parse_user_response("n")
        assert result == ConfirmationResult.REJECT

    def test_no_is_reject(self):
        """'no' means reject."""
        result = parse_user_response("no")
        assert result == ConfirmationResult.REJECT

    def test_non_is_reject(self):
        """'non' means reject."""
        result = parse_user_response("non")
        assert result == ConfirmationResult.REJECT

    def test_m_is_manual(self):
        """'m' means manual input."""
        result = parse_user_response("m")
        assert result == ConfirmationResult.MANUAL

    def test_manual_is_manual(self):
        """'manual' means manual input."""
        result = parse_user_response("manual")
        assert result == ConfirmationResult.MANUAL

    def test_v_is_view(self):
        """'v' means view video."""
        result = parse_user_response("v")
        assert result == ConfirmationResult.VIEW

    def test_case_insensitive(self):
        """Parsing is case insensitive."""
        assert parse_user_response("YES") == ConfirmationResult.ACCEPT
        assert parse_user_response("NO") == ConfirmationResult.REJECT

    def test_unknown_is_unknown(self):
        """Unknown input returns UNKNOWN."""
        result = parse_user_response("xyz")
        assert result == ConfirmationResult.UNKNOWN


class TestGetAvailableGenres:
    """Tests for get_available_genres function."""

    def test_returns_list(self):
        """Returns a list of genres."""
        genres = get_available_genres()
        assert isinstance(genres, list)
        assert len(genres) > 0

    def test_contains_expected_genres(self):
        """Contains expected genre names."""
        genres = get_available_genres()
        assert "Action & Aventure" in genres
        assert "Drame" in genres
        assert "Comédie" in genres

    def test_includes_non_detecte(self):
        """Includes 'Non détecté' option."""
        genres = get_available_genres()
        assert "Non détecté" in genres


class TestValidateGenreSelection:
    """Tests for validate_genre_selection function."""

    def test_valid_number(self):
        """Valid number returns genre."""
        genres = get_available_genres()
        result = validate_genre_selection("1", genres)
        assert result == genres[0]

    def test_last_number(self):
        """Last valid number returns last genre."""
        genres = get_available_genres()
        result = validate_genre_selection(str(len(genres)), genres)
        assert result == genres[-1]

    def test_zero_is_invalid(self):
        """Zero is invalid selection."""
        genres = get_available_genres()
        result = validate_genre_selection("0", genres)
        assert result is None

    def test_too_high_is_invalid(self):
        """Number too high is invalid."""
        genres = get_available_genres()
        result = validate_genre_selection("999", genres)
        assert result is None

    def test_non_number_is_invalid(self):
        """Non-numeric input is invalid."""
        genres = get_available_genres()
        result = validate_genre_selection("abc", genres)
        assert result is None

    def test_empty_is_invalid(self):
        """Empty input is invalid."""
        genres = get_available_genres()
        result = validate_genre_selection("", genres)
        assert result is None
