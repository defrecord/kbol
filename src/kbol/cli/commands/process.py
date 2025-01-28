# src/kbol/cli/commands/process.py

import typer
from rich.console import Console
from pathlib import Path
import asyncio

from ...indexer import BookIndexer

console = Console()


async def process_impl(
    books_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
    model: str,
    force: bool = False,
):
    """Implementation of process command."""
    indexer = BookIndexer(
        embed_model=model, 
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )

    try:
        # Pass force flag to the indexer
        results = await indexer.process_books(books_dir, force=force)
        console.print(
            f"[green]Processed {len(results)} chunks from "
            f"{len(set(c['book'] for c in results))} books[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error processing books: {str(e)}[/red]")
        raise typer.Exit(1)


def register(app: typer.Typer):
    """Register process command with the CLI app."""

    @app.command()
    def process(
        books_dir: Path = typer.Argument(
            "data/books",
            help="Directory containing PDF books",
        ),
        chunk_size: int = typer.Option(
            512, "--chunk-size", help="Target chunk size in tokens"
        ),
        chunk_overlap: int = typer.Option(
            50, "--overlap", help="Overlap between chunks in tokens"
        ),
        model: str = typer.Option(
            "nomic-embed-text", "--model", help="Embedding model to use"
        ),
        force: bool = typer.Option(
            False, 
            "--force", 
            "-f", 
            help="Force reprocessing of already processed books"
        ),
    ):
        """Process PDFs into chunks with embeddings.

        Examples:
            kbol process
            kbol process --chunk-size 256 --overlap 25
            kbol process --model nomic-embed-text data/books
            kbol process --force  # Reprocess all books
            kbol process --force --chunk-size 256  # Reprocess with different settings
        """
        try:
            # Make sure the output directory exists
            Path("data/processed").mkdir(parents=True, exist_ok=True)
            
            asyncio.run(
                process_impl(
                    books_dir=books_dir,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    model=model,
                    force=force,
                )
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Processing interrupted by user[/yellow]")
            raise typer.Exit(130)
        except Exception as e:
            console.print(f"[red]Fatal error: {str(e)}[/red]")
            raise typer.Exit(1)
