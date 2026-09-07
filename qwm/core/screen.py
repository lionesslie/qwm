import shutil
import subprocess
import logging

logger = logging.getLogger("qwm.core.screen")


def has_xrandr():
    return shutil.which("xrandr") is not None


def list_outputs():
    if not has_xrandr():
        return []
    try:
        out = subprocess.check_output(["xrandr", "--query"], timeout=5).decode()
    except Exception:
        logger.debug("xrandr --query basarisiz", exc_info=True)
        return []

    outputs = []
    for line in out.splitlines():
        if " connected" in line:
            name = line.split()[0]
            outputs.append(name)
    return outputs


def _build_xrandr_args(name, entry):
    args = ["--output", name]

    if entry.get("disabled"):
        args.append("--off")
        return args

    resolution = entry.get("resolution")
    refresh_rate = entry.get("refresh_rate")
    if resolution:
        mode = resolution
        args += ["--mode", mode]
        if refresh_rate:
            args += ["--rate", str(refresh_rate)]
    else:
        args.append("--auto")

    position = entry.get("position")
    if position:
        args += ["--pos", position]

    rotation = entry.get("rotation")
    if rotation in ("normal", "left", "right", "inverted"):
        args += ["--rotate", rotation]

    scale = entry.get("scale")
    if scale and scale != 1.0 and scale != 1:
        factor = f"{scale}x{scale}"
        args += ["--scale", factor]

    if entry.get("primary"):
        args.append("--primary")

    return args


def apply_monitor_config(monitors_cfg):
    if not monitors_cfg:
        return
    if not has_xrandr():
        logger.warning("xrandr bulunamadi, monitor ayarlari atlaniyor")
        return

    connected = set(list_outputs())
    for entry in monitors_cfg:
        name = entry.get("name")
        if name not in connected:
            logger.warning("monitor bulunamadi, atlaniyor: %s (bagli cikislar: %s)", name, sorted(connected))
            continue
        args = _build_xrandr_args(name, entry)
        try:
            subprocess.run(["xrandr"] + args, check=True, timeout=10,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.info("monitor ayarlandi: %s (%s)", name, " ".join(args))
        except subprocess.CalledProcessError as exc:
            logger.warning("xrandr basarisiz: %s -> %s", name, exc.stderr.decode(errors="replace") if exc.stderr else exc)
        except subprocess.TimeoutExpired:
            logger.warning("xrandr zaman asimina ugradi: %s", name)
