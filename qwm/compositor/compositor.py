import subprocess
import logging

logger = logging.getLogger("qwm.compositor")

class CompositorManager:
    """Manages lifecycle of external compositors like picom."""
    def __init__(self, cmd: str = "picom", args: list = None):
        self.cmd = cmd
        self.args = args or []
        self.process = None
        
    def start(self):
        if self.process:
            return
        logger.info(f"Starting compositor: {self.cmd}")
        try:
            self.process = subprocess.Popen([self.cmd] + self.args)
        except Exception as e:
            logger.error(f"Failed to start compositor: {e}")
            
    def kill(self):
        if not self.process:
            return
        logger.info("Killing compositor")
        self.process.terminate()
        self.process.wait()
        self.process = None
