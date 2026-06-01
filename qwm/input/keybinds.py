import logging
from typing import Callable, Dict

logger = logging.getLogger("qwm.input.keybinds")

class KeybindRegistry:
    """Registry mapping key combinations to action callbacks."""
    def __init__(self):
        self.bindings: Dict[str, Callable] = {}
        
    def register(self, key_string: str, action: Callable):
        logger.debug(f"Registered keybind: {key_string}")
        self.bindings[key_string] = action
        
    def dispatch(self, key_string: str):
        if key_string in self.bindings:
            self.bindings[key_string]()
        else:
            logger.debug(f"No action bound to {key_string}")
