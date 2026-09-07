from Xlib import X

EVENT_NAMES = {
    X.KeyPress: "KeyPress",
    X.KeyRelease: "KeyRelease",
    X.ButtonPress: "ButtonPress",
    X.ButtonRelease: "ButtonRelease",
    X.MotionNotify: "MotionNotify",
    X.EnterNotify: "EnterNotify",
    X.LeaveNotify: "LeaveNotify",
    X.FocusIn: "FocusIn",
    X.FocusOut: "FocusOut",
    X.MapRequest: "MapRequest",
    X.MapNotify: "MapNotify",
    X.UnmapNotify: "UnmapNotify",
    X.DestroyNotify: "DestroyNotify",
    X.ConfigureRequest: "ConfigureRequest",
    X.ConfigureNotify: "ConfigureNotify",
    X.ClientMessage: "ClientMessage",
    X.PropertyNotify: "PropertyNotify",
}


class EventDispatcher:
    def __init__(self):
        self._handlers = {}

    def register(self, event_type, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    def dispatch(self, event):
        handlers = self._handlers.get(event.type)
        if not handlers:
            return
        for handler in handlers:
            handler(event)
