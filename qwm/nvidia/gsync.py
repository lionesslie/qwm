import logging
from .settings import NvidiaSettings

logger = logging.getLogger("qwm.nvidia.gsync")

class GSyncController:
    """G-Sync / G-Sync Compatible control logic."""
    
    @staticmethod
    def enable_fullscreen_only(display: str = ":0"):
        """Enable G-Sync only for fullscreen applications."""
        logger.info("Enabling G-Sync (Fullscreen Only)")
        NvidiaSettings.set_attribute("AllowGSYNC", "1", display)
        
    @staticmethod
    def enable_always(display: str = ":0"):
        """Enable G-Sync for windowed and fullscreen applications."""
        logger.info("Enabling G-Sync (Always)")
        NvidiaSettings.set_attribute("AllowGSYNC", "2", display)
        NvidiaSettings.set_attribute("AllowGSYNCCompatible", "1", display)
        
    @staticmethod
    def disable(display: str = ":0"):
        """Disable G-Sync completely."""
        logger.info("Disabling G-Sync")
        NvidiaSettings.set_attribute("AllowGSYNC", "0", display)
        
    @staticmethod
    def disable_composition_pipeline(display: str = ":0"):
        """CRITICAL: ForceFullCompositionPipeline must be Off for G-Sync."""
        logger.info("Disabling ForceFullCompositionPipeline for G-Sync compatibility")
        attr = "CurrentMetaMode=nvidia-auto-select +0+0 { ForceFullCompositionPipeline=Off }"
        NvidiaSettings.set_attribute(attr, "", display)
        
    @staticmethod
    def enable_composition_pipeline(display: str = ":0"):
        """Re-enable to prevent tearing in desktop mode without G-Sync."""
        logger.info("Enabling ForceFullCompositionPipeline")
        attr = "CurrentMetaMode=nvidia-auto-select +0+0 { ForceFullCompositionPipeline=On }"
        NvidiaSettings.set_attribute(attr, "", display)
