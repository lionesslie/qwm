package wm

import "os/exec"

func (w *WM) ApplyNvidiaSettings() {
    if !w.Cfg.Nvidia.EnableOptimizations {
        return
    }
    mode := "0"
    if w.Cfg.Nvidia.PowerMode == "prefer_maximum_performance" {
        mode = "1"
    }
    exec.Command("nvidia-settings", "-a", "[gpu:0]/GPUPowerMizerMode="+mode).Start()
    if w.Cfg.Nvidia.ForceCompositionPipeline {
        exec.Command("nvidia-settings", "-a", "[gpu:0]/ForceCompositionPipeline=On").Start()
    }
}
