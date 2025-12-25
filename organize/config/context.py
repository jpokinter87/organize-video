"""Execution context for video organization operations."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Generator

# Global context storage
_current_context: Optional["ExecutionContext"] = None


@dataclass
class ExecutionContext:
    """
    Execution context containing runtime configuration.

    Centralizes settings like dry_run mode that need to be
    accessible throughout the application without parameter threading.

    Attributes:
        dry_run: If True, simulate operations without making changes.
        force_mode: If True, skip duplicate checks.
        search_dir: Directory to search for videos.
        storage_dir: Directory for final storage.
        symlinks_dir: Directory for symlinks.
        temp_symlinks_dir: Directory for temporary symlinks.
    """

    dry_run: bool = False
    force_mode: bool = False
    search_dir: Optional[Path] = None
    storage_dir: Optional[Path] = None
    symlinks_dir: Optional[Path] = None
    temp_symlinks_dir: Optional[Path] = None

    @property
    def is_simulation(self) -> bool:
        """Alias for dry_run for readability."""
        return self.dry_run


def get_context() -> ExecutionContext:
    """
    Get the current execution context.

    Returns:
        Current ExecutionContext, or a default one if not set.
    """
    global _current_context
    if _current_context is None:
        return ExecutionContext()
    return _current_context


def set_context(ctx: Optional[ExecutionContext]) -> None:
    """
    Set the global execution context.

    Args:
        ctx: ExecutionContext to set, or None to reset to default.
    """
    global _current_context
    _current_context = ctx


@contextmanager
def execution_context(**kwargs) -> Generator[ExecutionContext, None, None]:
    """
    Context manager for temporarily setting execution context.

    Args:
        **kwargs: Arguments to pass to ExecutionContext constructor.

    Yields:
        The created ExecutionContext.

    Example:
        with execution_context(dry_run=True) as ctx:
            # Operations here see dry_run=True
            process_videos()
        # Previous context restored
    """
    global _current_context
    previous = _current_context

    ctx = ExecutionContext(**kwargs)
    _current_context = ctx

    try:
        yield ctx
    finally:
        _current_context = previous
