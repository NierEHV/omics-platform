"""Structured logging with Rich terminal output. Graceful stdlib fallback."""

from __future__ import annotations

import logging
import sys
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

console = Console() if _HAS_RICH else None


def setup_logging(level: str = "INFO", log_file: Optional[str] = None, rich_tracebacks: bool = True) -> logging.Logger:
    logger = logging.getLogger("omics")
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    if _HAS_RICH:
        rich_handler = RichHandler(console=console, show_time=False, show_level=True, show_path=False,
                                   rich_tracebacks=rich_tracebacks)
        rich_handler.setLevel(logging.DEBUG)
        logger.addHandler(rich_handler)
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)

    if log_file:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)

    for noisy in ["numexpr", "matplotlib", "PIL", "anndata", "h5py"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger


def status(message: str) -> None:
    if _HAS_RICH:
        console.print(f"[bold blue]▶[/bold blue] {message}")
    else:
        print(f">>> {message}")


def success(message: str) -> None:
    if _HAS_RICH:
        console.print(f"[bold green]✓[/bold green] {message}")
    else:
        print(f"[OK] {message}")


def warning(message: str) -> None:
    if _HAS_RICH:
        console.print(f"[bold yellow]⚠[/bold yellow] {message}")
    else:
        print(f"[WARN] {message}")


def error(message: str) -> None:
    if _HAS_RICH:
        console.print(f"[bold red]✗[/bold red] {message}")
    else:
        print(f"[ERROR] {message}")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    if _HAS_RICH:
        from rich.table import Table
        table = Table()
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*[str(c) for c in row])
        console.print(table)
    else:
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
        print(fmt.format(*headers))
        print("-" * (sum(col_widths) + 2 * (len(headers) - 1)))
        for row in rows:
            print(fmt.format(*[str(c) for c in row]))
