"""Oyun modu acilip kapanirken sistem genelinde uygulanan performans ayarlari.

Buradaki her islem best-effort'tur: yetki yoksa veya arac kurulu degilse
sessizce atlanir, WM asla bu yuzden coker/durmaz.
"""
import os
import subprocess


def _run(cmd, timeout=2):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None


def _set_cpu_governor(governor):
    """Tum cekirdekler icin cpufreq governor'unu degistirmeyi dener (perf/powersave)."""
    base = "/sys/devices/system/cpu"
    try:
        cpus = [d for d in os.listdir(base) if d.startswith("cpu") and d[3:].isdigit()]
    except Exception:
        return
    for cpu in cpus:
        path = f"{base}/{cpu}/cpufreq/scaling_governor"
        try:
            with open(path, "w") as f:
                f.write(governor)
        except Exception:
            pass  # yetki yoksa (root degilsek) sessizce gec


def _renice_compositor(nice_value):
    """Calisan picom/compton gibi compositor surecine yeniden onceliklendirme dener."""
    result = _run(["pgrep", "-x", "picom"]) or _run(["pgrep", "-x", "compton"])
    if not result or result.returncode != 0:
        return
    for pid in result.stdout.split():
        try:
            os.system(f"renice -n {nice_value} -p {pid} > /dev/null 2>&1")
        except Exception:
            pass


def apply_game_mode(cfg, enable):
    if not getattr(cfg, "GAME_MODE_ENABLED", True):
        return

    for key, value in getattr(cfg, "GAME_MODE_ENV_VARS", {}).items():
        if enable:
            os.environ[key] = str(value)
        else:
            os.environ.pop(key, None)

    if getattr(cfg, "GAME_MODE_CPU_GOVERNOR", True):
        _set_cpu_governor("performance" if enable else "powersave")

    if getattr(cfg, "GAME_MODE_DEPRIORITIZE_COMPOSITOR", True):
        _renice_compositor(15 if enable else 0)

    for cmd in getattr(cfg, "GAME_MODE_ON_ENABLE" if enable else "GAME_MODE_ON_DISABLE", []):
        try:
            subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            print(f"[QWM] Oyun modu komutu calistirilamadi '{cmd}': {exc}")
