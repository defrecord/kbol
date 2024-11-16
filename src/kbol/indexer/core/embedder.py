import httpx
from typing import List
import asyncio

class Embedder:
    def __init__(self, url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.url = url
        self.model = model

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts."""
        async with httpx.AsyncClient() as client:
            tasks = []
            for text in texts:
                task = client.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
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
