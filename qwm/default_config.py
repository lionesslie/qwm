"""
=======================================================================
 QWM - YAPILANDIRMA DOSYASI
=======================================================================
 Bu dosya saf Python'dur. Degistirdikten sonra pencere yoneticisini
 yeniden baslatmadan uygulamak icin: Super+Shift+R

 Dosya konumu: ~/.config/qwm/config.py
=======================================================================
"""
import os

# -----------------------------------------------------------------
# 1) GENEL AYARLAR
# -----------------------------------------------------------------
MOD_KEY = "super"          # Ana degistirici tus: "super", "alt", "ctrl"
TERMINAL = "alacritty"     # Super+Enter ile acilacak terminal
LAUNCHER = "rofi -show drun"   # Super+D ile acilacak uygulama baslatici
SCRATCHPAD_CMD = "alacritty --class qwm-scratchpad"  # Super+` ile acilir-kapanir terminal

WORKSPACE_COUNT = 9
FOCUS_FOLLOWS_MOUSE = True

# -----------------------------------------------------------------
# 2) GORUNUM
# -----------------------------------------------------------------
BORDER_WIDTH = 2
GAP_OUTER = 10
GAP_INNER = 8
MASTER_RATIO = 0.55
DEFAULT_LAYOUT = "tile"          # "tile" (master-stack) veya "monocle"

# Akilli bosluk/kenarlik: tek pencere kaldiginda gap ve border kaldirilir
# (bspwm'deki "smart gaps" ile ayni mantik; oyunlarda kenar bosluklarini
# gormek istemezsiniz).
SMART_GAPS = True
SMART_BORDERS = True

FOCUSED_BORDER_COLOR   = "#89b4fa"
UNFOCUSED_BORDER_COLOR = "#45475a"
URGENT_BORDER_COLOR    = "#f38ba8"

WALLPAPER = "~/.config/qwm/wallpaper.jpg"   # feh ile ayarlanir, dosya yoksa atlanir

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
# 4) OYUN MODU (Super+Shift+G ile acilir/kapanir)
# -----------------------------------------------------------------
# Oyun modu acikken: gap/border tamamen kaldirilir, fare-takip-odak
# devre disi kalir, fullscreen pencereler icin compositor bypass edilir,
# CPU governor "performance"a alinir ve compositor sureci "renice" ile
# geriye itilir. Bunlarin hepsi best-effort'tur; yetki/arac yoksa
# sessizce atlanir.
GAME_MODE_ENABLED = True
GAME_MODE_CPU_GOVERNOR = True
GAME_MODE_DEPRIORITIZE_COMPOSITOR = True

GAME_MODE_ENV_VARS = {
    "__GL_SYNC_TO_VBLANK": "0",
    "__GL_MaxFramesAllowed": "1",
    "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS": "0",
    "DXVK_HUD": "0",
}

# Oyun moduna girerken/cikarken calistirilacak komutlar (opsiyonel).
# Ornek: picom'u tamamen kapatip acmak icin.
GAME_MODE_ON_ENABLE = []
GAME_MODE_ON_DISABLE = []

# Bu siniflardan (WM_CLASS) biri acildiginda oyun modu otomatik devreye girer
# ve pencere kapaninca otomatik kapanir.
AUTO_GAME_MODE_ENABLED = True
AUTO_GAME_MODE_CLASSES = [
    "steam_app_", "steam_proton", "lutris", "gamescope",
    "retroarch", "heroic",
]

# -----------------------------------------------------------------
# 5) PENCERE KURALLARI (bspwm'deki "rules" karsiligi)
# -----------------------------------------------------------------
# WM_CLASS (instance veya class) icinde "class" alaninda gecen deger
# (kucuk/buyuk harf duyarsiz alt-dize eslesmesi) bulunursa kural uygulanir.
WINDOW_RULES = [
    {"class": "pavucontrol", "floating": True},
    {"class": "blueman-manager", "floating": True},
    {"class": "nm-connection-editor", "floating": True},
    {"class": "gimp", "floating": True},
    {"class": "mpv", "floating": True},
    {"class": "feh", "floating": True},
    {"class": "qwm-scratchpad", "floating": True},
]

# -----------------------------------------------------------------
# 6) OTOMATIK BASLATILACAK PROGRAMLAR
# -----------------------------------------------------------------
AUTOSTART = [
    # "picom --backend glx --vsync",
]
_wallpaper_path = os.path.expanduser(WALLPAPER)
if os.path.isfile(_wallpaper_path):
    AUTOSTART.append(f'feh --bg-fill "{_wallpaper_path}"')

# -----------------------------------------------------------------
# 7) KLAVYE (VM ortamlarinda "yapisan tus" hissini azaltir)
# -----------------------------------------------------------------
KEYBOARD_REPEAT_DELAY = 250
KEYBOARD_REPEAT_RATE = 35

# -----------------------------------------------------------------
# 8) TUS ATAMALARI (keybindings)
# -----------------------------------------------------------------
# Format:  "mod-tus": ("eylem_adi", parametre)
# Kullanilabilecek modifikatorler: super, alt, ctrl, shift (birlestirilebilir: super-shift-1)
KEYBINDINGS = {
    f"{MOD_KEY}-Return":       ("spawn", TERMINAL),
    f"{MOD_KEY}-d":            ("spawn", LAUNCHER),
    f"{MOD_KEY}-q":            ("kill_window", None),

    # Odak / gezinme
    f"{MOD_KEY}-j":            ("focus_next", None),
    f"{MOD_KEY}-k":            ("focus_prev", None),
    f"{MOD_KEY}-shift-j":      ("move_window_next", None),
    f"{MOD_KEY}-shift-k":      ("move_window_prev", None),

    # Boyutlandirma
    f"{MOD_KEY}-h":            ("resize_master", -0.05),
    f"{MOD_KEY}-l":            ("resize_master", 0.05),

    # Pencere durumu
    f"{MOD_KEY}-f":            ("toggle_fullscreen", None),
    f"{MOD_KEY}-space":        ("toggle_floating", None),
    f"{MOD_KEY}-shift-c":      ("center_floating", None),
    f"{MOD_KEY}-equal":        ("grow_floating", None),
    f"{MOD_KEY}-minus":        ("shrink_floating", None),
    f"{MOD_KEY}-shift-Return": ("swap_master", None),

    # Duzen (layout)
    f"{MOD_KEY}-t":            ("cycle_layout", None),
    f"{MOD_KEY}-m":            ("toggle_monocle", None),
    f"{MOD_KEY}-shift-g":      ("toggle_gaps", None),

    # Yardimci pencereler
    f"{MOD_KEY}-grave":        ("toggle_scratchpad", SCRATCHPAD_CMD),

    # Oyun modu
    f"{MOD_KEY}-g":            ("toggle_game_mode", None),

    # Sistem
    f"{MOD_KEY}-shift-q":      ("quit_wm", None),
    f"{MOD_KEY}-shift-r":      ("reload_config", None),
}

# Calisma alani gecis kisayollari (Super+1..9 ve Super+Shift+1..9) otomatik eklenir
for i in range(1, WORKSPACE_COUNT + 1):
    KEYBINDINGS[f"{MOD_KEY}-{i}"] = ("switch_workspace", i - 1)
    KEYBINDINGS[f"{MOD_KEY}-shift-{i}"] = ("move_to_workspace", i - 1)

# -----------------------------------------------------------------
# 9) FARE KISAYOLLARI (sabit, degistirilemez ama burada belgeli)
# -----------------------------------------------------------------
#   Super + Sol Tik (surukle)  -> Pencereyi tasi (floating yapar)
#   Super + Sag Tik (surukle)  -> Pencereyi yeniden boyutlandir
