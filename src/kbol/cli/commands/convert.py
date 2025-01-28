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
