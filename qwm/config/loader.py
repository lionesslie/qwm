import os
import sys
import logging

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .schema import validate_and_merge, ConfigError, DEFAULTS

logger = logging.getLogger("qwm.config")

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/qwm")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.qc")


def _extract_line_from_error(exc):
    msg = str(exc)
    if "line" in msg:
        for token in msg.replace(",", " ").split():
            if token.isdigit():
                return int(token)
    return None


def parse_toml_file(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        raise ConfigError(f"config dosyası bulunamadı: {path}")
    except OSError as exc:
        raise ConfigError(f"config dosyası okunamadı: {exc}")

    try:
        return tomllib.loads(raw.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        line = _extract_line_from_error(exc)
        raise ConfigError(f"TOML sözdizim hatası: {exc}", line=line)


def load_config(path=None):
    path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        logger.warning("config dosyası yok, varsayılanlar kullanılıyor: %s", path)
        return validate_and_merge({}), path

    raw = parse_toml_file(path)
    try:
        merged = validate_and_merge(raw)
    except ConfigError as exc:
        logger.error(str(exc))
        print(f"[qwm] config hatasi: {exc}", file=sys.stderr)
        raise
    return merged, path


def ensure_default_config(path=None):
    path = path or DEFAULT_CONFIG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_src = os.path.join(here, "config.qc")
        if os.path.exists(default_src):
            with open(default_src, "r") as src, open(path, "w") as dst:
                dst.write(src.read())
        else:
            with open(path, "w") as dst:
                dst.write(render_default_qc())
    return path


def render_default_qc():
    lines = []
    for section, values in DEFAULTS.items():
        if not isinstance(values, dict) or section == "rules":
            continue
        lines.append(f"[{section}]")
        for key, val in values.items():
            lines.append(f"{key} = {_toml_value(val)}")
        lines.append("")
    return "\n".join(lines)


def _toml_value(val):
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        return "[" + ", ".join(_toml_value(v) for v in val) + "]"
    return '"' + str(val).replace('"', '\\"') + '"'
