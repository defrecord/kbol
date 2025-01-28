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
