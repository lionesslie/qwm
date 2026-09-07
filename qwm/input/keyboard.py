import shutil
import subprocess
import logging

logger = logging.getLogger("qwm.input.keyboard")


def has_setxkbmap():
    return shutil.which("setxkbmap") is not None


def apply_keyboard_config(cfg):
    _apply_layout(cfg)
    _apply_repeat(cfg)
    if cfg.get("numlock_on_start"):
        _enable_numlock()


def _apply_layout(cfg):
    if not has_setxkbmap():
        logger.warning("setxkbmap bulunamadi, klavye duzeni atlaniyor")
        return

    args = ["setxkbmap"]
    layout = cfg.get("layout", "us")
    args += ["-layout", layout]

    variant = cfg.get("variant")
    if variant:
        args += ["-variant", variant]

    model = cfg.get("model")
    if model:
        args += ["-model", model]

    options = cfg.get("options")
    if options:
        args += ["-option", options]
    else:
        args.append("-option")

    try:
        subprocess.run(args, check=True, timeout=5,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        logger.info("klavye duzeni ayarlandi: %s%s", layout, f" ({variant})" if variant else "")
    except subprocess.CalledProcessError as exc:
        logger.warning("setxkbmap basarisiz: %s", exc.stderr.decode(errors="replace") if exc.stderr else exc)
    except subprocess.TimeoutExpired:
        logger.warning("setxkbmap zaman asimina ugradi")


def _apply_repeat(cfg):
    if shutil.which("xset") is None:
        logger.warning("xset bulunamadi, tus tekrar hizi atlaniyor")
        return
    delay = cfg.get("repeat_delay_ms", 300)
    rate = cfg.get("repeat_rate", 30)
    try:
        subprocess.run(
            ["xset", "r", "rate", str(delay), str(rate)],
            check=True, timeout=5,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        logger.info("tus tekrar hizi ayarlandi: delay=%sms rate=%s/s", delay, rate)
    except Exception:
        logger.warning("xset ile tus tekrar hizi ayarlanamadi", exc_info=True)


def _enable_numlock():
    if shutil.which("numlockx") is None:
        logger.warning("numlockx bulunamadi, numlock atlaniyor")
        return
    try:
        subprocess.run(["numlockx", "on"], check=True, timeout=5,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("numlock acildi")
    except Exception:
        logger.warning("numlockx basarisiz oldu", exc_info=True)
