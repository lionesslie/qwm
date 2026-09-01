package wm

import "github.com/jezek/xgb/xproto"

type Client struct {
    Win        xproto.Window
    Floating   bool
    Fullscreen bool
    X, Y, W, H int
    PrevX, PrevY, PrevW, PrevH int
}

type Workspace struct {
    Clients []*Client
    Focused int
}

func (w *WM) FocusNext() {
    ws := w.Workspaces[w.CurWs]
    if len(ws.Clients) == 0 {
        return
    }
    ws.Focused = (ws.Focused + 1) % len(ws.Clients)
    w.Focus(ws.Clients[ws.Focused].Win)
}

func (w *WM) FocusPrev() {
    ws := w.Workspaces[w.CurWs]
    if len(ws.Clients) == 0 {
        return
    }
    ws.Focused = (ws.Focused - 1 + len(ws.Clients)) % len(ws.Clients)
    w.Focus(ws.Clients[ws.Focused].Win)
}

func (w *WM) MoveNext() {
    ws := w.Workspaces[w.CurWs]
    n := len(ws.Clients)
    if n < 2 {
        return
    }
    i := ws.Focused
    j := (i + 1) % n
    ws.Clients[i], ws.Clients[j] = ws.Clients[j], ws.Clients[i]
    ws.Focused = j
    w.Tile(w.CurWs)
}

func (w *WM) MovePrev() {
    ws := w.Workspaces[w.CurWs]
    n := len(ws.Clients)
    if n < 2 {
        return
    }
    i := ws.Focused
    j := (i - 1 + n) % n
    ws.Clients[i], ws.Clients[j] = ws.Clients[j], ws.Clients[i]
    ws.Focused = j
    w.Tile(w.CurWs)
}

func (w *WM) ToggleCurrentFloating() {
    ws := w.Workspaces[w.CurWs]
    if ws.Focused < 0 || ws.Focused >= len(ws.Clients) {
        return
    }
    ws.Clients[ws.Focused].Floating = !ws.Clients[ws.Focused].Floating
    w.Tile(w.CurWs)
}
