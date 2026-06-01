import enum
import logging
from .settings import NvidiaSettings

logger = logging.getLogger("qwm.nvidia.powermizer")

class PowerMizerMode(enum.Enum):
    AUTO = 0
    ADAPTIVE = 1
    MAX_PERF = 2

class PowerMizerController:
    """Controls NVIDIA PowerMizer modes for performance and power saving."""
    
    @staticmethod
    def set_mode(mode: PowerMizerMode, display: str = ":0"):
        logger.info(f"Setting PowerMizer mode to {mode.name} ({mode.value})")
        NvidiaSettings.set_attribute("GPUPowerMizerMode", str(mode.value), display)
