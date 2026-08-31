"""NVIDIA GPU tespiti ve tearing/performans optimizasyonlari."""
import os
import subprocess


def is_nvidia_gpu() -> bool:
    try:
        out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3).stdout
        return "nvidia" in out.lower()
    except Exception:
        return False


def get_connected_outputs():
    """xrandr'dan bagli ekran (output) isimlerini dondurur (orn. ['HDMI-0', 'DP-0'])."""
    outputs = []
    try:
        out = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=3).stdout
        for line in out.splitlines():
            if " connected" in line:
                outputs.append(line.split()[0])
    except Exception:
        pass
    return outputs


def apply_nvidia_optimizations(cfg):
    if not getattr(cfg, "NVIDIA_OPTIMIZATIONS_ENABLED", False):
        return
    if not is_nvidia_gpu():
        print("[QWM] NVIDIA GPU bulunamadi (VM olabilir), ilgili optimizasyonlar atlaniyor.")
        return

    for key, value in getattr(cfg, "NVIDIA_ENV_VARS", {}).items():
        os.environ[key] = str(value)

    if getattr(cfg, "NVIDIA_FORCE_COMPOSITION_PIPELINE", False):
        outputs = get_connected_outputs()
        if not outputs:
            print("[QWM] xrandr cikisi bulunamadi, ForceCompositionPipeline atlaniyor.")
        for output in outputs:
            result = subprocess.run(
                ["nvidia-settings", "-a", f"[DPY:{output}]/ForceCompositionPipeline=On"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"[QWM] NVIDIA ForceCompositionPipeline aktif: {output}")
            else:
                print(f"[QWM] NVIDIA ayari uygulanamadi ({output}): {result.stderr.strip()}")

    print("[QWM] NVIDIA optimizasyonlari uygulandi.")
