# src/kbol/cli/commands/health.py

import typer
from rich.console import Console
import httpx
import asyncio
from ...core.http import create_client, get_ollama_url

console = Console()

async def health_check_impl():
    """Check if Ollama is running and responding."""
    url = get_ollama_url()
    try:
        async with await create_client(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Test model loading
            test_models = ["nomic-embed-text", "phi3"]  # Add your models here
            for model in test_models:
                try:
                    response = await client.post(
                        f"{url}/api/generate",
                        json={
                            "model": model,
                            "prompt": "test",
                            "stream": False,
                        },
                        timeout=5.0,
                    )
                    response.raise_for_status()
                    console.print(f"[green]✓ Model {model} loaded and responding[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Model {model} not responding: {str(e)}[/red]")
            
            return True
    except Exception as e:
        console.print(f"[red]Error connecting to Ollama: {str(e)}[/red]")
        console.print(f"[yellow]Make sure Ollama is running at {url}[/yellow]")
        return False

def register(app: typer.Typer):
    """Register health command with the CLI app."""

    @app.command()
    def health():
        """Check if Ollama service is healthy and responding."""
        try:
            if asyncio.run(health_check_impl()):
                raise typer.Exit(0)
            raise typer.Exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Health check interrupted.[/yellow]")
            raise typer.Exit(130)
        except Exception as e:
            console.print(f"\n[red]Fatal error: {str(e)}[/red]")
            raise typer.Exit(1)
