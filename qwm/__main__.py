"""Giris noktasi: `python3 -m qwm`
Loglama + hata durumunda siyah ekranda kilitlenmeyi onleyen guvenlik agi icerir.
"""
import os
import subprocess
import sys
import traceback


def main():
    log_dir = os.path.expanduser("~/.local/share/qwm")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "qwm.log")
    log_file = open(log_path, "a", buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file

    try:
        from qwm import config, nvidia
        from qwm.wm import WM

        cfg = config.load_config()
        nvidia.apply_nvidia_optimizations(cfg)

        for cmd in getattr(cfg, "AUTOSTART", []):
            try:
                subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as exc:
                print(f"[QWM] Autostart hatasi ({cmd}): {exc}")

        wm = WM(cfg)
        wm.run()
        sys.exit(0)

    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        log_file.flush()
        # KRITIK: WM coker/baslamaz ise siyah ekranda kilitli kalma.
        # En azindan bir terminal ac ki kullanici log'u okuyup TTY'ye gecebilsin.
        try:
            subprocess.Popen(["xterm", "-geometry", "100x30", "-e",
                               f"bash -c 'echo QWM COKTU. Log: {log_path}; "
                               f"tail -n 40 {log_path}; exec bash'"])
        except FileNotFoundError:
            pass
        # Sonsuz beklemek yerine, X session'in kapanmasina izin ver.
        import time
        time.sleep(5)
        sys.exit(1)


if __name__ == "__main__":
    main()