package wm

import (
    "fmt"
    "os"
    "os/exec"
    "strings"

    "github.com/jezek/xgb/xproto"
    "github.com/jezek/xgbutil"
    "github.com/jezek/xgbutil/keybind"
    "github.com/jezek/xgbutil/xevent"
)

func (w *WM) spawn(cmd string) {
    if cmd == "" {
        return
    }
    parts := strings.Fields(cmd)
    c := exec.Command(parts[0], parts[1:]...)
    c.Env = w.buildEnv()
    c.Start()
}

func (w *WM) buildEnv() []string {
    env := os.Environ()
    if w.Cfg.Nvidia.EnableOptimizations {
        env = append(env,
            "__GL_YIELD=USLEEP",
            "__GL_THREADED_OPTIMIZATIONS=1",
            "__GL_SHADER_DISK_CACHE=1",
        )
        if w.Cfg.Nvidia.DisableVsyncForGames {
            env = append(env, "__GL_SYNC_TO_VBLANK=0")
        }
    }
    return env
}

func (w *WM) UngrabAllKeys() {
    xproto.UngrabKey(w.X.Conn(), 0, w.Root, xproto.ModMaskAny)
}

func (w *WM) RegisterKeys() {
    kb := w.Cfg.Keybindings

    bind := func(key string, fn func()) {
        if key == "" {
            return
        }
        err := keybind.KeyPressFun(func(X *xgbutil.XUtil, e xevent.KeyPressEvent) {
            fn()
        }).Connect(w.X, w.Root, key, true)
        if err != nil {
            fmt.Printf("keybind hatasi (%s): %v\n", key, err)
        }
    }

    bind(kb.Terminal, func() { w.spawn(w.Cfg.Apps.Terminal) })
    bind(kb.Launcher, func() { w.spawn(w.Cfg.Apps.Launcher) })
    bind(kb.CloseWindow, w.CloseFocused)
    bind(kb.QuitWM, func() { w.Shutdown(); os.Exit(0) })
    bind(kb.ReloadConfig, w.ReloadConfig)
    bind(kb.Fullscreen, w.ToggleFullscreen)
    bind(kb.ToggleFloating, w.ToggleCurrentFloating)
    bind(kb.FocusLeft, w.FocusPrev)
    bind(kb.FocusRight, w.FocusNext)
    bind(kb.FocusUp, w.FocusPrev)
    bind(kb.FocusDown, w.FocusNext)
    bind(kb.MoveLeft, w.MovePrev)
    bind(kb.MoveRight, w.MoveNext)
    bind(kb.MoveUp, w.MovePrev)
    bind(kb.MoveDown, w.MoveNext)
    bind(kb.ScreenshotFull, func() { w.spawn("scrot") })
    bind(kb.LockScreen, func() { w.spawn("i3lock") })

    mod := w.Cfg.General.ModKey
    digits := []string{"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"}
    for i, d := range digits {
        idx := i
        bind(mod+"-"+d, func() { w.SwitchWorkspace(idx) })
        bind(mod+"-Shift-"+d, func() { w.MoveToWorkspace(idx) })
    }
}
