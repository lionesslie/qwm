import logging
import Xlib.X as X
import Xlib.XK as XK
from typing import Callable, Dict, Tuple

logger = logging.getLogger("qwm.input.keybinds")

MODIFIERS = {
    "Shift": X.ShiftMask,
    "Lock": X.LockMask,
    "Control": X.ControlMask,
    "Mod1": X.Mod1Mask,  # Alt
    "Mod2": X.Mod2Mask,  # NumLock vs
    "Mod3": X.Mod3Mask,
    "Mod4": X.Mod4Mask,  # Super / Windows tuşu
    "Mod5": X.Mod5Mask,
}

class KeybindRegistry:
    """Registry mapping key combinations to action callbacks."""
    def __init__(self, display):
        self.display = display
        self.root = display.root
        # (keycode, modifier) -> callback
        self.bindings: Dict[Tuple[int, int], Callable] = {}
        
    def _parse_key_string(self, key_string: str) -> Tuple[int, int]:
        parts = key_string.split("-")
        key_name = parts[-1]
        mod_mask = 0
        
        for mod in parts[:-1]:
            if mod in MODIFIERS:
                mod_mask |= MODIFIERS[mod]
                
        keysym = XK.string_to_keysym(key_name)
        if keysym == XK.NoSymbol:
            logger.error(f"Bilinmeyen tuş: {key_name}")
            return 0, 0
            
        keycode = self.display.display.keysym_to_keycode(keysym)
        return keycode, mod_mask

    def register(self, key_string: str, action: Callable):
        keycode, mod_mask = self._parse_key_string(key_string)
        if keycode == 0:
            return
            
        logger.debug(f"Kısayol kaydedildi: {key_string} (code:{keycode}, mod:{mod_mask})")
        self.bindings[(keycode, mod_mask)] = action
        
        # X11'de tuşu yakala (grab)
        # NumLock (Mod2) açık/kapalı durumlarını da desteklemek için varyasyonları yakalamak iyi olur ama şimdilik basitleştirelim
        self.root.grab_key(
            keycode,
            mod_mask,
            1, # owner_events
            X.GrabModeAsync,
            X.GrabModeAsync
        )

    def dispatch(self, event):
        """X11 KeyPress eventini ilgili action'a yönlendir."""
        # state içinden sadece kullandığımız modifierları filtrele (NumLock vs yok say)
        mask = event.state & (X.ShiftMask | X.ControlMask | X.Mod1Mask | X.Mod4Mask)
        
        key = (event.detail, mask)
        if key in self.bindings:
            try:
                self.bindings[key]()
            except Exception as e:
                logger.error(f"Kısayol eylemi sırasında hata: {e}")
        else:
            logger.debug(f"Kayıtlı olmayan tuş basıldı: code={event.detail}, mask={mask}")
