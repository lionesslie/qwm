import struct
from Xlib import X, Xatom

SUPPORTED_ATOMS = [
    "_NET_SUPPORTED",
    "_NET_CLIENT_LIST",
    "_NET_CLIENT_LIST_STACKING",
    "_NET_NUMBER_OF_DESKTOPS",
    "_NET_DESKTOP_GEOMETRY",
    "_NET_DESKTOP_VIEWPORT",
    "_NET_CURRENT_DESKTOP",
    "_NET_DESKTOP_NAMES",
    "_NET_ACTIVE_WINDOW",
    "_NET_WORKAREA",
    "_NET_SUPPORTING_WM_CHECK",
    "_NET_WM_NAME",
    "_NET_WM_VISIBLE_NAME",
    "_NET_WM_DESKTOP",
    "_NET_WM_WINDOW_TYPE",
    "_NET_WM_WINDOW_TYPE_NORMAL",
    "_NET_WM_WINDOW_TYPE_DIALOG",
    "_NET_WM_WINDOW_TYPE_UTILITY",
    "_NET_WM_WINDOW_TYPE_TOOLBAR",
    "_NET_WM_WINDOW_TYPE_SPLASH",
    "_NET_WM_WINDOW_TYPE_DOCK",
    "_NET_WM_STATE",
    "_NET_WM_STATE_FULLSCREEN",
    "_NET_WM_STATE_MAXIMIZED_VERT",
    "_NET_WM_STATE_MAXIMIZED_HORZ",
    "_NET_WM_STATE_HIDDEN",
    "_NET_WM_STATE_DEMANDS_ATTENTION",
    "_NET_WM_STATE_ABOVE",
    "_NET_WM_ALLOWED_ACTIONS",
    "_NET_CLOSE_WINDOW",
    "_NET_MOVERESIZE_WINDOW",
    "_NET_WM_PID",
    "_NET_FRAME_EXTENTS",
    "WM_PROTOCOLS",
    "WM_DELETE_WINDOW",
    "WM_TAKE_FOCUS",
    "WM_STATE",
    "UTF8_STRING",
]


class EWMH:
    def __init__(self, display, root):
        self.display = display
        self.root = root
        self.atom = {}
        for name in SUPPORTED_ATOMS:
            self.atom[name] = display.intern_atom(name)
        self._check_win = None

    def get_atom(self, name):
        if name not in self.atom:
            self.atom[name] = self.display.intern_atom(name)
        return self.atom[name]

    def setup_supporting_wm_check(self, wm_name="qwm"):
        win = self.root.create_window(
            -100, -100, 1, 1, 0,
            X.CopyFromParent,
            X.InputOutput,
            X.CopyFromParent,
        )
        win.change_property(self.atom["_NET_WM_NAME"], self.atom["UTF8_STRING"], 8, wm_name.encode())
        win.change_property(self.atom["_NET_SUPPORTING_WM_CHECK"], Xatom.WINDOW, 32, [win.id])
        self.root.change_property(self.atom["_NET_SUPPORTING_WM_CHECK"], Xatom.WINDOW, 32, [win.id])
        self._check_win = win
        return win

    def set_supported(self):
        atoms = [self.atom[name] for name in SUPPORTED_ATOMS if name.startswith("_NET") or name.startswith("WM")]
        self.root.change_property(self.atom["_NET_SUPPORTED"], Xatom.ATOM, 32, atoms)

    def set_number_of_desktops(self, n):
        self.root.change_property(self.atom["_NET_NUMBER_OF_DESKTOPS"], Xatom.CARDINAL, 32, [n])

    def set_desktop_names(self, names):
        payload = b"\x00".join(n.encode() for n in names) + b"\x00"
        self.root.change_property(self.atom["_NET_DESKTOP_NAMES"], self.atom["UTF8_STRING"], 8, payload)

    def set_current_desktop(self, index):
        self.root.change_property(self.atom["_NET_CURRENT_DESKTOP"], Xatom.CARDINAL, 32, [index])

    def set_active_window(self, window_id):
        self.root.change_property(self.atom["_NET_ACTIVE_WINDOW"], Xatom.WINDOW, 32, [window_id])

    def set_client_list(self, window_ids):
        self.root.change_property(self.atom["_NET_CLIENT_LIST"], Xatom.WINDOW, 32, list(window_ids))
        self.root.change_property(self.atom["_NET_CLIENT_LIST_STACKING"], Xatom.WINDOW, 32, list(window_ids))

    def set_workarea(self, x, y, w, h, count):
        area = [x, y, w, h] * count
        self.root.change_property(self.atom["_NET_WORKAREA"], Xatom.CARDINAL, 32, area)

    def set_desktop_geometry(self, w, h):
        self.root.change_property(self.atom["_NET_DESKTOP_GEOMETRY"], Xatom.CARDINAL, 32, [w, h])

    def set_desktop_viewport(self):
        self.root.change_property(self.atom["_NET_DESKTOP_VIEWPORT"], Xatom.CARDINAL, 32, [0, 0])

    def set_wm_desktop(self, window, index):
        window.change_property(self.atom["_NET_WM_DESKTOP"], Xatom.CARDINAL, 32, [index])

    def get_wm_desktop(self, window):
        try:
            prop = window.get_full_property(self.atom["_NET_WM_DESKTOP"], Xatom.CARDINAL)
            if prop:
                return prop.value[0]
        except Exception:
            pass
        return None

    def get_window_type(self, window):
        try:
            prop = window.get_full_property(self.atom["_NET_WM_WINDOW_TYPE"], Xatom.ATOM)
            if prop:
                return list(prop.value)
        except Exception:
            pass
        return []

    def get_wm_state_atoms(self, window):
        try:
            prop = window.get_full_property(self.atom["_NET_WM_STATE"], Xatom.ATOM)
            if prop:
                return set(prop.value)
        except Exception:
            pass
        return set()

    def set_wm_state_atoms(self, window, atoms):
        window.change_property(self.atom["_NET_WM_STATE"], Xatom.ATOM, 32, list(atoms))

    def is_fullscreen(self, window):
        return self.atom["_NET_WM_STATE_FULLSCREEN"] in self.get_wm_state_atoms(window)

    def set_fullscreen(self, window, enabled):
        atoms = self.get_wm_state_atoms(window)
        fs = self.atom["_NET_WM_STATE_FULLSCREEN"]
        if enabled:
            atoms.add(fs)
        else:
            atoms.discard(fs)
        self.set_wm_state_atoms(window, atoms)

    def get_wm_name(self, window):
        try:
            prop = window.get_full_property(self.atom["_NET_WM_NAME"], self.atom["UTF8_STRING"])
            if prop and prop.value:
                return prop.value.decode("utf-8", "replace")
        except Exception:
            pass
        try:
            prop = window.get_full_property(Xatom.WM_NAME, Xatom.STRING)
            if prop and prop.value:
                return prop.value.decode("latin-1", "replace")
        except Exception:
            pass
        return ""

    def get_wm_class(self, window):
        try:
            prop = window.get_wm_class()
            if prop:
                return prop
        except Exception:
            pass
        return (None, None)

    def get_wm_protocols(self, window):
        try:
            prop = window.get_full_property(self.atom["WM_PROTOCOLS"], Xatom.ATOM)
            if prop:
                return set(prop.value)
        except Exception:
            pass
        return set()

    def send_delete_window(self, window):
        from Xlib.protocol import event
        protocols = self.get_wm_protocols(window)
        if self.atom["WM_DELETE_WINDOW"] in protocols:
            data = (32, [self.atom["WM_DELETE_WINDOW"], X.CurrentTime, 0, 0, 0])
            ev = event.ClientMessage(window=window, client_type=self.atom["WM_PROTOCOLS"], data=data)
            window.send_event(ev, event_mask=X.NoEventMask)
            self.display.flush()
            return True
        return False

    def send_take_focus(self, window):
        from Xlib.protocol import event
        protocols = self.get_wm_protocols(window)
        if self.atom["WM_TAKE_FOCUS"] in protocols:
            data = (32, [self.atom["WM_TAKE_FOCUS"], X.CurrentTime, 0, 0, 0])
            ev = event.ClientMessage(window=window, client_type=self.atom["WM_PROTOCOLS"], data=data)
            window.send_event(ev, event_mask=X.NoEventMask)

    def set_wm_pid(self, window, pid):
        window.change_property(self.atom["_NET_WM_PID"], Xatom.CARDINAL, 32, [pid])

    def get_wm_pid(self, window):
        try:
            prop = window.get_full_property(self.atom["_NET_WM_PID"], Xatom.CARDINAL)
            if prop:
                return prop.value[0]
        except Exception:
            pass
        return None

    def set_frame_extents(self, window, left, right, top, bottom):
        window.change_property(self.atom["_NET_FRAME_EXTENTS"], Xatom.CARDINAL, 32, [left, right, top, bottom])

    def is_transient(self, window):
        try:
            prop = window.get_full_property(Xatom.WM_TRANSIENT_FOR, Xatom.WINDOW)
            return bool(prop and prop.value)
        except Exception:
            return False

    def get_wm_normal_hints(self, window):
        try:
            return window.get_wm_normal_hints()
        except Exception:
            return None

    def get_wm_hints(self, window):
        try:
            return window.get_wm_hints()
        except Exception:
            return None
