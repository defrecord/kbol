from pathlib import Path
from pypdf import PdfReader
from typing import List, Dict
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich import progress
from rich.progress import Progress  # Add this for type hints

from .chunker import TextChunker
from .embedder import Embedder
from ..utils.progress import create_progress

class BookIndexer:
    def __init__(
        self,
        *,  # Force keyword arguments
        embed_model: str = "nomic-embed-text",
        ollama_url: str = "http://localhost:11434",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        batch_size: int = 10,
        max_retries: int = 3,
    ):
        """Initialize BookIndexer.
        
        Args:
            embed_model: Name of the Ollama model to use for embeddings
            ollama_url: URL of the Ollama server
            chunk_size: Target size of text chunks in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            batch_size: Number of chunks to process at once
            max_retries: Maximum number of retries for failed operations
        """
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedder = Embedder(url=ollama_url, model=embed_model)
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.console = Console()
        self.stats = {
            "total_chunks": 0,
            "total_tokens": 0,
            "failed_chunks": 0,
            "processed_books": 0,
        }

    async def process_pdf(self, pdf_path: Path, progress_bar: Progress) -> List[Dict]:
        """Process a single PDF file with detailed progress tracking."""
        chunks = []
        reader = PdfReader(pdf_path)
        output_path = Path("data/processed") / f"{pdf_path.stem}.json"
        temp_path = output_path.with_suffix('.tmp.json')

        # Setup progress bars
        main_task = progress_bar.add_task(
            f"[cyan]{pdf_path.name}[/cyan]", 
            total=len(reader.pages)
        )

        try:
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if not text.strip():
                    continue

                page_chunks = self.chunker.chunk_text(text)

                # Process in batches
                for i in range(0, len(page_chunks), self.batch_size):
                    batch = page_chunks[i : i + self.batch_size]
                    embeddings = await self.embedder.get_embeddings_batch(batch)

                    for chunk_text, embedding in zip(batch, embeddings):
                        if embedding is not None:
                            chunk = {
                                "book": pdf_path.stem,
                                "page": page_num,
                                "content": chunk_text,
                                "embedding": embedding,
                                "token_count": len(self.chunker.tokenizer.encode(chunk_text)),
                                "processed_at": datetime.now().isoformat(),
                            }
                            chunks.append(chunk)
                            self.stats["total_chunks"] += 1
                            self.stats["total_tokens"] += chunk["token_count"]
                        else:
                            self.stats["failed_chunks"] += 1

                progress_bar.update(main_task, advance=1)

                # Save intermediate results every 10 pages
                if page_num % 10 == 0:
                    with open(temp_path, "w") as f:
                        json.dump(chunks, f, indent=2)

            # Save final results
            with open(output_path, "w") as f:
                json.dump(chunks, f, indent=2)
            
            # Remove temp file
            temp_path.unlink(missing_ok=True)

            self.stats["processed_books"] += 1

        except Exception as e:
            self.console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
            # Clean up temp file on error
            temp_path.unlink(missing_ok=True)
            raise
        finally:
            progress_bar.remove_task(main_task)

        return chunks

    async def process_books(self, books_dir: Path) -> List[Dict]:
        """Process all PDFs with improved progress tracking."""
        pdf_files = list(books_dir.glob("*.pdf"))
        if not pdf_files:
            self.console.print("[yellow]No PDF files found in directory[/yellow]")
            return []

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
                        )
                    )

        # Print final statistics
        if self.stats["total_chunks"] > 0:
            self.console.print(
                Panel(
                    f"""[green]Processing Complete[/green]
                    • Processed Books: {self.stats['processed_books']}/{len(pdf_files)}
                    • Total Chunks: {self.stats['total_chunks']}
                    • Total Tokens: {self.stats['total_tokens']:,}
                    • Failed Chunks: {self.stats['failed_chunks']}
                    • Average Chunk Size: {self.stats['total_tokens'] / self.stats['total_chunks']:.0f} tokens""",
                    title="Statistics",
                )
            )
        else:
            self.console.print("[yellow]No chunks were processed successfully.[/yellow]")

        return all_chunks
