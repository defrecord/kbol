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

# Manual definitions with stable URLs
MANUALS = {
    # GNU Emacs & Related
    "emacs_manual.pdf": "https://www.gnu.org/software/emacs/manual/pdf/emacs.pdf",
    "elisp_manual.pdf": "https://www.gnu.org/software/emacs/manual/pdf/elisp.pdf",
    "org-mode_manual.pdf": "https://orgmode.org/org.pdf",
    
    # GNU Programming Languages & Tools
    "guile_manual.pdf": "https://www.gnu.org/software/guile/manual/guile.pdf",
    "make_manual.pdf": "https://www.gnu.org/software/make/manual/make.pdf",
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
            }
        )

    def is_valid_pdf(self, file_path: Path) -> bool:
        """Check if file is a valid PDF."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header.startswith(b'%PDF')
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
                console.print(f"[yellow]Existing PDF invalid, redownloading: {filename}")
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
@click.option('--manuals-dir', type=click.Path(), default='data/manuals',
              help='Directory to store downloaded manuals')
@click.option('--books-dir', type=click.Path(), default='data/books',
              help='Directory to create symlinks')
@click.option('--timeout', type=int, default=300,
              help='Download timeout in seconds')
@click.option('--force', is_flag=True, help='Force redownload of all manuals')
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

if __name__ == '__main__':
    main()
