import os
import tomllib
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("qwm.config")

class ConfigManager:
    """TOML loader, validator, hot-reload, auto-generator."""
    
    def __init__(self, reset: bool = False):
        self.config_dir = Path.home() / ".config" / "qwm"
        self.config_file = self.config_dir / "qwm.toml"
        self.reset = reset
        
    def load(self) -> Dict[str, Any]:
        """Load the configuration from TOML file, generating defaults if needed."""
        if self.reset or not self.config_file.exists():
            self._generate_default_config()
            
        try:
            with open(self.config_file, "rb") as f:
                config = tomllib.load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}. Falling back to empty defaults.")
            return {}
            
    def _generate_default_config(self):
        """Generates a default TOML configuration."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # We will populate this heavily commented config in later phases
        # For now, it's a basic placeholder
        default_toml = """
[meta]
qwm_version = "0.1.0"
schema_version = 3

[general]
focus_model = "click"
raise_on_focus = true
terminal = "alacritty"
launcher = "rofi"

[appearance]
border_width = 2
border_color_focused = "#00FF88"
border_color_unfocused = "#1A1A2E"

[layout]
default_layout = "tiling"

[nvidia]
nvidia_optimizations = true
enable_nvml = true
"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write(default_toml.strip())
        logger.info(f"Generated default config at {self.config_file}")
