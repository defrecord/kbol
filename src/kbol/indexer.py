import httpx
from pathlib import Path
from pypdf import PdfReader
from typing import List, Dict, Iterator, Callable, Optional
import asyncio
import tiktoken
import json
from datetime import datetime
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
import asyncio


class BookIndexer:
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        embed_model: str = "nomic-embed-text",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        batch_size: int = 10,  # Number of chunks to embed at once
        max_retries: int = 3,
    ):
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.console = Console()
        self.stats = {
            "total_chunks": 0,
            "total_tokens": 0,
            "failed_chunks": 0,
            "processed_books": 0,
        }

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts."""
        async with httpx.AsyncClient() as client:
            tasks = []
            for text in texts:
                task = client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text},
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

    async def process_pdf(self, pdf_path: Path, progress: Progress) -> List[Dict]:
        """Process a single PDF file with detailed progress tracking."""
        chunks = []
        current_batch = []
        reader = PdfReader(pdf_path)

        # Setup progress bars
        main_task = progress.add_task(f"[cyan]{pdf_path.name}", total=len(reader.pages))

        try:
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if not text.strip():
                    continue

                page_chunks = list(self.chunk_text(text))

                # Process in batches
                for i in range(0, len(page_chunks), self.batch_size):
                    batch = page_chunks[i : i + self.batch_size]
                    embeddings = await self.get_embeddings_batch(batch)

                    for chunk_text, embedding in zip(batch, embeddings):
                        if embedding is not None:
                            chunk = {
                                "book": pdf_path.stem,
                                "page": page_num,
                                "content": chunk_text,
                                "embedding": embedding,
                                "token_count": len(self.tokenizer.encode(chunk_text)),
                                "processed_at": datetime.now().isoformat(),
                            }
                            chunks.append(chunk)
                            self.stats["total_chunks"] += 1
                            self.stats["total_tokens"] += chunk["token_count"]
                        else:
                            self.stats["failed_chunks"] += 1

                progress.update(main_task, advance=1)

                # Save intermediate results every 10 pages
                if page_num % 10 == 0:
                    output_path = (
                        Path("data/processed") / f"{pdf_path.stem}_partial.json"
                    )
                    with open(output_path, "w") as f:
                        json.dump(chunks, f, indent=2)

            # Save final results
            output_path = Path("data/processed") / f"{pdf_path.stem}.json"
            with open(output_path, "w") as f:
                json.dump(chunks, f, indent=2)

            self.stats["processed_books"] += 1

        except Exception as e:
            self.console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
            raise
        finally:
            progress.remove_task(main_task)

        return chunks

    async def process_books(self, books_dir: Path) -> List[Dict]:
        """Process all PDFs with improved progress tracking."""
        pdf_files = list(books_dir.glob("*.pdf"))
        if not pdf_files:
            self.console.print("[yellow]No PDF files found in directory[/yellow]")
            return []

        all_chunks = []
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:
            for pdf_file in pdf_files:
                try:
                    chunks = await self.process_pdf(pdf_file, progress)
                    all_chunks.extend(chunks)
                except Exception as e:
                    self.console.print(
                        Panel(
                            f"[red]Failed to process {pdf_file.name}[/red]\n{str(e)}",
                            title="Error",
                        )
                    )

        # Print final statistics
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

        return all_chunks
