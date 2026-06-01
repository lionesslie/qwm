import logging

logger = logging.getLogger("qwm.x11.atoms")

class AtomCache:
    """Cache for X11 atoms (EWMH, ICCCM, NV-specific)."""
    
    def __init__(self, display):
        self.display = display
        self._cache = {}
        
    def get(self, name: str) -> int:
        if name not in self._cache:
            self._cache[name] = self.display.intern_atom(name)
        return self._cache[name]
        
    def setup_ewmh(self):
        """Intern commonly used EWMH atoms ahead of time."""
        atoms = [
            "_NET_SUPPORTED",
            "_NET_SUPPORTING_WM_CHECK",
            "_NET_WM_NAME",
            "_NET_WM_STATE",
            "_NET_WM_STATE_FULLSCREEN",
            "_NET_WM_WINDOW_TYPE",
            "_NET_WM_WINDOW_TYPE_DOCK",
            "_NET_WM_WINDOW_TYPE_DESKTOP",
            "_NET_ACTIVE_WINDOW",
        ]
        for atom in atoms:
            self.get(atom)
