import logging

logger = logging.getLogger("qwm.x11.window")

class Window:
    """Wrapper around an X11 Window object."""
    
    def __init__(self, display, xid: int):
        self.display = display
        self.xid = xid
        self.window = display.create_resource_object('window', xid)
        
    def map(self):
        self.window.map()
        
    def unmap(self):
        self.window.unmap()
        
    def configure(self, **kwargs):
        """Wrapper for configure window (geometry, border, etc.)"""
        self.window.configure(**kwargs)
