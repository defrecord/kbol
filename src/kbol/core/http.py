# src/kbol/core/http.py

import os
import httpx
from typing import Optional, Dict

def get_proxies() -> Dict[str, str]:
    """Get proxy settings from environment variables."""
    proxies = {}
    if http_proxy := os.getenv('HTTP_PROXY'):
        proxies['http://'] = http_proxy
    if https_proxy := os.getenv('HTTPS_PROXY'):
        proxies['https://'] = https_proxy
    return proxies

def get_ollama_url() -> str:
    """Get Ollama host URL from environment."""
    return os.getenv('OLLAMA_HOST', 'http://localhost:11434')

async def create_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Create an HTTP client with proxy and timeout configuration."""
    proxies = get_proxies()
    client = httpx.AsyncClient(
        proxies=proxies if proxies else None,
        timeout=timeout,
        verify=False if proxies else True  # Disable SSL verification when using proxy for debugging
    )
    return client
