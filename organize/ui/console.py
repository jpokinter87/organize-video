"""Console UI wrapper using Rich library."""

from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class ConsoleUI:
    """
    Wrapper for Rich Console providing styled output methods.

    Centralizes console output with consistent styling for
    different message types (info, warning, error, success).
    """

    def __init__(self) -> None:
        """Initialize with Rich Console."""
        self.console = Console()

    def print(self, *args, **kwargs) -> None:
        """Print to console (delegates to Rich Console)."""
        self.console.print(*args, **kwargs)

    def rule(self, title: str = "", **kwargs) -> None:
        """Print a horizontal rule with optional title."""
        self.console.rule(title, **kwargs)

    def print_info(self, message: str) -> None:
        """Print an info message with blue styling."""
        self.console.print(f"[blue]ℹ️  {message}[/blue]")

    def print_warning(self, message: str) -> None:
        """Print a warning message with yellow styling."""
        self.console.print(f"[yellow]⚠️  {message}[/yellow]")

    def print_error(self, message: str) -> None:
        """Print an error message with red styling."""
        self.console.print(f"[red]❌ {message}[/red]")

    def print_success(self, message: str) -> None:
        """Print a success message with green styling."""
        self.console.print(f"[green]✓ {message}[/green]")

    def print_simulation(self, message: str) -> None:
        """Print a simulation message with dim styling."""
        self.console.print(f"[dim]🔍 SIMULATION - {message}[/dim]")

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
            border_style: Border color/style.
        """
        panel = Panel(content, title=title, border_style=border_style)
        self.console.print(panel)

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
        self.console.print(table)


# Global console instance for backward compatibility
console = ConsoleUI()
