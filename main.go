package main

import (
    "log"
    "os"
    "os/signal"
    "syscall"

    "qwm/internal/wm"
)

func main() {
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
