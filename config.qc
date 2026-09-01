# QWM Yapilandirma Dosyasi (TOML sozdizimi)
# Bu dosyayi kaydettiginde QWM otomatik olarak algilar ve
# tum ayarlari (gap, animasyon, tus atamalari, picom) aninda uygular.

[general]
mod_key = "Mod4"
gaps_inner = 10
gaps_outer = 15
border_width = 2
border_radius = 14
border_active = "#89b4fa"
border_inactive = "#313244"
animations = true
animation_duration_ms = 180
animation_fps = 60

[apps]
terminal = "alacritty"
launcher = "rofi -show drun"
wallpaper_tool = "feh"
wallpaper_path = "~/.config/qwm/wallpaper.jpg"

[nvidia]
enable_optimizations = true
disable_vsync_for_games = true
force_composition_pipeline = false
power_mode = "prefer_maximum_performance"

[workspaces]
count = 10
names = ["1","2","3","4","5","6","7","8","9","10"]

[layout]
default = "master_stack"
master_ratio = 0.55

[keybindings]
terminal = "Mod4-Return"
launcher = "Mod4-d"
close_window = "Mod4-q"
quit_wm = "Mod4-Shift-e"
reload_config = "Mod4-Shift-r"
fullscreen = "Mod4-f"
toggle_floating = "Mod4-space"
focus_left = "Mod4-h"
focus_right = "Mod4-l"
focus_up = "Mod4-k"
focus_down = "Mod4-j"
move_left = "Mod4-Shift-h"
move_right = "Mod4-Shift-l"
move_up = "Mod4-Shift-k"
move_down = "Mod4-Shift-j"
screenshot_full = "Print"
lock_screen = ""
