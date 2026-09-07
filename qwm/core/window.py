from dataclasses import dataclass, field


@dataclass
class Geometry:
    x: int = 0
    y: int = 0
    width: int = 640
    height: int = 480

    def as_tuple(self):
        return (self.x, self.y, self.width, self.height)


class ManagedWindow:
    def __init__(self, window, wid, wm_class="", wm_name="", pid=None):
        self.window = window
        self.id = wid
        self.wm_class = wm_class
        self.wm_name = wm_name
        self.pid = pid

        self.workspace = 0
        self.floating = False
        self.fullscreen = False
        self.hidden = False
        self.urgent = False
        self.mapped = False

        self.geometry = Geometry()
        self.float_geometry = Geometry()
        self.saved_geometry = None

        self.border_width = 2
        self.focused = False

        self.min_width = 1
        self.min_height = 1
        self.max_width = 1 << 20
        self.max_height = 1 << 20

    def apply_size_hints(self, width, height):
        width = max(self.min_width, min(width, self.max_width))
        height = max(self.min_height, min(height, self.max_height))
        return width, height

    def matches_rule(self, rule):
        cls_match = True
        name_match = True
        if "class" in rule:
            cls_match = rule["class"].lower() in (self.wm_class or "").lower()
        if "name" in rule:
            name_match = rule["name"].lower() in (self.wm_name or "").lower()
        return cls_match and name_match

    def __repr__(self):
        return f"<ManagedWindow id={self.id:#x} class={self.wm_class!r} ws={self.workspace}>"
