[general]
mod_key = "super"
gap_inner = 10
gap_outer = 15
border_width = 2
border_radius = 12
focus_follows_mouse = true
default_layout = "master_stack"
master_ratio = 0.55

[colors]
border_active = "#89b4fa"
border_inactive = "#45475a"
background = "#1e1e2e"

[animations]
enabled = true
duration_ms = 180
easing = "ease_out_cubic"
workspace_slide = true
fps = 60

[compositor]
enabled = true
backend = "glx"
vsync = true
blur = true
shadow = true
corner_radius = 12
glx_no_stencil = true
glx_no_rebind_pixmap = true

[nvidia]
auto_optimize = true
force_composition_pipeline = true
triple_buffer = true

[gamemode]
enabled = true
auto_detect = true
unredirect_fullscreen = true
disable_animations_on_game = true

[apps]
terminal = "alacritty"
launcher = "rofi -show drun"
wallpaper_tool = "feh"
wallpaper_path = "~/.config/qwm/wallpaper.jpg"

[workspaces]
count = 9
names = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

[mouse]
accel_profile = "adaptive"
accel_speed = 0.0
natural_scroll = false
left_handed = false
scroll_speed = 1.0
cursor_theme = "default"
cursor_size = 24

[keyboard]
layout = "tr"
variant = ""
model = "pc105"
options = ""
repeat_delay_ms = 300
repeat_rate = 30
numlock_on_start = true

[system_autologin]
enabled = false
method = "display_manager"
target_user = ""
tty = 1

[autostart]
polybar = "~/.config/polybar/launch.sh"

[[monitors]]
name = "eDP-1"
resolution = "1920x1080"
refresh_rate = 60
position = "0x0"
primary = true

# [[monitors]]
# name = "HDMI-1"
# resolution = "1920x1080"
# refresh_rate = 144
# position = "1920x0"
# primary = false

[[rules]]
class = "Rofi"
floating = true

[[rules]]
class = "qwm-scratchpad"
floating = true

[keybinds]
terminal = "super+return"
launcher = "super+d"
close_window = "super+q"
fullscreen = "super+f"
toggle_floating = "super+shift+space"
cycle_layout = "super+space"
focus_left = "super+h"
focus_right = "super+l"
focus_up = "super+k"
focus_down = "super+j"
move_left = "super+shift+h"
move_right = "super+shift+l"
move_up = "super+shift+k"
move_down = "super+shift+j"
resize_grow = "super+equal"
resize_shrink = "super+minus"
workspace_1 = "super+1"
workspace_2 = "super+2"
workspace_3 = "super+3"
workspace_4 = "super+4"
workspace_5 = "super+5"
workspace_6 = "super+6"
workspace_7 = "super+7"
workspace_8 = "super+8"
workspace_9 = "super+9"
move_to_workspace_1 = "super+shift+1"
move_to_workspace_2 = "super+shift+2"
move_to_workspace_3 = "super+shift+3"
move_to_workspace_4 = "super+shift+4"
move_to_workspace_5 = "super+shift+5"
move_to_workspace_6 = "super+shift+6"
move_to_workspace_7 = "super+shift+7"
move_to_workspace_8 = "super+shift+8"
move_to_workspace_9 = "super+shift+9"
reload_config = "super+shift+r"
quit_wm = "super+shift+q"
screenshot = "super+shift+s"
lock_screen = "super+l"
scratchpad = "super+grave"
