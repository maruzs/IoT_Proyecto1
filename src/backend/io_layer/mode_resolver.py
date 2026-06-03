import os
from typing import Callable
from .video_source import VideoSource
from .command_output import CommandOutput
from .local_video import LocalVideoSource
from .local_output import LocalCommandOutput
from .mqtt_video import MQTTVideoSource
from .mqtt_output import MQTTCommandOutput


def resolve_mode(
    publish_func: Callable[[str, str], None] | None = None,
) -> tuple[VideoSource, CommandOutput]:
    """Return the (VideoSource, CommandOutput) pair for the current runtime mode.

    The ``MODE`` environment variable selects the strategy:
    * ``DEV_LOCAL``  → local webcam + console/cv2 output
    * ``PROD_MQTT``  → HTTP stream input + MQTT output
    """
    mode = os.environ.get("MODE", "DEV_LOCAL")
    if mode == "PROD_MQTT":
        if publish_func is None:
            raise ValueError("PROD_MQTT mode requires a publish_func")
        return (MQTTVideoSource(), MQTTCommandOutput(publish_func))
    if mode == "DEV_LOCAL":
        return (LocalVideoSource(), LocalCommandOutput())
    raise ValueError(f"Unknown MODE: {mode}")
