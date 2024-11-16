from pathlib import Path
import json
from typing import List, Dict
from .embedding import get_embedding, cosine_similarity


async def search_chunks(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
) -> List[Dict]:
    """Search for relevant chunks."""
    query_embedding = await get_embedding(query)
    all_chunks = []

    try:
        for json_file in Path("data/processed").glob("*.json"):
            with open(json_file) as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)

        if not all_chunks:
            return []

        # Calculate similarities
        for chunk in all_chunks:
            chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])

        # Filter and sort by similarity
        relevant_chunks = [
            c for c in all_chunks if c["similarity"] > similarity_threshold
        ]
        return sorted(relevant_chunks, key=lambda x: x["similarity"], reverse=True)[
            :top_k
        ]
    except Exception as e:
        raise Exception(f"Error searching chunks: {str(e)}")
