from pathlib import Path
import json
import typer
from rich.console import Console
from rich.table import Table

console = Console()

def register(app: typer.Typer):
    """Register stats command with the CLI app."""

    @app.command()
    def stats():
        """Show statistics about processed books."""
        processed_dir = Path("data/processed")

        # Create directory if it doesn't exist
        processed_dir.mkdir(parents=True, exist_ok=True)

        json_files = list(processed_dir.glob("*.json"))
        if not json_files:
            console.print(
                "[yellow]No processed files found in data/processed/.[/yellow]\n"
                "This could mean either:\n"
                "1. No books have been processed yet\n"
                "2. All books were skipped (already processed)\n"
                "3. The output directory is not in the expected location\n\n"
                "Try running 'kbol process' with some new PDFs."
            )
            return

        table = Table(
            title="Processed Books Statistics",
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Book")
        table.add_column("Chunks", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Avg Chunk Size", justify="right")

        total_chunks = 0
        total_tokens = 0

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    chunks = json.load(f)
                    if not chunks:  # Skip empty files
                        continue
                        
                    chunk_count = len(chunks)
                    token_count = sum(c["token_count"] for c in chunks)
                    avg_chunk = token_count // (chunk_count or 1)

                    table.add_row(
                        json_file.stem,
                        str(chunk_count),
                        f"{token_count:,}",
                        str(avg_chunk),
                    )

                    total_chunks += chunk_count
                    total_tokens += token_count
            except Exception as e:
                console.print(f"[red]Error reading {json_file.name}: {e}[/red]")

        if total_chunks > 0:
            table.add_section()
            table.add_row(
                "TOTAL",
                str(total_chunks),
                f"{total_tokens:,}",
                str(total_tokens // (total_chunks or 1)),
                style="bold",
            )
            console.print(table)
        else:
            console.print("[yellow]No chunk data found in processed files.[/yellow]")

