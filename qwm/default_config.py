"""
=======================================================================
 QWM - YAPILANDIRMA DOSYASI
=======================================================================
 Bu dosya saf Python'dur. Degistirdikten sonra pencere yoneticisini
 yeniden baslatmadan uygulamak icin: Super+Shift+R

 Dosya konumu: ~/.config/qwm/config.py
=======================================================================
"""

# -----------------------------------------------------------------
# 1) GENEL AYARLAR
# -----------------------------------------------------------------
MOD_KEY = "super"
TERMINAL = "xterm"
LAUNCHER = "dmenu_run"

WORKSPACE_COUNT = 9
FOCUS_FOLLOWS_MOUSE = True

# -----------------------------------------------------------------
# 2) GORUNUM
# -----------------------------------------------------------------
BORDER_WIDTH = 2
GAP_OUTER = 10
GAP_INNER = 8
MASTER_RATIO = 0.55

FOCUSED_BORDER_COLOR   = "#89b4fa"
UNFOCUSED_BORDER_COLOR = "#45475a"

# -----------------------------------------------------------------
# 3) NVIDIA OPTIMIZASYONLARI
# -----------------------------------------------------------------
NVIDIA_OPTIMIZATIONS_ENABLED = True
NVIDIA_FORCE_COMPOSITION_PIPELINE = True

NVIDIA_ENV_VARS = {
    "__GL_YIELD": "USLEEP",
    "__GL_MaxFramesAllowed": "1",
    "__GL_SYNC_TO_VBLANK": "0",
    "__GL_THREADED_OPTIMIZATIONS": "1",
}

# -----------------------------------------------------------------
# 4) OTOMATIK BASLATILACAK PROGRAMLAR
# -----------------------------------------------------------------
AUTOSTART = [
    # "picom --backend glx --vsync",   # Compositor istersen ac
    # "nitrogen --restore",             # Duvar kagidi
]

# -----------------------------------------------------------------
# 5) TUS ATAMALARI
# -----------------------------------------------------------------
KEYBINDINGS = {
    f"{MOD_KEY}-Return":       ("spawn", TERMINAL),
    f"{MOD_KEY}-d":            ("spawn", LAUNCHER),
    f"{MOD_KEY}-q":            ("kill_window", None),
    f"{MOD_KEY}-j":            ("focus_next", None),
    f"{MOD_KEY}-k":            ("focus_prev", None),
    f"{MOD_KEY}-h":            ("resize_master", -0.05),
    f"{MOD_KEY}-l":            ("resize_master", 0.05),
    f"{MOD_KEY}-f":            ("toggle_fullscreen", None),
    f"{MOD_KEY}-space":        ("toggle_floating", None),
    f"{MOD_KEY}-shift-Return": ("swap_master", None),
    f"{MOD_KEY}-shift-q":      ("quit_wm", None),
    f"{MOD_KEY}-shift-r":      ("reload_config", None),
}

for i in range(1, WORKSPACE_COUNT + 1):
    KEYBINDINGS[f"{MOD_KEY}-{i}"] = ("switch_workspace", i - 1)
    KEYBINDINGS[f"{MOD_KEY}-shift-{i}"] = ("move_to_workspace", i - 1)

# -----------------------------------------------------------------
# 6) FARE KISAYOLLARI (sabit)
# -----------------------------------------------------------------
#   Super + Sol Tik (surukle)  -> Pencereyi tasi (floating yapar)
#   Super + Sag Tik (surukle)  -> Yeniden boyutlandir