# src/kbol/tracking/document_tracker.py

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import Json
from dataclasses import dataclass, asdict
import inspect
import asyncio


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    chunk_size: int
    chunk_overlap: int
    embed_model: str
    processor_version: str

    @classmethod
    def from_indexer(cls, indexer: "BookIndexer") -> "ProcessingConfig":
        """Create config from BookIndexer instance."""
        chunker_code = inspect.getsource(indexer.chunker.__class__)
        embedder_code = inspect.getsource(indexer.embedder.__class__)

        version_hash = hashlib.sha256()
        version_hash.update(chunker_code.encode())
        version_hash.update(embedder_code.encode())

        return cls(
            chunk_size=indexer.chunker.chunk_size,
            chunk_overlap=indexer.chunker.chunk_overlap,
            embed_model=indexer.embedder.model,
            processor_version=version_hash.hexdigest()[:12],
        )


class DocumentTracker:
    """Tracks document processing state and manages caching."""

    def __init__(self, db_url: str):
        """Initialize tracker with database connection."""
        self.db_url = db_url
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure required database schema exists."""
        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
                cur.execute(schema_path.read_text())

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def should_process(
        self, file_path: Path, config: ProcessingConfig, force: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Check if document needs processing.
        
        Args:
            file_path: Path to the document
            config: Processing configuration
            force: If True, ignore existing processing state
            
        Returns:
            Tuple of (should_process: bool, error_message: Optional[str])
        """
        if force:
            return True, None

        # Run file hash computation in thread pool
        file_hash = await asyncio.get_event_loop().run_in_executor(
            None, self.compute_file_hash, file_path
        )

        def _check_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT status, error_message 
                        FROM processed_documents
                        WHERE file_path = %s 
                          AND file_hash = %s
                          AND chunk_size = %s
                          AND chunk_overlap = %s
                          AND embed_model = %s
                          AND processor_version = %s
                        """,
                        (
                            str(file_path),
                            file_hash,
                            config.chunk_size,
                            config.chunk_overlap,
                            config.embed_model,
                            config.processor_version,
                        ),
                    )
                    return cur.fetchone()

        # Run database query in thread pool
        result = await asyncio.get_event_loop().run_in_executor(None, _check_db)

        if result is None:
            return True, None  # Never processed

        status, error = result
        if status == "failed":
            return True, error  # Retry failed processing

        return False, None  # Already processed successfully

    async def record_processing(
        self,
        file_path: Path,
        config: ProcessingConfig,
        chunks_count: int,
        total_tokens: int,
        status: str = "completed",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Record document processing results.
        
        Args:
            file_path: Path to the processed document
            config: Processing configuration used
            chunks_count: Number of chunks generated
            total_tokens: Total tokens processed
            status: Processing status ("completed" or "failed")
            error_message: Optional error message if processing failed
            metadata: Optional additional metadata
        """
        file_hash = await asyncio.get_event_loop().run_in_executor(
            None, self.compute_file_hash, file_path
        )

        def _record_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # Record processor version if new
                    cur.execute(
                        """
                        INSERT INTO processor_versions (version_hash, config_json)
                        VALUES (%s, %s)
                        ON CONFLICT (version_hash) DO NOTHING
                        """,
                        (config.processor_version, Json(asdict(config))),
                    )

                    # Update or insert processing record
                    cur.execute(
                        """
                        INSERT INTO processed_documents (
                            file_path, file_hash, chunk_size, chunk_overlap,
                            embed_model, processor_version, chunks_count,
                            total_tokens, status, error_message, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (file_path) DO UPDATE SET
                            file_hash = EXCLUDED.file_hash,
                            chunk_size = EXCLUDED.chunk_size,
                            chunk_overlap = EXCLUDED.chunk_overlap,
                            embed_model = EXCLUDED.embed_model,
                            processor_version = EXCLUDED.processor_version,
                            chunks_count = EXCLUDED.chunks_count,
                            total_tokens = EXCLUDED.total_tokens,
                            status = EXCLUDED.status,
                            error_message = EXCLUDED.error_message,
                            metadata = EXCLUDED.metadata,
                            processed_at = CURRENT_TIMESTAMP
                        """,
                        (
                            str(file_path),
                            file_hash,
                            config.chunk_size,
                            config.chunk_overlap,
                            config.embed_model,
                            config.processor_version,
                            chunks_count,
                            total_tokens,
                            status,
                            error_message,
                            Json(metadata or {}),
                        ),
                    )

                    conn.commit()

        # Run database operations in thread pool
        await asyncio.get_event_loop().run_in_executor(None, _record_db)

    async def reset_tracking(self):
        """Reset all tracking information.
        
        This removes all processing records but keeps version history.
        """
        def _reset_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM processed_documents")
                    conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _reset_db)

    async def clear_all(self):
        """Clear all tracking data including version history."""
        def _clear_db():
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM processed_documents")
                    cur.execute("DELETE FROM processor_versions")
                    conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _clear_db)
