import shutil
import subprocess
import logging

from Xlib import X

logger = logging.getLogger("qwm.input.mouse")

BUTTON_LEFT = 1
BUTTON_MIDDLE = 2
BUTTON_RIGHT = 3


def _list_pointer_devices():
    if shutil.which("xinput") is None:
        return []
    try:
        out = subprocess.check_output(["xinput", "list", "--name-only"], timeout=5).decode()
    except Exception:
        return []
    devices = []
    for line in out.splitlines():
        name = line.strip()
        if not name or "keyboard" in name.lower() or "virtual core" in name.lower():
            continue
        devices.append(name)
    return devices


def _device_has_prop(device, prop_name):
    try:
        out = subprocess.check_output(["xinput", "list-props", device], timeout=5).decode()
        return prop_name in out
    except Exception:
        return False


def _set_prop(device, prop_name, values):
    try:
        subprocess.run(
            ["xinput", "set-prop", device, prop_name] + [str(v) for v in values],
            check=True, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning("xinput set-prop basarisiz: %s %s -> %s", device, prop_name,
                        exc.stderr.decode(errors="replace") if exc.stderr else exc)
        return False
    except Exception:
        logger.warning("xinput set-prop basarisiz: %s %s", device, prop_name, exc_info=True)
        return False


def apply_mouse_config(cfg):
    if shutil.which("xinput") is None:
        logger.warning("xinput bulunamadi, fare ayarlari atlaniyor")
        _apply_cursor_theme(cfg)
        return

    devices = _list_pointer_devices()
    if not devices:
        logger.warning("hicbir pointer aygiti bulunamadi")

    accel_profile_value = 0 if cfg.get("accel_profile", "adaptive") == "adaptive" else 1
    accel_speed = float(cfg.get("accel_speed", 0.0))
    natural_scroll = bool(cfg.get("natural_scroll", False))
    left_handed = bool(cfg.get("left_handed", False))

    for device in devices:
        if _device_has_prop(device, "libinput Accel Profile Enabled"):
            enabled = [0, 0]
            enabled[accel_profile_value] = 1
            _set_prop(device, "libinput Accel Profile Enabled", enabled)
        if _device_has_prop(device, "libinput Accel Speed"):
            _set_prop(device, "libinput Accel Speed", [accel_speed])
        if _device_has_prop(device, "libinput Natural Scrolling Enabled"):
            _set_prop(device, "libinput Natural Scrolling Enabled", [1 if natural_scroll else 0])
        if _device_has_prop(device, "libinput Left Handed Enabled"):
            _set_prop(device, "libinput Left Handed Enabled", [1 if left_handed else 0])

    logger.info("fare ayarlari uygulandi (%d aygit)", len(devices))
    _apply_cursor_theme(cfg)


def _apply_cursor_theme(cfg):
    import os
    theme = cfg.get("cursor_theme", "default")
    size = cfg.get("cursor_size", 24)
    os.environ["XCURSOR_THEME"] = theme
    os.environ["XCURSOR_SIZE"] = str(size)
    if shutil.which("xsetroot") is not None:
        try:
            subprocess.run(["xsetroot", "-cursor_name", "left_ptr"], check=False, timeout=5,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


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
