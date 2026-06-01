import logging
from typing import Any, Dict

from .state import QWMState
from ..x11.display import XDisplay

logger = logging.getLogger("qwm.wm")

class WindowManager:
    """Central WM engine and event dispatcher."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = QWMState()
        self.display = XDisplay()
        
    def setup(self):
        """Perform initial setup before entering the event loop."""
        logger.info("Setting up XDisplay")
        self.display.setup()
        
    def run(self):
        """Main event loop."""
        self.setup()
        
        logger.info("Starting X11 event loop")
        while self.state.running:
            # Event loop using python-xlib
            event = self.display.next_event()
            if event:
                self.handle_event(event)
                
    def handle_event(self, event):
        """Dispatch X11 events to appropriate handlers."""
        # TODO: Route events to input, layout, or window management handlers
        pass
        
    def cleanup(self):
        """Clean up resources before exit."""
        logger.info("Cleaning up QWM resources")
        self.display.cleanup()
