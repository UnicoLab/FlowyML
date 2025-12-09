"""Rich utilities for CLI commands."""

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Table = None
    Panel = None
    Text = None
    box = None
    Tree = None


def get_console() -> Console | None:
    """Get Rich console instance if available."""
    return Console() if RICH_AVAILABLE else None


def print_rich_table(title: str, headers: list[str], rows: list[list[str]], console: Console | None = None) -> None:
    """Print a rich table with fallback to simple output."""
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        table = Table(
            title=f"[bold cyan]{title}[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        for header in headers:
            table.add_column(header, style="cyan")
        for row in rows:
            table.add_row(*row)
        console.print(table)
    else:
        # Fallback to simple output
        print(f"\n{title}")
        print("=" * 70)
        print(" | ".join(headers))
        print("-" * 70)
        for row in rows:
            print(" | ".join(str(cell) for cell in row))
        print()


def print_rich_panel(content: str, title: str = "", style: str = "cyan", console: Console | None = None) -> None:
    """Print a rich panel with fallback to simple output."""
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        panel = Panel(
            content,
            title=title,
            border_style=style,
            box=box.ROUNDED,
        )
        console.print(panel)
    else:
        # Fallback to simple output
        if title:
            print(f"\n{title}")
            print("=" * 70)
        print(content)
        print()


def print_rich_text(*parts: tuple[str, str], console: Console | None = None) -> None:
    """Print rich text with styles, fallback to simple output.

    Args:
        *parts: Tuples of (text, style) to print
        console: Optional console instance
    """
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console and Text:
        text_obj = Text()
        for text, style in parts:
            text_obj.append(text, style=style)
        console.print(text_obj)
    else:
        # Fallback to simple output
        print("".join(text for text, _ in parts))
