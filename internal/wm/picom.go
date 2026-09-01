package wm

import (
    "fmt"
    "os"
    "os/exec"
    "path/filepath"
)

func (w *WM) StartPicom() {
    if w.PicomCmd != nil && w.PicomCmd.Process != nil {
        w.PicomCmd.Process.Kill()
        w.PicomCmd.Wait()
    }
    if _, err := exec.LookPath("picom"); err != nil {
        return
    }
    home, _ := os.UserHomeDir()
    dir := filepath.Join(home, ".config", "qwm")
    os.MkdirAll(dir, 0755)
    path := filepath.Join(dir, "picom.conf")
    content := w.generatePicomConf()
    os.WriteFile(path, []byte(content), 0644)
    cmd := exec.Command("picom", "--config", path)
    cmd.Start()
    w.PicomCmd = cmd
}

func (w *WM) generatePicomConf() string {
    radius := w.Cfg.General.BorderRadius
    vsync := "true"
    if !w.Cfg.Nvidia.EnableOptimizations {
        vsync = "false"
    }
    return fmt.Sprintf(`backend = "glx";
vsync = %s;
corner-radius = %d;
round-borders = 1;
rounded-corners-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];
shadow = true;
shadow-radius = 16;
shadow-opacity = 0.5;
shadow-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];
fading = true;
fade-in-step = 0.05;
fade-out-step = 0.05;
fade-delta = 5;
unredirect-fullscreen-windows = true;
use-damage = true;
detect-rounded-corners = true;
detect-client-opacity = true;
glx-no-stencil = true;
glx-no-rebind-pixmap = true;
mark-wmwin-focused = true;
mark-ovredir-focused = true;
detect-transient = true;
detect-client-leader = true;
`, vsync, radius)
}
