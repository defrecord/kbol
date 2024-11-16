import httpx
from typing import Optional


async def get_completion(
    prompt: str,
    context: str,
    url: str = "http://localhost:11434",
    model: str = "phi3",
    temperature: float = 0.7,
) -> str:
    """Get completion from Ollama.

    Args:
        prompt: Question to ask
        context: Context to use
        url: Ollama API URL
        model: Model name
        temperature: Generation temperature
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(f"Ollama error: {data['error']}")
            return data["response"]
        except httpx.TimeoutError:
            raise Exception("Ollama request timed out after 60 seconds")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise Exception(f"Error getting completion: {str(e)}")
