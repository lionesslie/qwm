package main

import (
    "log"
    "os"
    "os/signal"
    "path/filepath"
    "syscall"

    "qwm/internal/wm"
)

func setupLogging() *os.File {
    home, _ := os.UserHomeDir()
    dir := filepath.Join(home, ".cache", "qwm")
    os.MkdirAll(dir, 0755)
    path := filepath.Join(dir, "qwm.log")
    f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
    if err != nil {
        return nil
    }
    log.SetOutput(f)
    return f
}

func main() {
    logFile := setupLogging()
    if logFile != nil {
        defer logFile.Close()
    }

    w, err := wm.New()
    if err != nil {
        log.Fatalf("qwm baslatilamadi: %v", err)
    }
    sigc := make(chan os.Signal, 1)
    signal.Notify(sigc, syscall.SIGINT, syscall.SIGTERM)
    go func() {
        <-sigc
        w.Shutdown()
        os.Exit(0)
    }()
    w.Run()
}