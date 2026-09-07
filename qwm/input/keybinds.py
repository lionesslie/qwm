import logging
from Xlib import X, XK

logger = logging.getLogger("qwm.input.keybinds")

MODIFIER_MAP = {
    "super": X.Mod4Mask,
    "mod4": X.Mod4Mask,
    "win": X.Mod4Mask,
    "alt": X.Mod1Mask,
    "mod1": X.Mod1Mask,
    "shift": X.ShiftMask,
    "ctrl": X.ControlMask,
    "control": X.ControlMask,
}

IGNORED_MODIFIERS = [0, X.LockMask, X.Mod2Mask, X.LockMask | X.Mod2Mask]


def parse_keybind_string(spec):
    parts = spec.lower().split("+")
    key = parts[-1]
    mods = 0
    for part in parts[:-1]:
        if part not in MODIFIER_MAP:
            raise ValueError(f"bilinmeyen modifier: {part!r} (kısayol: {spec!r})")
        mods |= MODIFIER_MAP[part]
    return mods, key


class KeybindManager:
    def __init__(self, display, root, on_trigger):
        self.display = display
        self.root = root
        self.on_trigger = on_trigger
        self.bindings = {}

    def _keysym_for(self, key_name):
        if len(key_name) == 1:
            keysym = XK.string_to_keysym(key_name)
            if keysym == 0:
                keysym = XK.string_to_keysym(key_name.upper())
        else:
            aliases = {
                "grave": "grave",
                "return": "Return",
                "enter": "Return",
                "space": "space",
                "equal": "equal",
                "minus": "minus",
                "escape": "Escape",
                "tab": "Tab",
            }
            keysym = XK.string_to_keysym(aliases.get(key_name, key_name))
        return keysym

    def grab_all(self, keybind_config):
        self.ungrab_all()
        self.bindings = {}
        for action, spec in keybind_config.items():
            try:
                mods, key_name = parse_keybind_string(spec)
            except ValueError as exc:
                logger.error("kısayol atlanıyor: %s", exc)
                continue
            keysym = self._keysym_for(key_name)
            if keysym == 0:
                logger.error("bilinmeyen tuş: %r (%s)", key_name, action)
                continue
            keycode = self.display.keysym_to_keycode(keysym)
            if keycode == 0:
                logger.error("keycode bulunamadı: %r (%s)", key_name, action)
                continue
            self.bindings[(mods, keycode)] = action
            for ignored in IGNORED_MODIFIERS:
                self.root.grab_key(
                    keycode, mods | ignored, True,
                    X.GrabModeAsync, X.GrabModeAsync,
                )
        self.display.sync()
        logger.info("%d kısayol bağlandı", len(self.bindings))

    def ungrab_all(self):
        try:
            self.root.ungrab_key(X.AnyKey, X.AnyModifier)
            self.display.sync()
        except Exception:
            pass

    def dispatch(self, event):
        clean_state = event.state & ~(X.LockMask | X.Mod2Mask)
        action = self.bindings.get((clean_state, event.detail))
        if action:
            self.on_trigger(action)
            return True
        return False
