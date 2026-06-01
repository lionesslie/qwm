import logging
import Xlib.display
import Xlib.X
import Xlib.error

logger = logging.getLogger("qwm.x11.display")

class XDisplay:
    """Wrapper for the X server connection and root window."""
    
    def __init__(self):
        try:
            self.display = Xlib.display.Display()
            self.screen = self.display.screen()
            self.root = self.screen.root
            logger.info(f"Connected to X Display: {self.display.get_display_name()}")
        except Xlib.error.DisplayConnectionError as e:
            logger.critical(f"Failed to connect to X display: {e}")
            raise
            
    def setup(self):
        """Initialize root window properties and event masks."""
        # Request SubstructureRedirectMask so we can manage windows
        try:
            self.root.change_attributes(
                event_mask=(
                    Xlib.X.SubstructureRedirectMask |
                    Xlib.X.SubstructureNotifyMask |
                    Xlib.X.EnterWindowMask |
                    Xlib.X.LeaveWindowMask |
                    Xlib.X.StructureNotifyMask |
                    Xlib.X.PropertyChangeMask
                )
            )
            self.display.sync()
        except Xlib.error.BadAccess:
            logger.critical("Another window manager is already running!")
            raise RuntimeError("Another WM is running.")
            
    def next_event(self):
        """Fetch the next X11 event."""
        try:
            return self.display.next_event()
        except Exception as e:
            logger.error(f"Error reading event: {e}")
            return None
            
    def cleanup(self):
        """Close connection."""
        self.display.close()
