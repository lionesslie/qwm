package wm

import (
    "fmt"
    "os/exec"

    "github.com/jezek/xgb/xproto"
    "github.com/jezek/xgbutil"
    "github.com/jezek/xgbutil/mousebind"
    "github.com/jezek/xgbutil/xwindow"
)

func (w *WM) ApplyMonitorSettings() {
    m := w.Cfg.Monitor
    if !m.AutoApply || m.Output == "" {
        return
    }
    args := []string{"--output", m.Output}
    if m.Resolution != "" {
        args = append(args, "--mode", m.Resolution)
    }
    if m.RefreshRate > 0 {
        args = append(args, "--rate", fmt.Sprintf("%d", m.RefreshRate))
    }
    exec.Command("xrandr", args...).Run()

    geo, err := xwindow.New(w.X, w.Root).Geometry()
    if err == nil {
        w.ScreenW = geo.Width()
        w.ScreenH = geo.Height()
    }
}

func (w *WM) ApplyMouseSettings() {
    s := w.Cfg.Mouse.Sensitivity
    if s <= 0 {
        s = 1.0
    }
    mult := int(s * 10)
    if mult < 1 {
        mult = 10
    }
    exec.Command("xset", "m", fmt.Sprintf("%d/10", mult), "1").Run()
}

func (w *WM) RunAutostart() {
    if w.AutostartDone {
        return
    }
    for _, app := range w.Cfg.Autostart.Apps {
        w.spawn(app)
    }
    w.AutostartDone = true
}

func (w *WM) clientAt(win xproto.Window) *Client {
    for _, ws := range w.Workspaces {
        for _, c := range ws.Clients {
            if c.Win == win {
                return c
            }
        }
    }
    return nil
}

func (w *WM) SetupMouseBindings() {
    mousebind.Initialize(w.X)
    mod := w.Cfg.General.ModKey

    var dragClient *Client
    var startRootX, startRootY int
    var startWinX, startWinY int
    var startWinW, startWinH int

    mousebind.Drag(
        w.X, w.Root, w.Root, mod+"-1", true,
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) (bool, xproto.Cursor) {
            reply, err := xproto.QueryPointer(X.Conn(), w.Root).Reply()
            if err != nil || reply.Child == 0 {
                return false, 0
            }
            c := w.clientAt(reply.Child)
            if c == nil {
                return false, 0
            }
            dragClient = c
            dragClient.Floating = true
            startRootX, startRootY = rx, ry
            startWinX, startWinY = c.X, c.Y
            return true, 0
        },
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) {
            if dragClient == nil {
                return
            }
            dx := rx - startRootX
            dy := ry - startRootY
            nx := startWinX + dx
            ny := startWinY + dy
            dragClient.X, dragClient.Y = nx, ny
            xwindow.New(X, dragClient.Win).Move(nx, ny)
        },
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) {
            dragClient = nil
        },
    )

    mousebind.Drag(
        w.X, w.Root, w.Root, mod+"-3", true,
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) (bool, xproto.Cursor) {
            reply, err := xproto.QueryPointer(X.Conn(), w.Root).Reply()
            if err != nil || reply.Child == 0 {
                return false, 0
            }
            c := w.clientAt(reply.Child)
            if c == nil {
                return false, 0
            }
            dragClient = c
            dragClient.Floating = true
            startRootX, startRootY = rx, ry
            startWinW, startWinH = c.W, c.H
            return true, 0
        },
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) {
            if dragClient == nil {
                return
            }
            dx := rx - startRootX
            dy := ry - startRootY
            nw := startWinW + dx
            nh := startWinH + dy
            if nw < 100 {
                nw = 100
            }
            if nh < 100 {
                nh = 100
            }
            dragClient.W, dragClient.H = nw, nh
            xwindow.New(X, dragClient.Win).Resize(nw, nh)
        },
        func(X *xgbutil.XUtil, rx, ry, ex, ey int) {
            dragClient = nil
        },
    )
}