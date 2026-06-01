import sys
import argparse
import logging
from pathlib import Path

from .qwm import QWM

def main():
    parser = argparse.ArgumentParser(description="QWM - NVIDIA-Optimized Python X11 Tiling Window Manager")
    parser.add_argument("--reset-config", action="store_true", help="Reset config to defaults")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Minimal logging setup before the structured logger takes over
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    try:
        wm = QWM(reset_config=args.reset_config, debug=args.debug)
        wm.run()
    except Exception as e:
        logging.exception("Fatal error in QWM")
        sys.exit(1)

if __name__ == "__main__":
    main()
