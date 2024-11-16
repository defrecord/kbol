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
