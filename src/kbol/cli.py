import typer
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, SpinnerColumn, Task
import json
from typing import Optional

from .indexer import BookIndexer

app = typer.Typer(
    name="kbol",
    help="Knowledge Base for OLlama - Process and query technical books"
)
console = Console()

@app.command()
def process(
    books_dir: Path = typer.Argument(
        "data/books",
        help="Directory containing PDF books",
    ),
    chunk_size: int = typer.Option(
        512,
        "--chunk-size",
        help="Target chunk size in tokens"
    ),
    chunk_overlap: int = typer.Option(
        50,
        "--overlap",
        help="Overlap between chunks in tokens"
    ),
    model: str = typer.Option(
        "nomic-embed-text",
        "--model",
        help="Embedding model to use"
    )
):
    """Process PDFs into chunks with embeddings."""
    indexer = BookIndexer(
        embed_model=model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        progress_callback=lambda msg: console.print(f"[cyan]{msg}[/cyan]")
    )
    
    try:
        results = asyncio.run(indexer.process_books(books_dir))
        console.print(f"[green]Processed {len(results)} chunks from {len(set(c['book'] for c in results))} books[/green]")
    except Exception as e:
        console.print(f"[red]Error processing books: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def stats():
    """Show statistics about processed books."""
    processed_dir = Path("data/processed")
    
    if not processed_dir.exists() or not list(processed_dir.glob("*.json")):
        console.print("[yellow]No processed books found. Run 'kbol process' first.[/yellow]")
        return

    table = Table(
        title="Processed Books Statistics",
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Book")
    table.add_column("Chunks", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Avg Chunk Size", justify="right")
    
    total_chunks = 0
    total_tokens = 0
    
    for json_file in processed_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                chunks = json.load(f)
                chunk_count = len(chunks)
                token_count = sum(c["token_count"] for c in chunks)
                avg_chunk = token_count // chunk_count if chunk_count else 0
                
                table.add_row(
                    json_file.stem,
                    str(chunk_count),
                    f"{token_count:,}",
                    str(avg_chunk)
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
            str(total_tokens // total_chunks if total_chunks else 0),
            style="bold"
        )
    
    console.print(table)
