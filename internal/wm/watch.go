package wm

import (
    "log"
    "os"
    "path/filepath"
    "sync"
    "time"

    "github.com/fsnotify/fsnotify"
    "qwm/internal/config"
)

var reloadMu sync.Mutex

func (w *WM) WatchConfig() {
    watcher, err := fsnotify.NewWatcher()
    if err != nil {
        log.Printf("config izleyici baslatilamadi: %v", err)
        return
    }
    path := config.Path()
    dir := filepath.Dir(path)
    os.MkdirAll(dir, 0755)
    if err := watcher.Add(dir); err != nil {
        log.Printf("dizin izlenemedi: %v", err)
        return
    }

    var timer *time.Timer
    var timerMu sync.Mutex

    go func() {
        for {
            select {
            case ev, ok := <-watcher.Events:
                if !ok {
                    return
                }
                if filepath.Clean(ev.Name) != filepath.Clean(path) {
                    continue
                }
                if ev.Op&(fsnotify.Write|fsnotify.Create) == 0 {
                    continue
                }
                timerMu.Lock()
                if timer != nil {
                    timer.Stop()
                }
                timer = time.AfterFunc(500*time.Millisecond, func() {
                    w.ReloadConfig()
                })
                timerMu.Unlock()
            case _, ok := <-watcher.Errors:
                if !ok {
                    return
                }
            }
        }
    }()
}

func (w *WM) ReloadConfig() {
    reloadMu.Lock()
    defer reloadMu.Unlock()

    cfg, err := config.Load()
    if err != nil {
        log.Printf("config yeniden yuklenemedi: %v", err)
        return
    }
    oldCfg := w.Cfg
    w.Cfg = cfg
    w.UngrabAllKeys()
    w.RegisterKeys()
    if picomSettingsChanged(oldCfg, cfg) {
        w.StartPicom()
    }
    w.SetWallpaper()
    w.ApplyNvidiaSettings()
    w.ApplyMonitorSettings()
    w.ApplyMouseSettings()
    for i := range w.Workspaces {
        w.Tile(i)
    }
    log.Println("config yeniden yuklendi")
}

func picomSettingsChanged(a, b *config.Config) bool {
    if a == nil {
        return true
    }
    return a.General.BorderRadius != b.General.BorderRadius ||
        a.Nvidia.EnableOptimizations != b.Nvidia.EnableOptimizations
}