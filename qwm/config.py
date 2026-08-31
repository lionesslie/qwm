"""Kullanici yapilandirmasini yukler."""
import importlib.util
import os

USER_CONFIG_PATHS = [
    os.path.expanduser("~/.config/qwm/config.py"),
    "/etc/qwm/config.py",
]


def load_config():
    for path in USER_CONFIG_PATHS:
        if os.path.isfile(path):
            try:
                spec = importlib.util.spec_from_file_location("qwm_user_config", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print(f"[QWM] Yapilandirma yuklendi: {path}")
                return module
            except Exception as exc:
                print(f"[QWM] UYARI: '{path}' okunamadi ({exc}), varsayilana donuluyor.")

    print("[QWM] Ozel config bulunamadi, varsayilan ayarlar kullaniliyor.")
    from qwm import default_config
    return default_config
