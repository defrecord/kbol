import typer
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
import json
from typing import Optional, List, Dict
import numpy as np
import httpx

from .indexer import BookIndexer

app = typer.Typer(
    name="kbol",
    help="Knowledge Base for OLlama - Process and query technical books",
    no_args_is_help=True,
)
console = Console()


async def get_embedding(text: str, url: str = "http://localhost:11434") -> List[float]:
    """Get embedding for query text."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{url}/api/embeddings", json={"model": "nomic-embed-text", "prompt": text}
        )
        return response.json()["embedding"]


async def get_completion(
    prompt: str, context: str, url: str = "http://localhost:11434"
) -> str:
    """Get completion from Ollama."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{url}/api/generate",
            json={
                "model": "phi3",
                "prompt": f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:",
                "stream": False,
            },
        )
        return response.json()["response"]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


async def search_chunks(query: str, top_k: int = 5) -> List[Dict]:
    """Search for relevant chunks."""
    query_embedding = await get_embedding(query)
    all_chunks = []

    # Load all processed chunks
    for json_file in Path("data/processed").glob("*.json"):
        with open(json_file) as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)

    # Calculate similarities
    for chunk in all_chunks:
        chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])

    # Sort by similarity
    return sorted(all_chunks, key=lambda x: x["similarity"], reverse=True)[:top_k]


# ... (rest of the file remains the same, but process command should also be updated)


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
):
    """Process PDFs into chunks with embeddings."""
    indexer = BookIndexer(
        embed_model=model, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    async def process_impl():
        try:
            results = await indexer.process_books(books_dir)
            console.print(
                f"[green]Processed {len(results)} chunks from {len(set(c['book'] for c in results))} books[/green]"
            )
        except Exception as e:
            console.print(f"[red]Error processing books: {e}[/red]")
            raise typer.Exit(1)

    run_async(process_impl())


@app.command()
def stats():
    """Show statistics about processed books."""
    processed_dir = Path("data/processed")

    if not processed_dir.exists() or not list(processed_dir.glob("*.json")):
        console.print(
            "[yellow]No processed books found. Run 'kbol process' first.[/yellow]"
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

    for json_file in processed_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                chunks = json.load(f)
                chunk_count = len(chunks)
                token_count = sum(c["token_count"] for c in chunks)
                avg_chunk = token_count // chunk_count if chunk_count else 0

                table.add_row(
                    json_file.stem, str(chunk_count), f"{token_count:,}", str(avg_chunk)
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
            style="bold",
        )

    console.print(table)


def run_async(coro):
    """Helper to run async functions in the CLI."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask"),
    top_k: int = typer.Option(5, "--top-k", help="Number of chunks to retrieve"),
    show_context: bool = typer.Option(
        False, "--show-context", help="Show retrieved chunks"
    ),
    book_filter: Optional[str] = typer.Option(
        None, "--book", help="Filter to specific book"
    ),
    model: str = typer.Option(
        "phi3", "--model", "-m", help="Ollama model to use for response"
    ),
):
    """Query the knowledge base."""

    async def query_impl():
        try:
            with console.status("[cyan]Searching knowledge base...[/cyan]"):
                # Get relevant chunks
                chunks = await search_chunks(question, top_k)
                if not chunks:
                    console.print("[yellow]No relevant content found.[/yellow]")
                    return

                # Filter by book if specified
                if book_filter:
                    chunks = [
                        c for c in chunks if book_filter.lower() in c["book"].lower()
                    ]
                    if not chunks:
                        console.print(
                            f"[yellow]No results found in book matching '{book_filter}'[/yellow]"
                        )
                        return

                # Sort chunks by book and page for readability
                chunks.sort(key=lambda x: (x["book"], x.get("page", 0)))

                # Build context from chunks
                context_parts = []
                console.print("\n[cyan]Found relevant content in:[/cyan]")
                current_book = None
                for chunk in chunks:
                    if chunk["book"] != current_book:
                        current_book = chunk["book"]
                        console.print(f"• {current_book}")

                    similarity = chunk["similarity"] * 100
                    context_parts.append(
                        f"From {chunk['book']}, page {chunk['page']} (relevance: {similarity:.1f}%):\n{chunk['content']}"
                    )
                context = "\n\n".join(context_parts)

                if show_context:
                    console.print("\n[cyan]Retrieved Context:[/cyan]")
                    console.print(Panel(context, title="Context", border_style="blue"))

                # Get answer from Ollama
                console.print("\n[cyan]Generating response...[/cyan]")
                answer = await get_completion(question, context)
                console.print(
                    Panel(Markdown(answer), title="Answer", border_style="green")
                )

        except Exception as e:
            console.print(f"[red]Error during query: {e}[/red]")
            raise typer.Exit(1)

    run_async(query_impl())


@app.command()
def list_books():
    """List all processed books."""
    processed_dir = Path("data/processed")
    books = set()

    for json_file in processed_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                chunks = json.load(f)
                books.update(chunk["book"] for chunk in chunks)
        except Exception as e:
            console.print(f"[red]Error reading {json_file.name}: {e}[/red]")

    if books:
        console.print("[cyan]Available books:[/cyan]")
        for book in sorted(books):
            console.print(f"• {book}")
    else:
        console.print("[yellow]No processed books found.[/yellow]")


@app.command()
def validate():
    """Validate processed chunks and report issues."""
    processed_dir = Path("data/processed")
    issues = []

    for json_file in processed_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                chunks = json.load(f)

            for i, chunk in enumerate(chunks, 1):
                # Check required fields
                for field in ["book", "page", "content", "embedding"]:
                    if field not in chunk:
                        issues.append(f"{json_file.name}:chunk{i} missing {field}")

                # Check embedding dimension
                if "embedding" in chunk and len(chunk["embedding"]) != 384:
                    issues.append(
                        f"{json_file.name}:chunk{i} has wrong embedding dimension"
                    )

                # Check content
                if "content" in chunk and not chunk["content"].strip():
                    issues.append(f"{json_file.name}:chunk{i} has empty content")

        except Exception as e:
            issues.append(f"{json_file.name}: {str(e)}")

    if issues:
        console.print("[red]Found issues:[/red]")
        for issue in issues:
            console.print(f"• {issue}")
    else:
        console.print("[green]All chunks validated successfully[/green]")


if __name__ == "__main__":
    app()
