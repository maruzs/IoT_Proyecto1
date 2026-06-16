def build_decision_prompt(sensor_context: dict) -> tuple[str, str]:
    """Build system and user prompts for a sensor-driven decision.

    Returns:
        (user_prompt, system_prompt)
    """
    system_prompt = (
        "You are a smart home automation assistant. "
        "Analyze the sensor data and return a JSON object with the recommended action. "
        'Format: {"action": "string", "reason": "string", "confidence": number 0-1}'
    )

    lines = ["Current sensor readings:"]
    for key, value in sensor_context.items():
        lines.append(f"- {key}: {value}")
    lines.append("\nBased on these readings, what action should be taken?")

    user_prompt = "\n".join(lines)
    return user_prompt, system_prompt


def build_query_prompt(query: str) -> str:
    """Wrap a free-form query with an instruction to return JSON when applicable.

    Returns the prompt string directly.
    """
    return (
        "Answer the following question. "
        "If your answer can be represented as structured data, return it as JSON. "
        "Otherwise, answer in plain text.\n\n"
        f"Question: {query}"
    )
