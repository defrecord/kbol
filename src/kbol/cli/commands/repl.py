# src/kbol/cli/commands/repl.py

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import asyncio
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from pathlib import Path
import os

from ...core.search import search_chunks
from ...core.llm import get_completion

console = Console()

def get_prompt_style():
    return HTML('<green>Ask a question</green> › ')

async def repl_impl(
    model: str,
    temperature: float,
    show_context: bool,
    book_filter: Optional[str],
    top_k: int,
):
    """Interactive REPL implementation."""
    # Create history directory if it doesn't exist
    history_dir = Path.home() / ".kbol"
    history_dir.mkdir(exist_ok=True)
    history_file = history_dir / "history.txt"

    # Initialize prompt session with history and auto-suggest
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
        vi_mode=False,  # Set to True for vi mode if you prefer
        complete_while_typing=True,
    )

    console.print("[cyan]KBOL Interactive Query REPL[/cyan]")

    while True:
        try:
            # Get question with enhanced prompt
            question = await session.prompt_async(
                get_prompt_style(),
                enable_suspend=True,  # Enables Ctrl+Z
                mouse_support=True,
                complete_in_thread=True,
            )
            
            if not question.strip():
                continue

            if question.lower() in ('exit', 'quit'):
                break

            # Search and get response
            with console.status("[cyan]Searching knowledge base...[/cyan]"):
                chunks = await search_chunks(question, top_k)
                if not chunks:
                    console.print("[yellow]No relevant content found.[/yellow]\n")
                    continue

                if book_filter:
                    chunks = [c for c in chunks if book_filter.lower() in c["book"].lower()]
                    if not chunks:
                        console.print(f"[yellow]No results found in book matching '{book_filter}'[/yellow]\n")
                        continue

                chunks.sort(key=lambda x: (x["book"], x.get("page", 0)))
                context_parts = []
                
                if show_context:
                    console.print("\n[cyan]Found relevant content in:[/cyan]")
                
                current_book = None
                for chunk in chunks:
                    if chunk["book"] != current_book:
                        current_book = chunk["book"]
                        if show_context:
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

                console.print("\n[cyan]Generating response...[/cyan]")
                try:
                    answer = await get_completion(
                        question,
                        context,
                        model=model,
                        temperature=temperature,
                    )
                    console.print(Panel(Markdown(answer), title="Answer", border_style="green"))
                    console.print()  # Add blank line for readability
                except Exception as e:
                    console.print(f"[red]Error generating response: {str(e)}[/red]")
                    if show_context:
                        console.print("\n[yellow]Retrieved context was:[/yellow]")
                        console.print(Panel(context, title="Context", border_style="yellow"))
                    continue

        except EOFError:  # Ctrl+D
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except KeyboardInterrupt:  # Ctrl+C
            continue  # Clear current line and continue
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            continue

def register(app: typer.Typer):
    """Register repl command with the CLI app."""

    @app.command()
    def repl(
        model: str = typer.Option(
            "phi3", "--model", "-m", help="Ollama model to use for responses"
        ),
        temperature: float = typer.Option(
            0.7, "--temperature", "-t", help="Model temperature (0.0-1.0)", min=0.0, max=1.0
        ),
        show_context: bool = typer.Option(
            False, "--show-context", "-c", help="Show retrieved context chunks"
        ),
        book_filter: Optional[str] = typer.Option(
            None, "--book", "-b", help="Filter to specific book"
        ),
        top_k: int = typer.Option(
            5, "--top-k", "-k", help="Number of chunks to retrieve"
        ),
    ):
        """Start an interactive query REPL with enhanced editing.

        Features:
        • Command history (stored in ~/.kbol/history.txt)
        • Emacs-style keybindings (Ctrl+A, Ctrl+E, etc.)
        • History search with Ctrl+R
        • Auto-suggestions from history
        
        Examples:
            kbol repl
            kbol repl --show-context
            kbol repl --model llama2 --temperature 0.8
            kbol repl --book "clojure"
        """
        try:
            asyncio.run(repl_impl(
                model=model,
                temperature=temperature,
                show_context=show_context,
                book_filter=book_filter,
                top_k=top_k,
            ))
        except KeyboardInterrupt:
            console.print("\n[yellow]REPL terminated.[/yellow]")
            raise typer.Exit(0)
        except Exception as e:
            console.print(f"\n[red]Fatal error: {str(e)}[/red]")
            raise typer.Exit(1)
