package wm

import (
    "os"
    "os/exec"
)

func (w *WM) SetWallpaper() {
    tool := w.Cfg.Apps.WallpaperTool
    if tool == "" {
        tool = "feh"
    }
    if _, err := exec.LookPath(tool); err != nil {
        return
    }
    path := expandHome(w.Cfg.Apps.WallpaperPath)
    if _, err := os.Stat(path); err == nil {
        exec.Command(tool, "--bg-fill", path).Start()
    } else {
        exec.Command(tool, "--bg-color", "#1e1e2e").Start()
    }
}
