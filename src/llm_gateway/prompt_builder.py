def build_decision_prompt(sensor_context: dict) -> tuple[str, str]:
    """Build system and user prompts for a sensor-driven decision.

    Returns:
        (user_prompt, system_prompt)
    """
    system_prompt = (
        "Sos el agente de seguridad de una casa inteligente (SmartHome equipo69).\n"
        "Tu tarea es analizar los datos de sensores y determinar el nivel de alerta.\n\n"
        "Niveles de alerta (elegí uno):\n"
        "- critico: gas > 1020 ppm o temperatura > 30 °C (emergencia, actuar YA)\n"
        "- alto: gas > 800 ppm o temperatura > 28 °C (riesgo significativo)\n"
        "- medio: gas > 400 ppm o ruido > 85 dB (precaución)\n"
        "- bajo: valores levemente fuera de rango\n"
        "- info: todo normal\n\n"
        "Herramientas disponibles para actuar:\n"
        "- activate_led_alerta(estado: bool)\n"
        "- send_notification(mensaje: str)\n"
        "- trigger_camera(duracion: int)\n"
        "- silence_alerts()\n\n"
        "Respondé SOLO con un JSON en este formato exacto:\n"
        '{"nivel": "critico|alto|medio|bajo|info", '
        '"razonamiento": "explicación en español del análisis y por qué este nivel", '
        '"acciones": [{"tool": "nombre", "args": {...}}], '
        '"confidence": 0.0-1.0}\n\n'
        "Reglas:\n"
        "- Si gas > 1020 o temp > 30, nivel DEBE ser 'critico' y confidence 1.0\n"
        "- Si no hay anomalías, nivel 'info', acciones vacías, confidence alta\n"
        "- El razonamiento DEBE mencionar los valores concretos de los sensores\n"
        "- No inventes herramientas que no existen"
    )

    lines = ["Estado actual de los sensores:"]
    for key, value in sensor_context.items():
        lines.append(f"- {key}: {value}")
    lines.append("\nDeterminá el nivel de alerta y las acciones necesarias.")

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
