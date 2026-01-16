"""Console UI wrapper using Rich library."""

import sys
from typing import List, Optional

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class ConsoleUI:
    """
    Wrapper for Rich Console providing styled output methods.

    Centralizes console output with consistent styling for
    different message types (info, warning, error, success).

    En cas d'erreur Rich, les méthodes affichent sur stderr en fallback.
    """

    def __init__(self) -> None:
        """Initialize with Rich Console."""
        self.console = Console()

    def _safe_print(self, *args, **kwargs) -> None:
        """Print avec gestion des erreurs Rich."""
        try:
            self.console.print(*args, **kwargs)
        except Exception as e:
            # Fallback vers stderr en cas d'erreur Rich
            logger.debug(f"Erreur Rich console: {e}")
            # Extraire le texte brut des arguments
            text = " ".join(str(arg) for arg in args)
            # Retirer les balises Rich
            import re
            text = re.sub(r'\[/?[^\]]+\]', '', text)
            print(text, file=sys.stderr)

    def print(self, *args, **kwargs) -> None:
        """Print to console (delegates to Rich Console)."""
        self._safe_print(*args, **kwargs)

    def rule(self, title: str = "", **kwargs) -> None:
        """Print a horizontal rule with optional title."""
        try:
            self.console.rule(title, **kwargs)
        except Exception as e:
            logger.debug(f"Erreur Rich rule: {e}")
            separator = "=" * 60
            print(f"{separator} {title} {separator}", file=sys.stderr)

    def print_info(self, message: str) -> None:
        """Print an info message with blue styling."""
        self._safe_print(f"[blue]ℹ️  {message}[/blue]")

    def print_warning(self, message: str) -> None:
        """Print a warning message with yellow styling."""
        self._safe_print(f"[yellow]⚠️  {message}[/yellow]")

    def print_error(self, message: str) -> None:
        """Print an error message with red styling."""
        self._safe_print(f"[red]❌ {message}[/red]")

    def print_success(self, message: str) -> None:
        """Print a success message with green styling."""
        self._safe_print(f"[green]✓ {message}[/green]")

    def print_simulation(self, message: str) -> None:
        """Print a simulation message with dim styling."""
        self._safe_print(f"[dim]🔍 SIMULATION - {message}[/dim]")

    def print_panel(
        self,
        content: str,
        title: str = "",
        border_style: str = "blue"
    ) -> None:
        """
        Print content in a bordered panel.

        Args:
            content: Panel content.
            title: Panel title.
            border_style: Border color/style (blue, red, green, yellow, magenta, cyan).
        """
        try:
            panel = Panel(content, title=title, border_style=border_style)
            self.console.print(panel)
        except Exception as e:
            # Fallback: afficher le contenu sans formatage
            logger.debug(f"Erreur Rich panel: {e}")
            if title:
                print(f"=== {title} ===", file=sys.stderr)
            print(content, file=sys.stderr)

    def create_table(
        self,
        title: str,
        columns: Optional[List[str]] = None
    ) -> Table:
        """
        Create a Rich Table with optional columns.

        Args:
            title: Table title.
            columns: List of column headers.

        Returns:
            Rich Table instance.
        """
        table = Table(title=title, show_header=True, header_style="bold magenta")
        if columns:
            for col in columns:
                table.add_column(col)
        return table

    def print_table(self, table: Table) -> None:
        """Print a Rich Table."""
        try:
            self.console.print(table)
        except Exception as e:
            logger.debug(f"Erreur Rich table: {e}")
            # Fallback basique pour les tables
            print(f"Table: {table.title}", file=sys.stderr)


# Global console instance for backward compatibility
console = ConsoleUI()
