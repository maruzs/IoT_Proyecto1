import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Raised when all Ollama retries are exhausted or an unrecoverable error occurs."""

    pass


class OllamaClient:
    """Async HTTP client for Ollama's /api/generate endpoint.

    Handles timeouts, HTTP errors, and exponential backoff retries.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int,
        max_retries: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"},
        )

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send a prompt to Ollama and return the raw text response.

        Retries on TimeoutException and HTTPStatusError with exponential
        backoff (1s, 2s, 4s, ... up to max_retries).
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        if system_prompt is not None:
            payload["system"] = system_prompt

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["response"]
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Ollama timeout (attempt %s/%s)",
                    attempt + 1,
                    self.max_retries,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "Ollama HTTP error %s (attempt %s/%s)",
                    exc.response.status_code,
                    attempt + 1,
                    self.max_retries,
                )
            except Exception as exc:
                # Unrecoverable (e.g., JSON decode, connection refused) — don't retry
                raise OllamaError(f"Ollama request failed: {exc}") from exc

            if attempt < self.max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s, ...
                logger.info("Retrying Ollama in %s seconds...", backoff)
                await asyncio.sleep(backoff)

        raise OllamaError(
            f"Ollama request failed after {self.max_retries} retries"
        ) from last_error

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient session."""
        await self._client.aclose()
