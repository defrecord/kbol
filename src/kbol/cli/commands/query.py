# src/kbol/cli/commands/query.py

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from pathlib import Path
import asyncio
from datetime import datetime
from typing import Optional

from ...core.search import search_chunks
from ...core.llm import stream_completion

console = Console()


async def query_impl(
    question: str,
    top_k: int,
    show_context: bool,
    book_filter: Optional[str],
    model: str,
    temperature: float,
    save_responses: bool = True,
):
    """Implementation of query command."""
    try:
        chunks = []
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
            
            # Show source information
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

            # Stream the response
            response_parts = []
            console.print("\n[cyan]Generating response...[/cyan]")
            try:
                async for chunk in stream_completion(
                    question,
                    context,
                    model=model,
                    temperature=temperature,
                ):
                    response_parts.append(chunk)
                
                # Final response
                final_response = "".join(response_parts)
                console.print(Panel(
                    Markdown(final_response),
                    title="Answer",
                    border_style="green"
                ))

                # Save response if requested
                if save_responses:
                    answers_dir = Path("data/answers")
                    answers_dir.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = answers_dir / f"{timestamp}.md"
                    
                    try:
                        filename.write_text(final_response)
                        console.print(f"[dim]Saved to {filename}[/dim]")
                    except Exception as e:
                        console.print(f"[yellow]Could not save response: {e}[/yellow]")

            except Exception as e:
                console.print(f"[red]Error generating response: {str(e)}[/red]")
                if show_context:
                    console.print("\n[yellow]Retrieved context was:[/yellow]")
                    console.print(
                        Panel(context, title="Context", border_style="yellow")
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
        save_responses: bool = typer.Option(
            True, "--save/--no-save", help="Save responses to data/answers"
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
                save_responses=save_responses,
            )
        )
