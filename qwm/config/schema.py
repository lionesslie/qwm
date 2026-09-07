class ConfigError(Exception):
    def __init__(self, message, line=None):
        self.line = line
        if line is not None:
            message = f"config.qc:{line}: {message}"
        super().__init__(message)


DEFAULTS = {
    "general": {
        "mod_key": "super",
        "gap_inner": 10,
        "gap_outer": 15,
        "border_width": 2,
        "border_radius": 12,
        "focus_follows_mouse": True,
        "default_layout": "master_stack",
        "master_ratio": 0.55,
    },
    "colors": {
        "border_active": "#89b4fa",
        "border_inactive": "#45475a",
        "background": "#1e1e2e",
    },
    "animations": {
        "enabled": True,
        "duration_ms": 180,
        "easing": "ease_out_cubic",
        "workspace_slide": True,
        "fps": 60,
    },
    "compositor": {
        "enabled": True,
        "backend": "glx",
        "vsync": True,
        "blur": True,
        "shadow": True,
        "corner_radius": 12,
        "glx_no_stencil": True,
        "glx_no_rebind_pixmap": True,
    },
    "nvidia": {
        "auto_optimize": True,
        "force_composition_pipeline": True,
        "triple_buffer": True,
    },
    "gamemode": {
        "enabled": True,
        "auto_detect": True,
        "unredirect_fullscreen": True,
        "disable_animations_on_game": True,
    },
    "apps": {
        "terminal": "alacritty",
        "launcher": "rofi -show drun",
        "wallpaper_tool": "feh",
        "wallpaper_path": "~/.config/qwm/wallpaper.jpg",
    },
    "workspaces": {
        "count": 9,
        "names": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    },
    "autostart": {},
    "rules": [],
    "monitors": [],
    "mouse": {
        "accel_profile": "adaptive",
        "accel_speed": 0.0,
        "natural_scroll": False,
        "left_handed": False,
        "scroll_speed": 1.0,
        "cursor_theme": "default",
        "cursor_size": 24,
    },
    "keyboard": {
        "layout": "us",
        "variant": "",
        "model": "pc105",
        "options": "",
        "repeat_delay_ms": 300,
        "repeat_rate": 30,
        "numlock_on_start": False,
    },
    "system_autologin": {
        "enabled": False,
        "method": "display_manager",
        "target_user": "",
        "tty": 1,
    },
    "keybinds": {
        "terminal": "super+return",
        "launcher": "super+d",
        "close_window": "super+q",
        "fullscreen": "super+f",
        "toggle_floating": "super+shift+space",
        "focus_left": "super+h",
        "focus_right": "super+l",
        "focus_up": "super+k",
        "focus_down": "super+j",
        "move_left": "super+shift+h",
        "move_right": "super+shift+l",
        "move_up": "super+shift+k",
        "move_down": "super+shift+j",
        "resize_grow": "super+equal",
        "resize_shrink": "super+minus",
        "workspace_1": "super+1",
        "workspace_2": "super+2",
        "workspace_3": "super+3",
        "workspace_4": "super+4",
        "workspace_5": "super+5",
        "workspace_6": "super+6",
        "workspace_7": "super+7",
        "workspace_8": "super+8",
        "workspace_9": "super+9",
        "move_to_workspace_1": "super+shift+1",
        "move_to_workspace_2": "super+shift+2",
        "move_to_workspace_3": "super+shift+3",
        "move_to_workspace_4": "super+shift+4",
        "move_to_workspace_5": "super+shift+5",
        "move_to_workspace_6": "super+shift+6",
        "move_to_workspace_7": "super+shift+7",
        "move_to_workspace_8": "super+shift+8",
        "move_to_workspace_9": "super+shift+9",
        "reload_config": "super+shift+r",
        "quit_wm": "super+shift+q",
        "screenshot": "super+shift+s",
        "lock_screen": "super+l",
        "scratchpad": "super+grave",
        "cycle_layout": "super+space",
    },
}

VALID_LAYOUTS = {"master_stack", "grid", "spiral", "monocle", "floating"}
VALID_EASINGS = {"linear", "ease_out_cubic", "ease_in_cubic", "ease_in_out_cubic"}

_TYPE_MAP = {
    "gap_inner": int, "gap_outer": int, "border_width": int, "border_radius": int,
    "master_ratio": float, "duration_ms": int, "fps": int, "corner_radius": int,
    "count": int, "focus_follows_mouse": bool, "enabled": bool, "vsync": bool,
    "blur": bool, "shadow": bool, "glx_no_stencil": bool, "glx_no_rebind_pixmap": bool,
    "auto_optimize": bool, "force_composition_pipeline": bool, "triple_buffer": bool,
    "auto_detect": bool, "unredirect_fullscreen": bool, "disable_animations_on_game": bool,
    "workspace_slide": bool, "accel_speed": float, "natural_scroll": bool,
    "left_handed": bool, "scroll_speed": float, "cursor_size": int,
    "repeat_delay_ms": int, "repeat_rate": int, "numlock_on_start": bool,
    "tty": int,
}

VALID_ACCEL_PROFILES = {"adaptive", "flat"}
VALID_AUTOLOGIN_METHODS = {"display_manager", "tty"}


def _merge_section(defaults, user, section_name):
    merged = dict(defaults)
    if not isinstance(user, dict):
        raise ConfigError(f"[{section_name}] bir tablo olmalı")
    for key, value in user.items():
        merged[key] = value
    return merged


def validate_and_merge(user_config):
    if not isinstance(user_config, dict):
        raise ConfigError("config.qc kök seviyesinde tablolar bekleniyor")

    result = {}
    for section, defaults in DEFAULTS.items():
        user_section = user_config.get(section, {})
        if isinstance(defaults, dict):
            result[section] = _merge_section(defaults, user_section, section)
        else:
            result[section] = user_section if section in user_config else defaults

    for key, expected in _TYPE_MAP.items():
        for section in result.values():
            if isinstance(section, dict) and key in section:
                val = section[key]
                if expected is bool and not isinstance(val, bool):
                    raise ConfigError(f"'{key}' alanı boolean (true/false) olmalı, alınan: {val!r}")
                if expected is int and not isinstance(val, int):
                    raise ConfigError(f"'{key}' alanı tam sayı olmalı, alınan: {val!r}")
                if expected is float and not isinstance(val, (int, float)):
                    raise ConfigError(f"'{key}' alanı sayı olmalı, alınan: {val!r}")

    layout = result["general"].get("default_layout")
    if layout not in VALID_LAYOUTS:
        raise ConfigError(f"geçersiz default_layout: {layout!r}, geçerli değerler: {sorted(VALID_LAYOUTS)}")

    easing = result["animations"].get("easing")
    if easing not in VALID_EASINGS:
        raise ConfigError(f"geçersiz easing: {easing!r}, geçerli değerler: {sorted(VALID_EASINGS)}")

    ws = result["workspaces"]
    if ws["count"] < 1 or ws["count"] > 36:
        raise ConfigError("workspaces.count 1-36 aralığında olmalı")
    if len(ws.get("names", [])) < ws["count"]:
        ws["names"] = list(ws.get("names", [])) + [str(i + 1) for i in range(len(ws.get("names", [])), ws["count"])]

    for key, val in result["keybinds"].items():
        if not isinstance(val, str) or "+" not in val and len(val) == 0:
            raise ConfigError(f"keybinds.{key} geçersiz kısayol: {val!r}")

    if "rules" in user_config:
        rules = user_config["rules"]
        if not isinstance(rules, list):
            raise ConfigError("[[rules]] bir dizi tablo olmalı")
        result["rules"] = rules

    if "monitors" in user_config:
        monitors = user_config["monitors"]
        if not isinstance(monitors, list):
            raise ConfigError("[[monitors]] bir dizi tablo olmalı")
        for entry in monitors:
            if not isinstance(entry, dict) or "name" not in entry:
                raise ConfigError("her [[monitors]] girdisi 'name' alanı icermeli")
        result["monitors"] = monitors

    accel_profile = result["mouse"].get("accel_profile")
    if accel_profile not in VALID_ACCEL_PROFILES:
        raise ConfigError(f"gecersiz mouse.accel_profile: {accel_profile!r}, gecerli degerler: {sorted(VALID_ACCEL_PROFILES)}")
    accel_speed = result["mouse"].get("accel_speed")
    if not (-1.0 <= float(accel_speed) <= 1.0):
        raise ConfigError("mouse.accel_speed -1.0 ile 1.0 arasinda olmali")

    autologin_method = result["system_autologin"].get("method")
    if autologin_method not in VALID_AUTOLOGIN_METHODS:
        raise ConfigError(f"gecersiz system_autologin.method: {autologin_method!r}, gecerli degerler: {sorted(VALID_AUTOLOGIN_METHODS)}")

    if "autostart" in user_config:
        result["autostart"] = user_config["autostart"]

    return result
