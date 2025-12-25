"""Tests for ExecutionContext."""

import pytest
from pathlib import Path

from organize.config.context import (
    ExecutionContext,
    get_context,
    set_context,
    execution_context,
)


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        ctx = ExecutionContext()
        assert ctx.dry_run is False
        assert ctx.force_mode is False
        assert ctx.search_dir is None
        assert ctx.storage_dir is None

    def test_custom_values(self):
        """Custom values can be set."""
        ctx = ExecutionContext(
            dry_run=True,
            force_mode=True,
            search_dir=Path("/search"),
            storage_dir=Path("/storage"),
        )
        assert ctx.dry_run is True
        assert ctx.force_mode is True
        assert ctx.search_dir == Path("/search")
        assert ctx.storage_dir == Path("/storage")

    def test_is_simulation_property(self):
        """is_simulation returns dry_run value."""
        ctx = ExecutionContext(dry_run=True)
        assert ctx.is_simulation is True

        ctx = ExecutionContext(dry_run=False)
        assert ctx.is_simulation is False


class TestGetSetContext:
    """Tests for get_context and set_context functions."""

    def test_get_context_returns_default(self):
        """get_context returns default context initially."""
        # Reset any existing context
        set_context(None)
        ctx = get_context()
        assert ctx.dry_run is False

    def test_set_and_get_context(self):
        """set_context updates global context."""
        custom_ctx = ExecutionContext(dry_run=True, force_mode=True)
        set_context(custom_ctx)

        retrieved = get_context()
        assert retrieved.dry_run is True
        assert retrieved.force_mode is True

        # Cleanup
        set_context(None)

    def test_set_none_resets_to_default(self):
        """Setting None resets to default context."""
        set_context(ExecutionContext(dry_run=True))
        set_context(None)

        ctx = get_context()
        assert ctx.dry_run is False


class TestExecutionContextManager:
    """Tests for execution_context context manager."""

    def test_context_manager_sets_context(self):
        """Context manager sets context for duration."""
        with execution_context(dry_run=True) as ctx:
            assert ctx.dry_run is True
            assert get_context().dry_run is True

    def test_context_manager_restores_previous(self):
        """Context manager restores previous context after."""
        set_context(ExecutionContext(dry_run=False))

        with execution_context(dry_run=True):
            assert get_context().dry_run is True

        assert get_context().dry_run is False

        # Cleanup
        set_context(None)

    def test_nested_context_managers(self):
        """Nested context managers work correctly."""
        with execution_context(dry_run=False, force_mode=False) as outer:
            assert outer.dry_run is False

            with execution_context(dry_run=True, force_mode=True) as inner:
                assert inner.dry_run is True
                assert inner.force_mode is True

            # Outer context restored
            assert get_context().dry_run is False

    def test_context_manager_with_paths(self):
        """Context manager works with path arguments."""
        search = Path("/search")
        storage = Path("/storage")

        with execution_context(search_dir=search, storage_dir=storage) as ctx:
            assert ctx.search_dir == search
            assert ctx.storage_dir == storage

    def test_context_manager_accepts_existing_context(self):
        """Context manager accepts an existing ExecutionContext."""
        ctx = ExecutionContext(
            dry_run=True,
            force_mode=True,
            days_to_process=7.0,
            debug=True,
            tag="test_tag",
        )

        with execution_context(ctx) as active_ctx:
            assert active_ctx is ctx
            assert get_context().dry_run is True
            assert get_context().days_to_process == 7.0
            assert get_context().tag == "test_tag"


class TestExecutionContextNewFields:
    """Tests for new ExecutionContext fields."""

    def test_days_to_process_default(self):
        """days_to_process defaults to 0."""
        ctx = ExecutionContext()
        assert ctx.days_to_process == 0

    def test_debug_and_tag_defaults(self):
        """debug and tag have correct defaults."""
        ctx = ExecutionContext()
        assert ctx.debug is False
        assert ctx.tag == ""

    def test_output_dir_field(self):
        """output_dir can be set."""
        ctx = ExecutionContext(output_dir=Path("/output"))
        assert ctx.output_dir == Path("/output")

    def test_all_new_fields(self):
        """All new fields work together."""
        ctx = ExecutionContext(
            output_dir=Path("/output"),
            days_to_process=30.0,
            debug=True,
            tag="my_tag",
        )
        assert ctx.output_dir == Path("/output")
        assert ctx.days_to_process == 30.0
        assert ctx.debug is True
        assert ctx.tag == "my_tag"
