# KBOL - Knowledge Base for OLlama

## Project Structure

### scripts/fetch_manuals.py

```python
#!/usr/bin/env python3
"""fetch_manuals.py - Download and verify technical manuals for KBOL."""

import click
import httpx
import sys
from pathlib import Path
from typing import Dict, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import shutil

MANUALS = {
    # GNU Manuals (original)
    "emacs_manual.pdf": "https://www.gnu.org/software/emacs/manual/pdf/emacs.pdf",
    "elisp_manual.pdf": "https://www.gnu.org/software/emacs/manual/pdf/elisp.pdf",
    "org-mode_manual.pdf": "https://orgmode.org/org.pdf",
    "guile_manual.pdf": "https://www.gnu.org/software/guile/manual/guile.pdf",
    "make_manual.pdf": "https://www.gnu.org/software/make/manual/make.pdf",
    # Logic & Philosophy of Mathematics
    "frege_foundations.pdf": "https://archive.org/download/basisarithmetic00freg/basisarithmetic00freg.pdf",  # Basic Laws of Arithmetic
    "russell_principia.pdf": "https://archive.org/download/principiamathemat01whituoft/principiamathemat01whituoft.pdf",
    "wittgenstein_tractatus.pdf": "https://people.umass.edu/klement/tlp/tlp.pdf",
    "godel_completeness.pdf": "https://archive.org/download/GodelOnFormallyUndecidablePropositionsOfPrincipiaMathematicaAndRelatedSystems/Godel-OnFormallyUndecidablePropositionsOfPrincipiaMathematicaAndRelatedSystems.pdf",
    "church_calculus.pdf": "https://archive.org/download/TheCalculiOfLambdaConversionChurchA/The_Calculi_of_Lambda-Conversion_Church_A.pdf",
    "turing_computing.pdf": "https://archive.org/download/B-001-001-251/B-001-001-251.pdf",  # On Computable Numbers
    # Philosophy of Science
    "einstein_relativity.pdf": "https://www.gutenberg.org/files/5001/5001-pdf.pdf",  # Relativity: Special and General Theory
    "popper_logic.pdf": "https://archive.org/download/PopperLogicOfScientificDiscovery/Popper-Logic_of_scientific_discovery.pdf",
    "kuhn_structure.pdf": "https://archive.org/download/structure-of-scientific-revolutions-2nd-edition/structure-of-scientific-revolutions-2nd-edition.pdf",
    # Early Modern Philosophy
    "plato_republic.pdf": "https://www.gutenberg.org/files/1497/1497-pdf.pdf",
    "aristotle_ethics.pdf": "https://www.gutenberg.org/files/8438/8438-pdf.pdf",
    "meditations_aurelius.pdf": "https://www.gutenberg.org/files/2680/2680-pdf.pdf",
    "kant_critique_pure_reason.pdf": "https://www.gutenberg.org/files/4280/4280-pdf.pdf",
    "hume_enquiry.pdf": "https://www.gutenberg.org/files/9662/9662-pdf.pdf",
    # Contemporary Foundational Works
    "quine_two_dogmas.pdf": "https://archive.org/download/QuineTwoDogmasOfEmpiricism/Quine-TwoDogmasOfEmpiricism.pdf",
    "kripke_naming.pdf": "https://archive.org/download/NamingAndNecessity/Kripke%20-%20Naming%20and%20Necessity.pdf",
    "putnam_reason.pdf": "https://archive.org/download/PutnamReasonTruthAndHistory/Putnam%20-%20Reason%2C%20Truth%20and%20History.pdf",
    "davidson_essays.pdf": "https://archive.org/download/DavidsonEssaysOnActionsAndEvents/Davidson%20-%20Essays%20on%20Actions%20and%20Events.pdf",
    # Contemporary Philosophy
    "arendt_human_condition.pdf": "https://archive.org/download/ArendtHannahTheHumanCondition2nd1998/Arendt_Hannah_The_Human_Condition_2nd_1998.pdf",
    "foucault_discipline_punish.pdf": "https://archive.org/download/michel-foucault-discipline-and-punish/michel-foucault-discipline-and-punish.pdf",
    "rawls_theory_justice.pdf": "https://archive.org/download/TheoryOfJustice/john%20rawls%20-%20a%20theory%20of%20justice.pdf",
    # Literature (foundational)
    "dante_inferno.pdf": "https://www.gutenberg.org/files/1001/1001-pdf.pdf",
    "odyssey_homer.pdf": "https://www.gutenberg.org/files/3160/3160-pdf.pdf",
    "shakespeare_hamlet.pdf": "https://www.gutenberg.org/files/1524/1524-pdf.pdf",
}

console = Console()


class ManualDownloader:
    def __init__(self, manuals_dir: Path, books_dir: Path, timeout: int = 300):
        self.manuals_dir = manuals_dir
        self.books_dir = books_dir
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            },
        )

    def is_valid_pdf(self, file_path: Path) -> bool:
        """Check if file is a valid PDF."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                return header.startswith(b"%PDF")
        except Exception as e:
            console.print(f"[red]Error checking PDF {file_path}: {e}")
            return False

    def download_manual(self, filename: str, url: str) -> Optional[Path]:
        """Download a single manual."""
        target_path = self.manuals_dir / filename

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Downloading {filename}...", total=None)

                response = self.client.get(url)
                response.raise_for_status()

                target_path.write_bytes(response.content)

                if not self.is_valid_pdf(target_path):
                    target_path.unlink(missing_ok=True)
                    progress.update(task, description=f"[red]Invalid PDF: {filename}")
                    return None

                progress.update(task, description=f"[green]Downloaded {filename}")
                return target_path

        except Exception as e:
            console.print(f"[red]Error downloading {filename}: {e}")
            target_path.unlink(missing_ok=True)
            return None

    def create_symlink(self, source: Path, target: Path) -> bool:
        """Create symlink from source to target."""
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(source.resolve())
            return True
        except Exception as e:
            console.print(f"[red]Error creating symlink for {source.name}: {e}")
            return False

    def process_manuals(self) -> tuple[int, int, int]:
        """Process all manuals and return (success, skipped, failed) counts."""
        success = skipped = failed = 0

        for filename, url in sorted(MANUALS.items()):
            manual_path = self.manuals_dir / filename
            target_path = self.books_dir / filename

            if manual_path.exists() and self.is_valid_pdf(manual_path):
                console.print(f"[yellow]Already have valid PDF: {filename}")
                skipped += 1
                if self.create_symlink(manual_path, target_path):
                    success += 1
                else:
                    failed += 1
                continue

            if manual_path.exists():
                console.print(
                    f"[yellow]Existing PDF invalid, redownloading: {filename}"
                )
                manual_path.unlink()

            if self.download_manual(filename, url):
                if self.create_symlink(manual_path, target_path):
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1

        return success, skipped, failed


@click.command()
@click.option(
    "--manuals-dir",
    type=click.Path(),
    default="data/manuals",
    help="Directory to store downloaded manuals",
)
@click.option(
    "--books-dir",
    type=click.Path(),
    default="data/books",
    help="Directory to create symlinks",
)
@click.option("--timeout", type=int, default=300, help="Download timeout in seconds")
@click.option("--force", is_flag=True, help="Force redownload of all manuals")
def main(manuals_dir: str, books_dir: str, timeout: int, force: bool):
    """Download and verify technical manuals for KBOL."""
    manuals_path = Path(manuals_dir)
    books_path = Path(books_dir)

    # Ensure directories exist
    manuals_path.mkdir(parents=True, exist_ok=True)
    books_path.mkdir(parents=True, exist_ok=True)

    if force:
        console.print("[yellow]Force mode: removing existing manuals")
        for file in manuals_path.glob("*.pdf"):
            file.unlink()

    downloader = ManualDownloader(manuals_path, books_path, timeout)
    success, skipped, failed = downloader.process_manuals()

    # Print summary
    console.print("\n[bold]Summary[/bold]")
    console.print(f"Successfully processed: [green]{success}[/green]")
    console.print(f"Skipped (already valid): [yellow]{skipped}[/yellow]")
    console.print(f"Failed: [red]{failed}[/red]")

    if failed == 0:
        console.print("\n[green]All manuals processed successfully")
        console.print("Run 'poetry run python -m kbol process' to index them")
        sys.exit(0)
    else:
        console.print("\n[red]Some manuals failed to process")
        sys.exit(1)


if __name__ == "__main__":
    main()

```

### scripts/verify_paths.py

```python
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

```

### src/kbol/__init__.py

```python
"""Knowledge base from technical books using Ollama."""

__version__ = "0.1.0"

```

### src/kbol/__main__.py

```python
from .cli.app import init_app

app = init_app()

if __name__ == "__main__":
    app()

```

### src/kbol/cli/__init__.py

```python
from .app import init_app

__all__ = ["init_app"]

```

### src/kbol/cli/app.py

```python
# src/kbol/cli/app.py

import typer
from rich.console import Console

app = typer.Typer(
    name="kbol",
    help="Knowledge Base for OLlama - Process and query technical books",
    no_args_is_help=True,
)
console = Console()

def init_app():
    """Initialize CLI application."""
    # Import commands here to avoid circular imports
    from .commands import process, query, stats, list, validate, topics, prompt, convert

    # Register commands
    process.register(app)
    query.register(app)
    stats.register(app)
    list.register(app)
    validate.register(app)
    topics.register(app)
    prompt.register(app)
    convert.register(app)

    return app

# For direct use
app = init_app()

```

### src/kbol/cli/cli_old.py

```python
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
        try:
            response = await client.post(
                f"{url}/api/generate",
                json={
                    "model": "phi3",
                    "prompt": f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:",
                    "stream": False,
                },
                timeout=60.0,  # Add timeout
            )
            response.raise_for_status()  # Raise for bad HTTP status
            data = response.json()
            if "error" in data:
                raise Exception(f"Ollama error: {data['error']}")
            return data["response"]
        except httpx.TimeoutError:
            raise Exception("Ollama request timed out after 60 seconds")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise Exception(f"Error getting completion: {str(e)}")


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
    temperature: float = typer.Option(
        0.7, "--temperature", "-t", help="Model temperature (0.0-1.0)", min=0.0, max=1.0
    ),
):
    """Query the knowledge base.

    Examples:
        kbol query "Explain monads in Clojure"
        kbol query --book "Python" --show-context "How to handle exceptions?"
        kbol query --model llama2 "Compare Python and Clojure immutability"
    """

    async def query_impl():
        try:
            with console.status("[cyan]Searching knowledge base...[/cyan]") as status:
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
                        f"From {chunk['book']}, page {chunk['page']} "
                        f"(relevance: {similarity:.1f}%):\n{chunk['content']}"
                    )
                context = "\n\n".join(context_parts)

                if show_context:
                    console.print("\n[cyan]Retrieved Context:[/cyan]")
                    console.print(Panel(context, title="Context", border_style="blue"))

                # Get answer from Ollama
                status.update("[cyan]Generating response...[/cyan]")
                try:
                    answer = await get_completion(
                        question, context, model=model, temperature=temperature
                    )
                    console.print(
                        Panel(Markdown(answer), title="Answer", border_style="green")
                    )
                except Exception as e:
                    console.print(f"[red]Error generating response: {str(e)}[/red]")
                    if show_context:
                        console.print("\n[yellow]Retrieved context was:[/yellow]")
                        console.print(
                            Panel(context, title="Context", border_style="yellow")
                        )
                    console.print(
                        "\n[yellow]Try adjusting the model parameters or checking "
                        "Ollama status[/yellow]"
                    )
                    return

        except Exception as e:
            console.print(f"[red]Error during query: {str(e)}[/red]")
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

```

### src/kbol/cli/commands/__init__.py

```python

```

### src/kbol/cli/commands/convert.py

```python
# src/kbol/cli/commands/convert.py

import typer
from rich.console import Console
from pathlib import Path
import subprocess
import tempfile
import shutil

console = Console()

def register(app: typer.Typer):
    """Register convert command with the CLI app."""

    @app.command()
    def convert(
        input_file: Path = typer.Argument(..., help="Input markdown file to convert"),
        target: str = typer.Option(
            "org", "--to", "-t", help="Target format (org, rst, etc.)"
        ),
        output_file: Path = typer.Option(
            None, "--output", "-o", help="Output file (default: auto-generated)"
        ),
    ):
        """Convert documentation between formats using pandoc.
        
        Examples:
            kbol convert README.md -t org
            kbol convert docs.md -t rst -o output.rst
        """
        try:
            # Check if pandoc is installed
            if not shutil.which("pandoc"):
                console.print(
                    "[red]Error: pandoc is not installed. Please install it first:[/red]\n"
                    "  brew install pandoc  # on macOS\n"
                    "  apt install pandoc   # on Ubuntu/Debian"
                )
                raise typer.Exit(1)

            # Generate output filename if not provided
            if output_file is None:
                output_file = input_file.with_suffix(f".{target}")

            # Convert using pandoc
            cmd = [
                "pandoc",
                "-f", "markdown",
                "-t", target,
                str(input_file),
                "-o", str(output_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                console.print(f"[red]Conversion failed:[/red]\n{result.stderr}")
                raise typer.Exit(1)

            console.print(f"[green]Successfully converted to {output_file}[/green]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Pandoc error: {e.stderr}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error during conversion: {str(e)}[/red]")
            raise typer.Exit(1)

```

### src/kbol/cli/commands/list.py

```python
import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer):
    """Register list command with the CLI app."""
    # TODO: Implement list command
    pass

```

### src/kbol/cli/commands/process.py

```python
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
):
    """Implementation of process command."""
    indexer = BookIndexer(
        embed_model=model, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    try:
        results = await indexer.process_books(books_dir)
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
    ):
        """Process PDFs into chunks with embeddings.

        Examples:
            kbol process
            kbol process --chunk-size 256 --overlap 25
            kbol process --model nomic-embed-text data/books
        """
        asyncio.run(
            process_impl(
                books_dir=books_dir,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                model=model,
            )
        )

```

### src/kbol/cli/commands/prompt.py

```python
# src/kbol/cli/commands/prompt.py

import typer
from rich.console import Console
from pathlib import Path
import json

console = Console()

def register(app: typer.Typer):
    """Register prompt command with the CLI app."""

    @app.command()
    def prompt(
        source_dir: Path = typer.Argument(
            ".", help="Source directory to analyze"
        ),
        output: Path = typer.Option(
            "README.md", "--output", "-o", help="Output markdown file"
        ),
    ):
        """Generate documentation from source code.
        
        Examples:
            kbol prompt .
            kbol prompt . -o custom.md
            kbol prompt src/kbol
        """
        try:
            # Create documentation string
            docs = []
            
            # Add header
            docs.append("# KBOL - Knowledge Base for OLlama\n")
            docs.append("## Project Structure\n")
            
            # Analyze directory structure
            for path in sorted(source_dir.rglob("*.py")):
                if "__pycache__" in str(path):
                    continue
                    
                rel_path = path.relative_to(source_dir)
                docs.append(f"### {rel_path}\n")
                
                # Add file content
                docs.append("```python")
                docs.append(path.read_text())
                docs.append("```\n")
            
            # Write output
            output_text = "\n".join(docs)
            output.write_text(output_text)
            console.print(f"[green]Documentation written to {output}[/green]")
            
        except Exception as e:
            console.print(f"[red]Error generating documentation: {str(e)}[/red]")
            raise typer.Exit(1)

```

### src/kbol/cli/commands/query.py

```python
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import Optional
import asyncio
from datetime import datetime

from ...core.search import search_chunks
from ...core.llm import get_completion

console = Console()


async def query_impl(
    question: str,
    top_k: int,
    show_context: bool,
    book_filter: Optional[str],
    model: str,
    temperature: float,
):
    """Implementation of query command."""
    try:
        with console.status("[cyan]Searching knowledge base...[/cyan]") as status:
            chunks = await search_chunks(question, top_k)
            if not chunks:
                console.print("[yellow]No relevant content found.[/yellow]")
                return

            if book_filter:
                chunks = [c for c in chunks if book_filter.lower() in c["book"].lower()]
                if not chunks:
                    console.print(
                        f"[yellow]No results found in book matching '{book_filter}'[/yellow]"
                    )
                    return

            chunks.sort(key=lambda x: (x["book"], x.get("page", 0)))
            context_parts = []
            console.print("\n[cyan]Found relevant content in:[/cyan]")
            current_book = None

            for chunk in chunks:
                if chunk["book"] != current_book:
                    current_book = chunk["book"]
                    console.print(f"• {current_book}")

                similarity = chunk["similarity"] * 100
                context_parts.append(
                    f"From {chunk['book']}, page {chunk['page']} "
                    f"(relevance: {similarity:.1f}%):\n{chunk['content']}"
                )

            context = "\n\n".join(context_parts)

            if show_context:
                console.print("\n[cyan]Retrieved Context:[/cyan]")
                console.print(Panel(context, title="Context", border_style="blue"))

            status.update("[cyan]Generating response...[/cyan]")
            try:
                answer = await get_completion(
                    question,
                    context,
                    model=model,
                    temperature=temperature,
                )

                console.print(
                    Panel(Markdown(answer), title="Answer", border_style="green")
                )

                timestamp = datetime.now().strftime("%Y%m%d:%H%M%S")
                filename = f"data/answers/{timestamp}.md"
                with open(filename, "w") as f:
                    f.write(answer)
                console.print(filename)

            except Exception as e:
                console.print(f"[red]Error generating response: {str(e)}[/red]")
                if show_context:
                    console.print("\n[yellow]Retrieved context was:[/yellow]")
                    console.print(
                        Panel(context, title="Context", border_style="yellow")
                    )
                console.print(
                    "\n[yellow]Try adjusting the model parameters or checking "
                    "Ollama status[/yellow]"
                )
                return

    except Exception as e:
        console.print(f"[red]Error during query: {str(e)}[/red]")
        raise typer.Exit(1)


def register(app: typer.Typer):
    """Register query command with the CLI app."""

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
        temperature: float = typer.Option(
            0.7,
            "--temperature",
            "-t",
            help="Model temperature (0.0-1.0)",
            min=0.0,
            max=1.0,
        ),
    ):
        """Query the knowledge base."""
        asyncio.run(
            query_impl(
                question=question,
                top_k=top_k,
                show_context=show_context,
                book_filter=book_filter,
                model=model,
                temperature=temperature,
            )
        )

```

### src/kbol/cli/commands/stats.py

```python
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


```

### src/kbol/cli/commands/topics.py

```python
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import json
import numpy as np
from collections import Counter
from typing import List, Dict
import re
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

console = Console()


@dataclass
class TopicSummary:
    name: str
    documents: List[str]
    key_terms: List[str]
    chunk_count: int
    total_tokens: int


def analyze_topics(chunks: List[Dict], n_clusters: int = 10) -> List[TopicSummary]:
    """Analyze topics in the chunks using TF-IDF and clustering."""
    # Extract text content
    texts = [chunk["content"] for chunk in chunks]

    # Create TF-IDF matrix
    vectorizer = TfidfVectorizer(
        max_features=1000, stop_words="english", ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Cluster documents
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(tfidf_matrix)

    # Get feature names
    feature_names = vectorizer.get_feature_names_out()

    # Analyze each cluster
    topics = []
    for i in range(n_clusters):
        cluster_docs = [doc for doc, cluster in zip(chunks, clusters) if cluster == i]
        if not cluster_docs:
            continue

        # Get top terms for cluster
        cluster_center = kmeans.cluster_centers_[i]
        top_term_indices = np.argsort(cluster_center)[-5:][::-1]
        key_terms = [feature_names[idx] for idx in top_term_indices]

        # Get unique documents in cluster
        unique_docs = set(doc["book"] for doc in cluster_docs)

        topics.append(
            TopicSummary(
                name=f"Topic {i+1}: {key_terms[0]}",
                documents=sorted(unique_docs),
                key_terms=key_terms,
                chunk_count=len(cluster_docs),
                total_tokens=sum(doc["token_count"] for doc in cluster_docs),
            )
        )

    return topics


def register(app: typer.Typer):
    @app.command()
    def topics(
        n_clusters: int = typer.Option(
            10, "--clusters", "-n", help="Number of topics to identify"
        ),
        min_chunks: int = typer.Option(
            5, "--min-chunks", help="Minimum chunks per topic to display"
        ),
    ):
        """Analyze topics and clusters in the knowledge base."""
        processed_dir = Path("data/processed")

        if not processed_dir.exists() or not list(processed_dir.glob("*.json")):
            console.print(
                "[yellow]No processed books found. Run 'kbol process' first.[/yellow]"
            )
            return

        # Load all chunks
        all_chunks = []
        for json_file in processed_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
            except Exception as e:
                console.print(f"[red]Error reading {json_file.name}: {e}[/red]")

        if not all_chunks:
            console.print("[yellow]No chunks found in processed files.[/yellow]")
            return

        # Analyze topics
        topics = analyze_topics(all_chunks, n_clusters)

        # Filter and sort topics
        topics = [t for t in topics if t.chunk_count >= min_chunks]
        topics.sort(key=lambda x: x.chunk_count, reverse=True)

        # Display results
        console.print(f"\n[bold cyan]Found {len(topics)} major topics:[/bold cyan]\n")

        for topic in topics:
            console.print(
                Panel(
                    f"[bold]{topic.name}[/bold]\n\n"
                    f"Key terms: {', '.join(topic.key_terms)}\n\n"
                    f"Documents ({len(topic.documents)}):\n"
                    + "\n".join(f"• {doc}" for doc in topic.documents)
                    + f"\n\nChunks: {topic.chunk_count:,} | Tokens: {topic.total_tokens:,}",
                    border_style="blue",
                )
            )

        # Print co-occurrence matrix
        table = Table(title="Topic Co-occurrence")
        table.add_column("Topic", style="cyan")
        for t in topics[:5]:  # Show top 5 topics
            table.add_column(t.name.split(":")[0], justify="right")

        for t1 in topics[:5]:
            row = [t1.name.split(":")[0]]
            for t2 in topics[:5]:
                common_docs = len(set(t1.documents) & set(t2.documents))
                row.append(str(common_docs))
            table.add_row(*row)

        console.print("\n", table)


if __name__ == "__main__":
    app = typer.Typer()
    register(app)
    app()

```

### src/kbol/cli/commands/validate.py

```python
import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer):
    """Register validate command with the CLI app."""
    # TODO: Implement validate command
    pass

```

### src/kbol/cli/utils.py

```python
import asyncio
import typer
from rich.console import Console

console = Console()


def run_async(coro):
    """Helper to run async functions in the CLI."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

```

### src/kbol/core/__init__.py

```python
from .embedding import get_embedding, cosine_similarity
from .search import search_chunks
from .llm import get_completion

__all__ = ["get_embedding", "cosine_similarity", "search_chunks", "get_completion"]

```

### src/kbol/core/embedding.py

```python
import httpx
from typing import List
import numpy as np


async def get_embedding(text: str, url: str = "http://localhost:11434") -> List[float]:
    """Get embedding for query text."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            if "error" in result:
                raise Exception(f"Embedding error: {result['error']}")
            return result["embedding"]
        except Exception as e:
            raise Exception(f"Error getting embedding: {str(e)}")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

```

### src/kbol/core/llm.py

```python
import httpx
from typing import Optional


async def get_completion(
    prompt: str,
    context: str,
    url: str = "http://localhost:11434",
    model: str = "phi3",
    temperature: float = 0.7,
) -> str:
    """Get completion from Ollama.

    Args:
        prompt: Question to ask
        context: Context to use
        url: Ollama API URL
        model: Model name
        temperature: Generation temperature
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(f"Ollama error: {data['error']}")
            return data["response"]
        except httpx.TimeoutError:
            raise Exception("Ollama request timed out after 60 seconds")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise Exception(f"Error getting completion: {str(e)}")

```

### src/kbol/core/search.py

```python
from pathlib import Path
import json
from typing import List, Dict
from .embedding import get_embedding, cosine_similarity


async def search_chunks(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
) -> List[Dict]:
    """Search for relevant chunks."""
    query_embedding = await get_embedding(query)
    all_chunks = []

    try:
        for json_file in Path("data/processed").glob("*.json"):
            with open(json_file) as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)

        if not all_chunks:
            return []

        # Calculate similarities
        for chunk in all_chunks:
            chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])

        # Filter and sort by similarity
        relevant_chunks = [
            c for c in all_chunks if c["similarity"] > similarity_threshold
        ]
        return sorted(relevant_chunks, key=lambda x: x["similarity"], reverse=True)[
            :top_k
        ]
    except Exception as e:
        raise Exception(f"Error searching chunks: {str(e)}")

```

### src/kbol/db/__init__.py

```python

```

### src/kbol/indexer/__init__.py

```python
from .core.processor import BookIndexer

__all__ = ["BookIndexer"]

```

### src/kbol/indexer/core/__init__.py

```python

```

### src/kbol/indexer/core/chunker.py

```python
from typing import List
import tiktoken


class TextChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks of roughly equal token count."""
        if not text.strip():
            return []

        # Get token indices for the text
        tokens = self.tokenizer.encode(text)

        # Calculate chunk boundaries
        chunk_indices = []
        start = 0
        while start < len(tokens):
            # Get end index for this chunk
            end = start + self.chunk_size

            # If this isn't the last chunk, try to break at a sentence
            if end < len(tokens):
                # Look for sentence breaks in the overlap region
                overlap_start = max(0, end - self.chunk_overlap)
                text_segment = self.tokenizer.decode(tokens[overlap_start:end])

                # Try to break at sentence end
                sentences = text_segment.split(".")
                if len(sentences) > 1:
                    # Find last complete sentence
                    last_sentence = text_segment.rindex(".")
                    end = overlap_start + last_sentence + 1

            chunk_indices.append((start, min(end, len(tokens))))
            start = end - self.chunk_overlap

        # Decode chunks
        chunks = []
        for start, end in chunk_indices:
            chunk_text = self.tokenizer.decode(tokens[start:end]).strip()
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)

        return chunks

```

### src/kbol/indexer/core/embedder.py

```python
import httpx
from typing import List
import asyncio


class Embedder:
    def __init__(
        self, url: str = "http://localhost:11434", model: str = "nomic-embed-text"
    ):
        self.url = url
        self.model = model

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts."""
        async with httpx.AsyncClient() as client:
            tasks = []
            for text in texts:
                task = client.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30.0,
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            embeddings = []

            for response in responses:
                if isinstance(response, Exception):
                    embeddings.append(None)
                else:
                    result = response.json()
                    embeddings.append(result.get("embedding"))

            return embeddings

```

### src/kbol/indexer/core/processor.py

```python
from pathlib import Path
from typing import List, Dict, Optional
import os
import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich import progress
from pypdf import PdfReader

from .chunker import TextChunker
from .embedder import Embedder
from ...tracking import DocumentTracker, ProcessingConfig
from ..utils.progress import create_progress


class BookIndexer:
    """Process and index books with caching support."""

    def __init__(
        self,
        *,  # Force keyword arguments
        embed_model: str = "nomic-embed-text",
        ollama_url: str = "http://localhost:11434",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        batch_size: int = 10,
        max_retries: int = 3,
        db_url: Optional[str] = None,
    ):
        """Initialize BookIndexer with tracking support.

        Args:
            embed_model: Name of the Ollama model to use for embeddings
            ollama_url: URL of the Ollama server
            chunk_size: Target size of text chunks in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            batch_size: Number of chunks to process at once
            max_retries: Maximum number of retries for failed operations
            db_url: Database URL for tracking (defaults to DATABASE_URL env var)
        """
        # Initialize core components
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedder = Embedder(url=ollama_url, model=embed_model)

        # Configuration
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.console = Console()

        # Initialize tracking
        self.tracker = DocumentTracker(
            db_url or os.getenv("DATABASE_URL", "postgresql://localhost:5432/kbol_db")
        )
        self.config = ProcessingConfig.from_indexer(self)

        # Processing statistics
        self.stats = {
            "total_chunks": 0,
            "total_tokens": 0,
            "failed_chunks": 0,
            "processed_books": 0,
            "skipped_books": 0,
            "processing_time": 0,
            "embedding_time": 0,
        }

    async def _process_chunks(
        self,
        chunks: List[str],
        page_num: int,
        book_name: str,
        progress_bar: Optional[progress.Progress] = None,
        task_id: Optional[str] = None,
    ) -> List[Dict]:
        """Process a batch of chunks with embeddings."""
        processed_chunks = []

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]

            # Get embeddings with retries
            for attempt in range(self.max_retries):
                try:
                    embeddings = await self.embedder.get_embeddings_batch(batch)
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        self.console.print(
                            f"[red]Failed to get embeddings after {self.max_retries} attempts: {e}[/red]"
                        )
                        raise
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

            # Create chunk objects
            for chunk_text, embedding in zip(batch, embeddings):
                if embedding is not None:
                    chunk = {
                        "book": book_name,
                        "page": page_num,
                        "content": chunk_text,
                        "embedding": embedding,
                        "token_count": len(self.chunker.tokenizer.encode(chunk_text)),
                        "processed_at": datetime.now().isoformat(),
                    }
                    processed_chunks.append(chunk)
                    self.stats["total_chunks"] += 1
                    self.stats["total_tokens"] += chunk["token_count"]
                else:
                    self.stats["failed_chunks"] += 1

            if progress_bar and task_id:
                progress_bar.advance(task_id, len(batch))

        return processed_chunks

    async def process_pdf(
        self, pdf_path: Path, progress_bar: progress.Progress
    ) -> List[Dict]:
        """Process a single PDF file with caching support.

        Args:
            pdf_path: Path to the PDF file
            progress_bar: Progress bar instance for tracking

        Returns:
            List of processed chunks with embeddings
        """
        # Check if we need to process this file
        should_process, error = await self.tracker.should_process(pdf_path, self.config)

        if not should_process:
            self.console.print(
                f"[yellow]Skipping {pdf_path.name} - already processed[/yellow]"
            )
            self.stats["skipped_books"] += 1
            return []

        if error:
            self.console.print(
                f"[yellow]Retrying {pdf_path.name} - previous attempt failed: {error}[/yellow]"
            )

        # Setup progress tracking
        reader = PdfReader(pdf_path)
        chunks = []
        output_path = Path("data/processed") / f"{pdf_path.stem}.json"
        temp_path = output_path.with_suffix(".tmp.json")

        # Initialize progress bars
        total_pages = len(reader.pages)
        main_task = progress_bar.add_task(
            f"[cyan]Processing {pdf_path.name}[/cyan]", total=total_pages
        )

        try:
            start_time = datetime.now()

            for page_num, page in enumerate(reader.pages, 1):
                # Extract and chunk text
                text = page.extract_text()
                if not text.strip():
                    progress_bar.advance(main_task)
                    continue

                page_chunks = self.chunker.chunk_text(text)

                # Process chunks
                processed_chunks = await self._process_chunks(
                    chunks=page_chunks,
                    page_num=page_num,
                    book_name=pdf_path.stem,
                    progress_bar=progress_bar,
                    task_id=main_task,
                )
                chunks.extend(processed_chunks)

                # Save intermediate results periodically
                if page_num % 10 == 0:
                    self._save_chunks(temp_path, chunks)

                progress_bar.advance(main_task)

            # Save final results
            self._save_chunks(output_path, chunks)
            temp_path.unlink(missing_ok=True)

            # Record successful processing
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats["processing_time"] += processing_time

            await self.tracker.record_processing(
                file_path=pdf_path,
                config=self.config,
                chunks_count=len(chunks),
                total_tokens=sum(c["token_count"] for c in chunks),
                metadata={
                    "pages_processed": total_pages,
                    "processing_time_seconds": processing_time,
                    "average_chunk_size": (
                        sum(c["token_count"] for c in chunks) / len(chunks)
                        if chunks
                        else 0
                    ),
                },
            )

            self.stats["processed_books"] += 1

        except Exception as e:
            # Record failed processing
            await self.tracker.record_processing(
                file_path=pdf_path,
                config=self.config,
                chunks_count=0,
                total_tokens=0,
                status="failed",
                error_message=str(e),
            )
            # Clean up temp file
            temp_path.unlink(missing_ok=True)
            raise

        finally:
            progress_bar.remove_task(main_task)

        return chunks

    def _save_chunks(self, path: Path, chunks: List[Dict]) -> None:
        """Save chunks to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    async def process_books(self, books_dir: Path) -> List[Dict]:
        """Process all PDFs in directory with caching support.

        Args:
            books_dir: Directory containing PDF files

        Returns:
            List of all processed chunks
        """
        pdf_files = list(books_dir.glob("*.pdf"))
        if not pdf_files:
            self.console.print("[yellow]No PDF files found in directory[/yellow]")
            return []

        start_time = datetime.now()
        all_chunks = []

        with create_progress() as progress_bar:
            for pdf_file in pdf_files:
                try:
                    chunks = await self.process_pdf(pdf_file, progress_bar)
                    all_chunks.extend(chunks)
                except Exception as e:
                    self.console.print(
                        Panel(
                            f"[red]Failed to process {pdf_file.name}[/red]\n{str(e)}",
                            title="Error",
                            border_style="red",
                        )
                    )

        # Print final statistics
        total_time = (datetime.now() - start_time).total_seconds()
        self.stats["total_time"] = total_time

        if self.stats["total_chunks"] > 0 or self.stats["skipped_books"] > 0:
            self.console.print(
                Panel(
                    f"""[green]Processing Complete[/green]
                    • Total Time: {total_time:.1f}s
                    • Processed Books: {self.stats['processed_books']}/{len(pdf_files)}
                    • Skipped Books: {self.stats['skipped_books']}
                    • Total Chunks: {self.stats['total_chunks']}
                    • Total Tokens: {self.stats['total_tokens']:,}
                    • Failed Chunks: {self.stats['failed_chunks']}
                    • Average Chunk Size: {(avg := self.stats['total_tokens'] / self.stats['total_chunks'] if self.stats['total_chunks'] else 0):.0f} tokens
                    • Processing Rate: {self.stats['total_tokens'] / total_time:.0f} tokens/second""",
                    title="Processing Statistics",
                    border_style="green",
                )
            )
        else:
            self.console.print("[yellow]No new chunks were processed.[/yellow]")

        return all_chunks

    @classmethod
    def create_with_env(cls, **overrides) -> "BookIndexer":
        """Create BookIndexer instance using environment variables with overrides.

        Example:
            indexer = BookIndexer.create_with_env(chunk_size=256)
        """
        config = {
            "embed_model": os.getenv("KBOL_EMBED_MODEL", "nomic-embed-text"),
            "ollama_url": os.getenv("KBOL_OLLAMA_URL", "http://localhost:11434"),
            "chunk_size": int(os.getenv("KBOL_CHUNK_SIZE", "512")),
            "chunk_overlap": int(os.getenv("KBOL_CHUNK_OVERLAP", "50")),
            "batch_size": int(os.getenv("KBOL_BATCH_SIZE", "10")),
            "max_retries": int(os.getenv("KBOL_MAX_RETRIES", "3")),
            "db_url": os.getenv("DATABASE_URL"),
        }

        # Apply overrides
        config.update(overrides)

        return cls(**config)

```

### src/kbol/indexer/utils/__init__.py

```python

```

### src/kbol/indexer/utils/progress.py

```python
from rich import progress


def create_progress() -> progress.Progress:
    """Create a progress bar with standard formatting."""
    return progress.Progress(
        progress.TextColumn("[progress.description]{task.description}"),
        progress.BarColumn(),
        progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        progress.TimeElapsedColumn(),
        progress.TimeRemainingColumn(),
    )

```

### src/kbol/tracking/__init__.py

```python
from .document_tracker import DocumentTracker, ProcessingConfig

__all__ = ["DocumentTracker", "ProcessingConfig"]

```

### src/kbol/tracking/document_tracker.py

```python
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import Json
from dataclasses import dataclass, asdict
import inspect
import asyncio


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    chunk_size: int
    chunk_overlap: int
    embed_model: str
    processor_version: str

    @classmethod
    def from_indexer(cls, indexer: "BookIndexer") -> "ProcessingConfig":
        """Create config from BookIndexer instance."""
        chunker_code = inspect.getsource(indexer.chunker.__class__)
        embedder_code = inspect.getsource(indexer.embedder.__class__)

        version_hash = hashlib.sha256()
        version_hash.update(chunker_code.encode())
        version_hash.update(embedder_code.encode())

        return cls(
            chunk_size=indexer.chunker.chunk_size,
            chunk_overlap=indexer.chunker.chunk_overlap,
            embed_model=indexer.embedder.model,
            processor_version=version_hash.hexdigest()[:12],
        )


class DocumentTracker:
    """Tracks document processing state and manages caching."""

    def __init__(self, db_url: str):
        """Initialize tracker with database connection."""
        self.db_url = db_url
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure required database schema exists."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
                cur.execute(schema_path.read_text())

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def should_process(
        self, file_path: Path, config: ProcessingConfig
    ) -> Tuple[bool, Optional[str]]:
        """Check if document needs processing."""
        # Run file hash computation in thread pool due to I/O
        file_hash = await asyncio.get_event_loop().run_in_executor(
            None, self.compute_file_hash, file_path
        )

        def _check_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, error_message 
                        FROM processed_documents
                        WHERE file_path = %s 
                          AND file_hash = %s
                          AND chunk_size = %s
                          AND chunk_overlap = %s
                          AND embed_model = %s
                          AND processor_version = %s
                    """,
                        (
                            str(file_path),
                            file_hash,
                            config.chunk_size,
                            config.chunk_overlap,
                            config.embed_model,
                            config.processor_version,
                        ),
                    )
                    return cur.fetchone()

        # Run database query in thread pool
        result = await asyncio.get_event_loop().run_in_executor(None, _check_db)

        if result is None:
            return True, None  # Never processed

        status, error = result
        if status == "failed":
            return True, error  # Retry failed processing

        return False, None  # Already processed successfully

    async def record_processing(
        self,
        file_path: Path,
        config: ProcessingConfig,
        chunks_count: int,
        total_tokens: int,
        status: str = "completed",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Record document processing results."""
        file_hash = await asyncio.get_event_loop().run_in_executor(
            None, self.compute_file_hash, file_path
        )

        def _record_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Record processor version if new
                    cur.execute(
                        """
                        INSERT INTO processor_versions (version_hash, config_json)
                        VALUES (%s, %s)
                        ON CONFLICT (version_hash) DO NOTHING
                    """,
                        (config.processor_version, Json(asdict(config))),
                    )

                    # Update or insert processing record
                    cur.execute(
                        """
                        INSERT INTO processed_documents (
                            file_path, file_hash, chunk_size, chunk_overlap,
                            embed_model, processor_version, chunks_count,
                            total_tokens, status, error_message, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (file_path) DO UPDATE SET
                            file_hash = EXCLUDED.file_hash,
                            chunk_size = EXCLUDED.chunk_size,
                            chunk_overlap = EXCLUDED.chunk_overlap,
                            embed_model = EXCLUDED.embed_model,
                            processor_version = EXCLUDED.processor_version,
                            chunks_count = EXCLUDED.chunks_count,
                            total_tokens = EXCLUDED.total_tokens,
                            status = EXCLUDED.status,
                            error_message = EXCLUDED.error_message,
                            metadata = EXCLUDED.metadata,
                            processed_at = CURRENT_TIMESTAMP
                    """,
                        (
                            str(file_path),
                            file_hash,
                            config.chunk_size,
                            config.chunk_overlap,
                            config.embed_model,
                            config.processor_version,
                            chunks_count,
                            total_tokens,
                            status,
                            error_message,
                            Json(metadata or {}),
                        ),
                    )

        # Run database operations in thread pool
        await asyncio.get_event_loop().run_in_executor(None, _record_db)

```
