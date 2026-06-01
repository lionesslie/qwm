import os
import logging

logger = logging.getLogger("qwm.nvidia.glx")

class GLXEnvironment:
    """Manage environment variables for OpenGL/GLX optimization."""
    
    @staticmethod
    def set_desktop_mode():
        """Environment settings to prevent tearing on desktop."""
        logger.info("Setting GLX environment for Desktop Mode")
        os.environ["__GL_SYNC_TO_VBLANK"] = "1"
        os.environ["__GL_MaxFramesAllowed"] = "2"
        # Clear game mode specific vars if set
        os.environ.pop("__GL_YIELD", None)
        
    @staticmethod
    def set_game_mode():
        """Environment settings for maximum gaming performance and low latency."""
        logger.info("Setting GLX environment for Game Mode")
        os.environ["__GL_SYNC_TO_VBLANK"] = "0"
        os.environ["__GL_MaxFramesAllowed"] = "1"
        os.environ["__GL_YIELD"] = "NOTHING"
        os.environ["__GL_THREADED_OPTIMIZATIONS"] = "1"
        
        # Proton/Wine DXVK enhancements
        os.environ["PROTON_ENABLE_NVAPI"] = "1"
        os.environ["DXVK_NVAPI_ENABLE"] = "1"
        os.environ["VKD3D_CONFIG"] = "dxr"
