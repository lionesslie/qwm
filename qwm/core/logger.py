import logging
import sys
from pathlib import Path

def setup_logger(debug: bool = False) -> logging.Logger:
    """Configure structured logging for QWM."""
    logger = logging.getLogger("qwm")
    
    # Avoid adding multiple handlers if setup_logger is called again
    if logger.hasHandlers():
        return logger
        
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_dir = Path.home() / ".local" / "share" / "qwm"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "qwm.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        logger.warning(f"Could not create log directory {log_dir}. File logging disabled.")
        
    return logger
