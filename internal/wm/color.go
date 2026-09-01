package wm

import (
    "os"
    "path/filepath"
    "strconv"
    "strings"

    "github.com/jezek/xgb/xproto"
    "github.com/jezek/xgbutil"
)

func hexToPixel(X *xgbutil.XUtil, hex string) uint32 {
    hex = strings.TrimPrefix(hex, "#")
    if len(hex) != 6 {
        return 0
    }
    r, err1 := strconv.ParseUint(hex[0:2], 16, 16)
    g, err2 := strconv.ParseUint(hex[2:4], 16, 16)
    b, err3 := strconv.ParseUint(hex[4:6], 16, 16)
    if err1 != nil || err2 != nil || err3 != nil {
        return 0
    }
    screen := X.Screen()
    reply, err := xproto.AllocColor(
        X.Conn(), screen.DefaultColormap,
        uint16(r*257), uint16(g*257), uint16(b*257),
    ).Reply()
    if err != nil {
        return 0
    }
    return reply.Pixel
}

func expandHome(p string) string {
    if strings.HasPrefix(p, "~") {
        home, _ := os.UserHomeDir()
        return filepath.Join(home, strings.TrimPrefix(p, "~"))
    }
    return p
}
