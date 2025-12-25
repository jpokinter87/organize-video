"""Entry point for the organize video package.

This module provides the command-line entry point for the video organization tool.
Run with: python -m organize
"""

import sys

from loguru import logger

from organize.config import (
    parse_arguments,
    args_to_cli_args,
    validate_directories,
    execution_context,
    ExecutionContext,
)
from organize.ui import ConsoleUI


def setup_logging(debug: bool = False) -> None:
    """
    Configure loguru logging.

    Args:
        debug: If True, enable debug-level logging.
    """
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    logger.add(
        "organize.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )


def display_configuration(cli_args, console: ConsoleUI) -> None:
    """
    Display the current configuration to the user.

    Args:
        cli_args: Parsed CLI arguments.
        console: Console UI instance.
    """
    mode_parts = []
    if cli_args.force_mode:
        mode_parts.append("[red]FORCE[/red]")
    if cli_args.dry_run:
        mode_parts.append("[yellow]SIMULATION[/yellow]")
    if not mode_parts:
        mode_parts.append("[green]Normal[/green]")

    mode_status = " ".join(mode_parts)

    days_display = (
        "Tous les fichiers"
        if cli_args.process_all
        else f"{cli_args.days_to_process} derniers jours"
    )

    console.print_panel(
        f"[bold]Configuration du traitement[/bold]\n"
        f"Source: [cyan]{cli_args.search_dir}[/cyan]\n"
        f"Stockage: [cyan]{cli_args.storage_dir}[/cyan]\n"
        f"Symlinks: [cyan]{cli_args.symlinks_dir}[/cyan]\n"
        f"Temporaire: [cyan]{cli_args.output_dir}[/cyan]\n"
        f"Période: {days_display}\n"
        f"Mode: {mode_status}",
        title="Organisateur de Vidéothèque",
    )


def main() -> int:
    """
    Main entry point for the video organization tool.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Parse command-line arguments
    namespace = parse_arguments()
    cli_args = args_to_cli_args(namespace)

    # Setup logging
    setup_logging(cli_args.debug)

    # Initialize console UI
    console = ConsoleUI()

    # Validate directories
    if not validate_directories(
        input_dir=cli_args.search_dir,
        output_dir=cli_args.output_dir,
        symlinks_dir=cli_args.symlinks_dir,
        storage_dir=cli_args.storage_dir,
        dry_run=cli_args.dry_run,
    ):
        console.print_error("Directory validation failed")
        return 1

    # Display simulation mode warning if active
    if cli_args.dry_run:
        console.print_warning(
            "MODE SIMULATION ACTIVÉ\n\n"
            "• Aucune modification ne sera apportée aux fichiers\n"
            "• Toutes les opérations seront simulées et loggées\n"
            "• Les fichiers originaux restent intacts"
        )

    # Display configuration
    display_configuration(cli_args, console)

    # Create execution context
    ctx = ExecutionContext(
        dry_run=cli_args.dry_run,
        force_mode=cli_args.force_mode,
        search_dir=cli_args.search_dir,
        storage_dir=cli_args.storage_dir,
        symlinks_dir=cli_args.symlinks_dir,
        output_dir=cli_args.output_dir,
        days_to_process=cli_args.days_to_process,
        debug=cli_args.debug,
        tag=cli_args.tag,
    )

    # Run the main processing pipeline within the execution context
    with execution_context(ctx):
        logger.info("Starting video organization...")

        # TODO: Phase 8 will integrate the full pipeline here
        # For now, this demonstrates the new modular entry point structure

        if cli_args.debug and cli_args.tag:
            logger.debug(f"Debug mode with tag: {cli_args.tag}")

        console.print_success("Entry point initialized successfully")
        logger.info("Video organization complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
