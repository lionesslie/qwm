package wm

import (
    "log"
    "os/exec"

    "qwm/internal/config"

    "github.com/jezek/xgb/xproto"
    "github.com/jezek/xgbutil"
    "github.com/jezek/xgbutil/ewmh"
    "github.com/jezek/xgbutil/keybind"
    "github.com/jezek/xgbutil/xevent"
    "github.com/jezek/xgbutil/xprop"
    "github.com/jezek/xgbutil/xwindow"
)

type WM struct {
    X          *xgbutil.XUtil
    Cfg        *config.Config
    Root       xproto.Window
    Workspaces [10]*Workspace
    CurWs      int
    ScreenW    int
    ScreenH    int
    PicomCmd   *exec.Cmd
    Focused    xproto.Window
}

func New() (*WM, error) {
    X, err := xgbutil.NewConn()
    if err != nil {
        return nil, err
    }
    cfg, err := config.Load()
    if err != nil {
        log.Printf("config yuklenemedi, varsayilan degerler kullaniliyor: %v", err)
        cfg = config.Default()
    }
    root := X.RootWin()
    geo, err := xwindow.New(X, root).Geometry()
    if err != nil {
        return nil, err
    }

    w := &WM{
        X:       X,
        Cfg:     cfg,
        Root:    root,
        ScreenW: geo.Width(),
        ScreenH: geo.Height(),
    }
    for i := range w.Workspaces {
        w.Workspaces[i] = &Workspace{Focused: -1}
    }

    err = xwindow.New(X, root).Listen(
        xproto.EventMaskSubstructureRedirect |
            xproto.EventMaskSubstructureNotify |
            xproto.EventMaskPropertyChange,
    )
    if err != nil {
        return nil, err
    }

    keybind.Initialize(X)
    ewmh.SupportedSet(X, []string{
        "_NET_WM_STATE",
        "_NET_WM_STATE_FULLSCREEN",
        "_NET_ACTIVE_WINDOW",
        "_NET_NUMBER_OF_DESKTOPS",
        "_NET_CURRENT_DESKTOP",
    })
    ewmh.NumberOfDesktopsSet(X, uint(cfg.Workspaces.Count))
    ewmh.CurrentDesktopSet(X, 0)

    w.registerEvents()
    w.RegisterKeys()
    w.StartPicom()
    w.SetWallpaper()
    w.ApplyNvidiaSettings()
    w.WatchConfig()

    return w, nil
}

func (w *WM) Run() {
    xevent.Main(w.X)
}

func (w *WM) Shutdown() {
    if w.PicomCmd != nil && w.PicomCmd.Process != nil {
        w.PicomCmd.Process.Kill()
    }
}

func (w *WM) registerEvents() {
    xevent.MapRequestFun(func(X *xgbutil.XUtil, e xevent.MapRequestEvent) {
        w.Manage(e.Window)
    }).Connect(w.X, w.Root)

    xevent.DestroyNotifyFun(func(X *xgbutil.XUtil, e xevent.DestroyNotifyEvent) {
        w.Unmanage(e.Window)
    }).Connect(w.X, w.Root)

    xevent.UnmapNotifyFun(func(X *xgbutil.XUtil, e xevent.UnmapNotifyEvent) {
        w.Unmanage(e.Window)
    }).Connect(w.X, w.Root)

    xevent.ConfigureRequestFun(func(X *xgbutil.XUtil, e xevent.ConfigureRequestEvent) {
        var values []uint32
        if e.ValueMask&xproto.ConfigWindowX != 0 {
            values = append(values, uint32(e.X))
        }
        if e.ValueMask&xproto.ConfigWindowY != 0 {
            values = append(values, uint32(e.Y))
        }
        if e.ValueMask&xproto.ConfigWindowWidth != 0 {
            values = append(values, uint32(e.Width))
        }
        if e.ValueMask&xproto.ConfigWindowHeight != 0 {
            values = append(values, uint32(e.Height))
        }
        if e.ValueMask&xproto.ConfigWindowBorderWidth != 0 {
            values = append(values, uint32(e.BorderWidth))
        }
        if e.ValueMask&xproto.ConfigWindowSibling != 0 {
            values = append(values, uint32(e.Sibling))
        }
        if e.ValueMask&xproto.ConfigWindowStackMode != 0 {
            values = append(values, uint32(e.StackMode))
        }
        xproto.ConfigureWindow(X.Conn(), e.Window, e.ValueMask, values)
    }).Connect(w.X, w.Root)
}

func (w *WM) Manage(win xproto.Window) {
    attrs, err := xproto.GetWindowAttributes(w.X.Conn(), win).Reply()
    if err == nil && attrs.OverrideRedirect {
        return
    }
    c := &Client{Win: win}
    ws := w.Workspaces[w.CurWs]
    ws.Clients = append(ws.Clients, c)
    ws.Focused = len(ws.Clients) - 1

    bw := uint32(w.Cfg.General.BorderWidth)
    xproto.ConfigureWindow(w.X.Conn(), win, xproto.ConfigWindowBorderWidth, []uint32{bw})
    color := hexToPixel(w.X, w.Cfg.General.BorderActive)
    xproto.ChangeWindowAttributes(w.X.Conn(), win, xproto.CwBorderPixel, []uint32{color})

    xwindow.New(w.X, win).Listen(xproto.EventMaskEnterWindow | xproto.EventMaskPropertyChange)
    xproto.MapWindow(w.X.Conn(), win)
    w.Focus(win)
    w.Tile(w.CurWs)
}

func (w *WM) Unmanage(win xproto.Window) {
    for idx, ws := range w.Workspaces {
        for i, c := range ws.Clients {
            if c.Win == win {
                ws.Clients = append(ws.Clients[:i], ws.Clients[i+1:]...)
                if ws.Focused >= len(ws.Clients) {
                    ws.Focused = len(ws.Clients) - 1
                }
                w.Tile(idx)
                return
            }
        }
    }
}

func (w *WM) Focus(win xproto.Window) {
    w.Focused = win
    xproto.SetInputFocus(w.X.Conn(), xproto.InputFocusPointerRoot, win, xproto.TimeCurrentTime)
    active := hexToPixel(w.X, w.Cfg.General.BorderActive)
    inactive := hexToPixel(w.X, w.Cfg.General.BorderInactive)
    for _, ws := range w.Workspaces {
        for _, c := range ws.Clients {
            col := inactive
            if c.Win == win {
                col = active
            }
            xproto.ChangeWindowAttributes(w.X.Conn(), c.Win, xproto.CwBorderPixel, []uint32{col})
        }
    }
    ewmh.ActiveWindowSet(w.X, win)
}

func (w *WM) CloseFocused() {
    ws := w.Workspaces[w.CurWs]
    if ws.Focused < 0 || ws.Focused >= len(ws.Clients) {
        return
    }
    win := ws.Clients[ws.Focused].Win
    protoAtom, err1 := xprop.Atm(w.X, "WM_PROTOCOLS")
    deleteAtom, err2 := xprop.Atm(w.X, "WM_DELETE_WINDOW")
    if err1 == nil && err2 == nil {
        cm, err := xevent.NewClientMessage(32, win, protoAtom, int(deleteAtom))
        if err == nil {
            xproto.SendEvent(w.X.Conn(), false, win, xproto.EventMaskNoEvent, string(cm.Bytes()))
            return
        }
    }
    xproto.DestroyWindow(w.X.Conn(), win)
}

func (w *WM) ToggleFullscreen() {
    ws := w.Workspaces[w.CurWs]
    if ws.Focused < 0 || ws.Focused >= len(ws.Clients) {
        return
    }
    c := ws.Clients[ws.Focused]
    c.Fullscreen = !c.Fullscreen
    if c.Fullscreen {
        c.PrevX, c.PrevY, c.PrevW, c.PrevH = c.X, c.Y, c.W, c.H
        w.AnimateWindow(c.Win, c.X, c.Y, c.W, c.H, 0, 0, w.ScreenW, w.ScreenH)
        c.X, c.Y, c.W, c.H = 0, 0, w.ScreenW, w.ScreenH
    } else {
        w.Tile(w.CurWs)
    }
}

func (w *WM) SwitchWorkspace(n int) {
    if n == w.CurWs || n < 0 || n >= len(w.Workspaces) {
        return
    }
    for _, c := range w.Workspaces[w.CurWs].Clients {
        xproto.UnmapWindow(w.X.Conn(), c.Win)
    }
    w.CurWs = n
    for _, c := range w.Workspaces[w.CurWs].Clients {
        xproto.MapWindow(w.X.Conn(), c.Win)
    }
    w.Tile(w.CurWs)
    ewmh.CurrentDesktopSet(w.X, uint(n))
}

func (w *WM) MoveToWorkspace(n int) {
    if n == w.CurWs || n < 0 || n >= len(w.Workspaces) {
        return
    }
    ws := w.Workspaces[w.CurWs]
    if ws.Focused < 0 || ws.Focused >= len(ws.Clients) {
        return
    }
    c := ws.Clients[ws.Focused]
    ws.Clients = append(ws.Clients[:ws.Focused], ws.Clients[ws.Focused+1:]...)
    xproto.UnmapWindow(w.X.Conn(), c.Win)
    w.Workspaces[n].Clients = append(w.Workspaces[n].Clients, c)
    if ws.Focused >= len(ws.Clients) {
        ws.Focused = len(ws.Clients) - 1
    }
    w.Tile(w.CurWs)
}
