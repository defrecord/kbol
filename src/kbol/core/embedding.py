# src/kbol/core/embedding.py

from typing import List
import numpy as np
from .http import create_client, get_ollama_url


async def get_embedding(text: str) -> List[float]:
    """Get embedding for query text."""
    url = get_ollama_url()
    async with await create_client(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            response.raise_for_status()
            result = response.json()
            if "error" in result:
                raise Exception(f"Embedding error: {result['error']}")
            return result["embedding"]
        except Exception as e:
            raise Exception(f"Error getting embedding: {str(e)}")


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
