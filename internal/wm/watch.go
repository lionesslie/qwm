package wm

import (
    "log"
    "os"
    "path/filepath"
    "time"

    "github.com/fsnotify/fsnotify"
    "qwm/internal/config"
)

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
    go func() {
        for {
            select {
            case ev, ok := <-watcher.Events:
                if !ok {
                    return
                }
                if filepath.Clean(ev.Name) == filepath.Clean(path) {
                    if ev.Op&(fsnotify.Write|fsnotify.Create) != 0 {
                        time.Sleep(150 * time.Millisecond)
                        w.ReloadConfig()
                    }
                }
            case _, ok := <-watcher.Errors:
                if !ok {
                    return
                }
            }
        }
    }()
}

func (w *WM) ReloadConfig() {
    cfg, err := config.Load()
    if err != nil {
        log.Printf("config yeniden yuklenemedi: %v", err)
        return
    }
    w.Cfg = cfg
    w.UngrabAllKeys()
    w.RegisterKeys()
    w.StartPicom()
    w.SetWallpaper()
    w.ApplyNvidiaSettings()
    for i := range w.Workspaces {
        w.Tile(i)
    }
    log.Println("config yeniden yuklendi")
}
