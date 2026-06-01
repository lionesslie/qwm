import sys
import logging

from .core.logger import setup_logger
from .core.config import ConfigManager
from .core.wm import WindowManager

class QWM:
    """Top-level QWM class (thin orchestrator)."""
    
    def __init__(self, reset_config: bool = False, debug: bool = False):
        self.logger = setup_logger(debug=debug)
        self.logger.info("Starting QWM initialization...")
        
        # Load and validate configuration
        self.config_manager = ConfigManager(reset=reset_config)
        self.config = self.config_manager.load()
        
        # Initialize core WM engine
        self.wm = WindowManager(self.config)
        
    def run(self):
        """Start the X11 event loop."""
        self.logger.info("Entering main event loop")
        self.wm.run()
