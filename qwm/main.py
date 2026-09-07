import os
import sys
import time
import logging
import argparse

LOG_DIR = os.path.expanduser("~/.local/share/qwm")
LOG_PATH = os.path.join(LOG_DIR, "qwm.log")


def setup_logging(verbose=False):
    os.makedirs(LOG_DIR, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def run_once(config_path, verbose):
    from qwm.config.loader import load_config, ensure_default_config
    from qwm.core.wm import WindowManager
    from qwm.config.watcher import ConfigWatcher
    from qwm.ipc.socket_server import IPCServer

    logger = logging.getLogger("qwm.main")

    ensure_default_config(config_path)
    config, resolved_path = load_config(config_path)

    wm = WindowManager(config, resolved_path)

    watcher = ConfigWatcher(resolved_path, wm.reload_config, debounce_ms=300)
    watcher.start()

    ipc = IPCServer(wm)
    ipc.start()

    try:
        wm.start()
    finally:
        watcher.stop()
        ipc.stop()

    return 0


def main():
    parser = argparse.ArgumentParser(prog="qwm")
    parser.add_argument("--config", default=None, help="config.qc dosya yolu")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-restart", action="store_true", help="cokme sonrasi otomatik yeniden baslatma")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("qwm.main")

    if "DISPLAY" not in os.environ:
        print("HATA: DISPLAY ortam degiskeni tanimli degil, X session icinde calistirilmali", file=sys.stderr)
        return 1

    restart_count = 0
    max_restarts = 5
    while True:
        try:
            return run_once(args.config, args.verbose)
        except SystemExit as exc:
            return exc.code or 0
        except KeyboardInterrupt:
            logger.info("qwm kapatiliyor (kullanici istegi)")
            return 0
        except Exception:
            logger.exception("qwm coktu")
            if args.no_restart:
                return 1
            restart_count += 1
            if restart_count > max_restarts:
                logger.error("cok fazla cokme, yeniden baslatma durduruldu")
                return 1
            time.sleep(1)
            logger.info("qwm yeniden baslatiliyor (%d/%d)", restart_count, max_restarts)


if __name__ == "__main__":
    sys.exit(main())
