from Xlib import X

BUTTON_LEFT = 1
BUTTON_MIDDLE = 2
BUTTON_RIGHT = 3


class MouseController:
    def __init__(self, display, root, mod_mask, on_move_resize_done=None):
        self.display = display
        self.root = root
        self.mod_mask = mod_mask
        self.drag = None
        self.on_move_resize_done = on_move_resize_done

    def grab_buttons(self):
        for button in (BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT):
            self.root.grab_button(
                button, self.mod_mask, True,
                X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
                X.GrabModeAsync, X.GrabModeAsync,
                X.NONE, X.NONE,
            )

    def ungrab_buttons(self):
        for button in (BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT):
            self.root.ungrab_button(button, self.mod_mask)

    def begin_move(self, managed_window, pointer_x, pointer_y):
        self.drag = {
            "mode": "move",
            "window": managed_window,
            "start_px": pointer_x,
            "start_py": pointer_y,
            "orig_x": managed_window.geometry.x,
            "orig_y": managed_window.geometry.y,
        }

    def begin_resize(self, managed_window, pointer_x, pointer_y):
        self.drag = {
            "mode": "resize",
            "window": managed_window,
            "start_px": pointer_x,
            "start_py": pointer_y,
            "orig_w": managed_window.geometry.width,
            "orig_h": managed_window.geometry.height,
        }

    def motion(self, pointer_x, pointer_y):
        if not self.drag:
            return None
        win = self.drag["window"]
        dx = pointer_x - self.drag["start_px"]
        dy = pointer_y - self.drag["start_py"]
        if self.drag["mode"] == "move":
            new_x = self.drag["orig_x"] + dx
            new_y = self.drag["orig_y"] + dy
            win.geometry.x = new_x
            win.geometry.y = new_y
            win.window.configure(x=new_x, y=new_y)
            return ("move", win)
        else:
            new_w = max(50, self.drag["orig_w"] + dx)
            new_h = max(50, self.drag["orig_h"] + dy)
            win.geometry.width = new_w
            win.geometry.height = new_h
            win.window.configure(width=new_w, height=new_h)
            return ("resize", win)

    def end_drag(self):
        win = self.drag["window"] if self.drag else None
        self.drag = None
        if win and self.on_move_resize_done:
            self.on_move_resize_done(win)
