"""Rich utilities for CLI commands."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.columns import Columns

RICH_AVAILABLE = True

# Module-level consoles (created once, reused)
_console = Console()
_err_console = Console(stderr=True)


def get_console() -> Console | None:
    """Get Rich console instance if available."""
    return _console


def recho(message: str = "", err: bool = False, **kw) -> None:
    """Rich-aware echo — drop-in replacement for click.echo.

    Renders Rich markup ([bold], [cyan], etc.) when Rich is available.
    Falls back to plain print otherwise.

    Args:
        message: Text to print (may contain Rich markup).
        err: If True, print to stderr.
        **kw: Extra keyword args forwarded to console.print.
    """
    if RICH_AVAILABLE:
        c = _err_console if err else _console
        c.print(message, **kw)
    else:
        # Strip Rich markup for plain output
        import re

        clean = re.sub(r"\[/?[^\]]*\]", "", str(message))
        print(clean, file=sys.stderr if err else sys.stdout)


def print_rich_table(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    console: Console | None = None,
) -> None:
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


def print_rich_panel(
    content: str,
    title: str = "",
    style: str = "cyan",
    console: Console | None = None,
) -> None:
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


# ─── New Premium Helpers ─────────────────────────────────────────────

BANNER = r"""
 _____ _                     __  __ _
|  ___| | _____      ___   _|  \/  | |
| |_  | |/ _ \ \ /\ / / | | | |\/| | |
|  _| | | (_) \ V  V /| |_| | |  | | |___
|_|   |_|\___/ \_/\_/  \__, |_|  |_|_____|
                       |___/
"""


def print_banner(console: Console | None = None, subtitle: str = "") -> None:
    """Print the FlowyML ASCII art banner."""
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        console.print(f"[bold cyan]{BANNER.strip()}[/bold cyan]")
        if subtitle:
            console.print(f"[dim]{subtitle}[/dim]")
        console.print()
    else:
        print(BANNER.strip())
        if subtitle:
            print(f"  {subtitle}")
        print()


def print_kv_panel(
    title: str,
    data: dict[str, str],
    style: str = "cyan",
    console: Console | None = None,
) -> None:
    """Print a key-value panel using Rich Table inside a Panel."""
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        table = Table(
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Key", style="bold cyan", width=22)
        table.add_column("Value", style="green")

        for k, v in data.items():
            table.add_row(k, str(v))

        panel = Panel(
            table,
            title=f"[bold]{title}[/bold]",
            border_style=style,
            box=box.ROUNDED,
            expand=True,
        )
        console.print(panel)
    else:
        print(f"\n{title}")
        print("=" * 50)
        for k, v in data.items():
            print(f"  {k:<20} {v}")
        print()


def print_stats_cards(
    cards: list[tuple[str, str, str]],
    console: Console | None = None,
) -> None:
    """Print a horizontal row of stat cards.

    Args:
        cards: List of (label, value, color) tuples
        console: Optional console instance
    """
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        renderables = []
        for label, value, color in cards:
            panel = Panel(
                f"[bold {color}]{value}[/]\n[dim]{label}[/]",
                box=box.ROUNDED,
                border_style=color,
                width=18,
                height=5,
            )
            renderables.append(panel)
        console.print(Columns(renderables))
    else:
        parts = [f"  {label}: {value}" for label, value, _ in cards]
        print("\n".join(parts))
        print()


def print_db_stats(
    counts: dict[str, int],
    db_size: str = "",
    console: Console | None = None,
) -> None:
    """Print database table statistics."""
    if not console:
        console = get_console()

    if RICH_AVAILABLE and console:
        table = Table(
            title="[bold cyan]🗄  Database Statistics[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        table.add_column("Table", style="cyan", width=25)
        table.add_column("Rows", justify="right", style="green", width=10)
        table.add_column("Status", justify="center", width=8)

        total = 0
        for name, cnt in sorted(counts.items()):
            status = "🟢" if cnt > 0 else "⚪"
            table.add_row(name, str(cnt), status)
            total += cnt

        table.add_row("─" * 25, "─" * 8, "──", style="dim")
        table.add_row("[bold]TOTAL[/]", f"[bold]{total}[/]", f"📁 {db_size}")

        console.print(table)
    else:
        print("\nDatabase Statistics:")
        print("=" * 50)
        total = 0
        for name, cnt in sorted(counts.items()):
            print(f"  {name:<25} {cnt:>8} rows")
            total += cnt
        print("-" * 50)
        print(f"  {'TOTAL':<25} {total:>8} rows  ({db_size})")
        print()
