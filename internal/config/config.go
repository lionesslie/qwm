package config

import (
    "os"
    "path/filepath"

    "github.com/BurntSushi/toml"
)

type General struct {
    ModKey              string `toml:"mod_key"`
    GapsInner           int    `toml:"gaps_inner"`
    GapsOuter           int    `toml:"gaps_outer"`
    BorderWidth         int    `toml:"border_width"`
    BorderRadius        int    `toml:"border_radius"`
    BorderActive        string `toml:"border_active"`
    BorderInactive      string `toml:"border_inactive"`
    Animations          bool   `toml:"animations"`
    AnimationDurationMs int    `toml:"animation_duration_ms"`
    AnimationFps        int    `toml:"animation_fps"`
}

type Apps struct {
    Terminal      string `toml:"terminal"`
    Launcher      string `toml:"launcher"`
    WallpaperTool string `toml:"wallpaper_tool"`
    WallpaperPath string `toml:"wallpaper_path"`
}

type Nvidia struct {
    EnableOptimizations      bool   `toml:"enable_optimizations"`
    DisableVsyncForGames     bool   `toml:"disable_vsync_for_games"`
    ForceCompositionPipeline bool   `toml:"force_composition_pipeline"`
    PowerMode                string `toml:"power_mode"`
}

type Workspaces struct {
    Count int      `toml:"count"`
    Names []string `toml:"names"`
}

type Layout struct {
    Default     string  `toml:"default"`
    MasterRatio float64 `toml:"master_ratio"`
}

type Monitor struct {
    Output      string `toml:"output"`
    Resolution  string `toml:"resolution"`
    RefreshRate int    `toml:"refresh_rate"`
    AutoApply   bool   `toml:"auto_apply"`
}

type Mouse struct {
    Sensitivity  float64 `toml:"sensitivity"`
    NaturalAccel bool    `toml:"natural_accel"`
}

type Autostart struct {
    Apps []string `toml:"apps"`
}

type CustomKeybinding struct {
    Key  string `toml:"key"`
    Exec string `toml:"exec"`
}

type Keybindings struct {
    Terminal       string `toml:"terminal"`
    Launcher       string `toml:"launcher"`
    CloseWindow    string `toml:"close_window"`
    QuitWM         string `toml:"quit_wm"`
    ReloadConfig   string `toml:"reload_config"`
    Fullscreen     string `toml:"fullscreen"`
    ToggleFloating string `toml:"toggle_floating"`
    FocusLeft      string `toml:"focus_left"`
    FocusRight     string `toml:"focus_right"`
    FocusUp        string `toml:"focus_up"`
    FocusDown      string `toml:"focus_down"`
    MoveLeft       string `toml:"move_left"`
    MoveRight      string `toml:"move_right"`
    MoveUp         string `toml:"move_up"`
    MoveDown       string `toml:"move_down"`
    ScreenshotFull string `toml:"screenshot_full"`
    LockScreen     string `toml:"lock_screen"`
}

type Config struct {
    General           General            `toml:"general"`
    Apps              Apps               `toml:"apps"`
    Nvidia            Nvidia             `toml:"nvidia"`
    Workspaces        Workspaces         `toml:"workspaces"`
    Layout            Layout             `toml:"layout"`
    Monitor           Monitor            `toml:"monitor"`
    Mouse             Mouse              `toml:"mouse"`
    Autostart         Autostart          `toml:"autostart"`
    Keybindings       Keybindings        `toml:"keybindings"`
    CustomKeybindings []CustomKeybinding `toml:"custom_keybindings"`
}

func Default() *Config {
    return &Config{
        General: General{
            ModKey: "Mod4", GapsInner: 10, GapsOuter: 15,
            BorderWidth: 2, BorderRadius: 8,
            BorderActive: "#89b4fa", BorderInactive: "#313244",
            Animations: true, AnimationDurationMs: 180, AnimationFps: 60,
        },
        Apps: Apps{
            Terminal: "alacritty", Launcher: "rofi -show drun",
            WallpaperTool: "feh", WallpaperPath: "~/.config/qwm/wallpaper.jpg",
        },
        Nvidia: Nvidia{
            EnableOptimizations: true, DisableVsyncForGames: true,
            ForceCompositionPipeline: false, PowerMode: "prefer_maximum_performance",
        },
        Workspaces: Workspaces{Count: 10, Names: []string{"1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}},
        Layout:     Layout{Default: "master_stack", MasterRatio: 0.55},
        Monitor:    Monitor{Output: "", Resolution: "", RefreshRate: 0, AutoApply: false},
        Mouse:      Mouse{Sensitivity: 1.0, NaturalAccel: false},
        Autostart:  Autostart{Apps: []string{}},
        Keybindings: Keybindings{
            Terminal: "Mod4-Return", Launcher: "Mod4-d", CloseWindow: "Mod4-q",
            QuitWM: "Mod4-Shift-e", ReloadConfig: "Mod4-Shift-r", Fullscreen: "Mod4-f",
            ToggleFloating: "Mod4-space",
            FocusLeft: "Mod4-h", FocusRight: "Mod4-l", FocusUp: "Mod4-k", FocusDown: "Mod4-j",
            MoveLeft: "Mod4-Shift-h", MoveRight: "Mod4-Shift-l", MoveUp: "Mod4-Shift-k", MoveDown: "Mod4-Shift-j",
            ScreenshotFull: "Print", LockScreen: "",
        },
        CustomKeybindings: []CustomKeybinding{},
    }
}

func Path() string {
    home, _ := os.UserHomeDir()
    return filepath.Join(home, ".config", "qwm", "config.qc")
}

func Load() (*Config, error) {
    cfg := Default()
    path := Path()
    if _, err := os.Stat(path); os.IsNotExist(err) {
        return cfg, nil
    }
    if _, err := toml.DecodeFile(path, cfg); err != nil {
        return nil, err
    }
    return cfg, nil
}