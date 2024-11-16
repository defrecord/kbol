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
                    • Average Chunk Size: {self.stats['total_tokens'] / self.stats['total_chunks']:.0f} tokens
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
