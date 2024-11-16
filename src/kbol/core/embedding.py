import httpx
from typing import List
import numpy as np


async def get_embedding(text: str, url: str = "http://localhost:11434") -> List[float]:
    """Get embedding for query text."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30.0,
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
