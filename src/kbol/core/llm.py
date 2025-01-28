# src/kbol/core/llm.py

from typing import Optional, AsyncIterator
import json
from rich.live import Live
from rich.markdown import Markdown
from .http import create_client, get_ollama_url


async def stream_completion(
    prompt: str,
    context: str,
    model: str = "phi3",
    temperature: float = 0.7,
) -> AsyncIterator[str]:
    """Stream completion from Ollama."""
    url = get_ollama_url()
    async with await create_client(timeout=60.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:",
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if "error" in data:
                            raise Exception(f"Ollama error: {data['error']}")
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            raise Exception(f"Error streaming completion: {str(e)}")


async def get_completion(
    prompt: str,
    context: str,
    model: str = "phi3",
    temperature: float = 0.7,
) -> str:
    """Get completion from Ollama with live updates."""
    chunks = []
    try:
        with Live(Markdown(""), refresh_per_second=10) as live:
            async for chunk in stream_completion(
                prompt=prompt,
                context=context,
                model=model,
                temperature=temperature,
            ):
                chunks.append(chunk)
                # Update display with accumulated text
                live.update(Markdown("".join(chunks)))
        
        return "".join(chunks)
    except Exception as e:
        raise Exception(f"Error getting completion: {str(e)}")
