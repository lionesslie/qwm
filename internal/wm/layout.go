package wm

func (w *WM) Tile(idx int) {
    ws := w.Workspaces[idx]
    var tiled []*Client
    for _, c := range ws.Clients {
        if !c.Floating && !c.Fullscreen {
            tiled = append(tiled, c)
        }
    }
    n := len(tiled)
    if n == 0 {
        return
    }
    cfg := w.Cfg
    gap := cfg.General.GapsInner
    outer := cfg.General.GapsOuter
    usableW := w.ScreenW - 2*outer
    usableH := w.ScreenH - 2*outer

    if n == 1 {
        w.animateClient(tiled[0], outer, outer, usableW, usableH)
        return
    }

    ratio := cfg.Layout.MasterRatio
    if ratio <= 0.1 || ratio >= 0.9 {
        ratio = 0.55
    }
    masterW := int(float64(usableW) * ratio)
    stackW := usableW - masterW - gap

    w.animateClient(tiled[0], outer, outer, masterW, usableH)

    stackCount := n - 1
    stackH := (usableH - (stackCount-1)*gap) / stackCount
    y := outer
    for i := 1; i < n; i++ {
        w.animateClient(tiled[i], outer+masterW+gap, y, stackW, stackH)
        y += stackH + gap
    }
}
