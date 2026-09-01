package wm

import (
    "time"

    "github.com/jezek/xgb/xproto"
    "github.com/jezek/xgbutil/xwindow"
)

func easeOutCubic(t float64) float64 {
    t -= 1
    return t*t*t + 1
}

func (w *WM) animateClient(c *Client, x, y, width, height int) {
    bw := w.Cfg.General.BorderWidth
    cw := width - 2*bw
    ch := height - 2*bw
    if cw < 50 {
        cw = 50
    }
    if ch < 50 {
        ch = 50
    }
    fx, fy, fw, fh := c.X, c.Y, c.W, c.H
    if fw == 0 && fh == 0 {
        fx, fy, fw, fh = x, y, cw, ch
    }
    w.AnimateWindow(c.Win, fx, fy, fw, fh, x, y, cw, ch)
    c.X, c.Y, c.W, c.H = x, y, cw, ch
}

func (w *WM) AnimateWindow(win xproto.Window, fx, fy, fw, fh, tx, ty, tw, th int) {
    if !w.Cfg.General.Animations {
        xwindow.New(w.X, win).MoveResize(tx, ty, tw, th)
        return
    }
    fps := w.Cfg.General.AnimationFps
    if fps <= 0 {
        fps = 60
    }
    durationMs := w.Cfg.General.AnimationDurationMs
    if durationMs <= 0 {
        durationMs = 180
    }
    steps := durationMs * fps / 1000
    if steps < 1 {
        steps = 1
    }
    interval := time.Duration(durationMs/steps) * time.Millisecond

    go func() {
        win2 := xwindow.New(w.X, win)
        for i := 1; i <= steps; i++ {
            t := easeOutCubic(float64(i) / float64(steps))
            x := fx + int(float64(tx-fx)*t)
            y := fy + int(float64(ty-fy)*t)
            ww := fw + int(float64(tw-fw)*t)
            hh := fh + int(float64(th-fh)*t)
            if ww < 1 {
                ww = 1
            }
            if hh < 1 {
                hh = 1
            }
            win2.MoveResize(x, y, ww, hh)
            time.Sleep(interval)
        }
        win2.MoveResize(tx, ty, tw, th)
    }()
}
