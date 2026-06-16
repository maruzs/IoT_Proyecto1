import json
import logging
import re

from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class JsonValidationError(Exception):
    """Raised when JSON cannot be extracted even after all correction retries."""

    pass


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences and any leading/trailing non-JSON text.

    Handles both ```json ... ``` and ``` ... ``` variations.
    """
    # Remove ```json ... ``` or ``` ... ``` blocks
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```", "", text)
    text = text.strip()

    # Try to find the first JSON object/array in the text
    # Look for the first '{' or '[' and the matching last '}' or ']'
    first_brace = text.find("{")
    first_bracket = text.find("[")

    if first_brace == -1 and first_bracket == -1:
        return text  # No JSON-like structure found

    if first_brace == -1:
        start = first_bracket
    elif first_bracket == -1:
        start = first_brace
    else:
        start = min(first_brace, first_bracket)

    # Find the last matching closing brace/bracket
    last_brace = text.rfind("}")
    last_bracket = text.rfind("]")

    if last_brace == -1 and last_bracket == -1:
        return text[start:]

    end_candidates = [c for c in (last_brace, last_bracket) if c != -1]
    end = max(end_candidates)

    return text[start:end + 1]


def extract_json(text: str) -> dict | None:
    """Attempt to parse JSON from raw text after stripping fences.

    Returns the parsed dict or None if parsing fails.
    """
    cleaned = strip_markdown_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


async def validate_and_parse(
    ollama_client: OllamaClient,
    raw_text: str,
    correction_prompt: str,
    max_retries: int,
) -> dict:
    """Validate and parse JSON from raw LLM output.

    If parsing fails, sends a correction prompt to Ollama and retries.
    Raises JsonValidationError after all retries are exhausted.
    """
    result = extract_json(raw_text)
    if result is not None:
        return result

    for attempt in range(1, max_retries):
        logger.warning(
            "JSON parse failed, attempting correction (attempt %s/%s)",
            attempt,
            max_retries,
        )
        corrected = await ollama_client.generate(
            prompt=f"{correction_prompt}\n\nReturn ONLY valid JSON, no explanations.\n\n{raw_text}",
        )
        result = extract_json(corrected)
        if result is not None:
            return result

    raise JsonValidationError(
        f"Could not parse valid JSON after {max_retries} attempts"
    )
