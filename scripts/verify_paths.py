#!/usr/bin/env python3
"""verify_paths.py - Thorough book path and symlink verification."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
import json
import os

console = Console()


def verify_symlink(path: Path) -> tuple[bool, str]:
    """Verify a symlink exists and points to a valid file."""
    try:
        if not path.is_symlink():
            return False, "Not a symlink"

        target = path.resolve()
        if not target.exists():
            return False, f"Broken link → {target}"

        if not os.access(target, os.R_OK):
            return False, f"No read access → {target}"

        return True, f"OK → {target}"
    except Exception as e:
        return False, f"Error: {str(e)}"


@click.command()
@click.option(
    "--books-dir",
    type=click.Path(),
    default="data/books",
    help="Directory containing books",
)
@click.option(
    "--processed-dir",
    type=click.Path(),
    default="data/processed",
    help="Directory containing processed chunks",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed link information")
@click.option("--fix", is_flag=True, help="Attempt to fix broken symlinks")
def verify(books_dir: str, processed_dir: str, verbose: bool, fix: bool):
    """Verify book paths and processed files match."""
    books_path = Path(books_dir)
    processed_path = Path(processed_dir)

    # Get all symlinks and their status
    symlinks = {}
    symlink_status = {}
    for path in books_path.glob("*.pdf"):
        symlinks[path.name] = path
        symlink_status[path.name] = verify_symlink(path)

    # Get all referenced books from processed chunks
    referenced_books = set()
    for json_file in processed_path.glob("*.json"):
        try:
            with open(json_file) as f:
                chunks = json.load(f)
                for chunk in chunks:
                    referenced_books.add(f"{chunk['book']}.pdf")
        except Exception as e:
            console.print(f"[red]Error reading {json_file}: {e}[/red]")

    # Create report table
    table = Table(title="Book Path Status")
    table.add_column("Book", style="cyan")
    table.add_column("Symlink", style="green")
    table.add_column("Referenced", style="yellow")
    if verbose:
        table.add_column("Details", style="dim")
    table.add_column("Status", style="bold")

    all_books = sorted(symlinks.keys() | referenced_books)
    broken_links = []

    for book in all_books:
        is_symlink = book in symlinks
        is_valid, link_details = symlink_status.get(book, (False, "Missing"))
        is_referenced = book in referenced_books

        symlink_status_str = "✓" if is_valid else "✗"
        referenced_str = "✓" if is_referenced else "✗"

        status = ""
        if is_valid and is_referenced:
            status = "[green]OK[/green]"
        elif is_valid:
            status = "[yellow]Unprocessed[/yellow]"
        elif is_referenced:
            status = "[red]Broken[/red]"
            broken_links.append(book)
        else:
            status = "[red]Missing[/red]"

        if verbose:
            table.add_row(
                book, symlink_status_str, referenced_str, link_details, status
            )
        else:
            table.add_row(book, symlink_status_str, referenced_str, status)

    console.print(table)

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total books: {len(all_books)}")
    console.print(f"Valid symlinks: {sum(1 for s in symlink_status.values() if s[0])}")
    console.print(f"Broken symlinks: {len(broken_links)}")
    console.print(f"Referenced in chunks: {len(referenced_books)}")

    if broken_links:
        console.print("\n[bold red]Broken Symlinks:[/bold red]")
        for book in sorted(broken_links):
            console.print(f"• {book}")
            if fix:
                path = books_path / book
                if path.is_symlink():
                    path.unlink()
                    console.print(f"  [yellow]Removed broken link[/yellow]")

    if fix and broken_links:
        console.print(
            "\n[yellow]Broken links removed. Please recreate them with correct targets.[/yellow]"
        )
        console.print("Run: ./scripts/link_books.sh")


if __name__ == "__main__":
    verify()
