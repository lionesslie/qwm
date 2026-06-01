import subprocess
import logging

logger = logging.getLogger("qwm.nvidia.settings")

class NvidiaSettings:
    """Wrapper for nvidia-settings CLI."""
    
    @staticmethod
    def set_attribute(attr: str, value: str, display: str = ":0"):
        """Run nvidia-settings to set an attribute."""
        cmd = ["nvidia-settings", f"--ctrl-display={display}", "-a", f"{attr}={value}"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.debug(f"Applied nvidia-settings: {attr}={value}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply nvidia-settings {attr}={value}: {e.stderr}")
        except FileNotFoundError:
            logger.error("nvidia-settings not found in PATH")
            
    @staticmethod
    def query_attribute(attr: str, display: str = ":0") -> str:
        cmd = ["nvidia-settings", f"--ctrl-display={display}", "-q", attr, "-t"]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return ""
