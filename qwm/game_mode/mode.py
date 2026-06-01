import logging
from typing import Optional

from ..nvidia.powermizer import PowerMizerController, PowerMizerMode
from ..nvidia.gsync import GSyncController
from ..nvidia.glx import GLXEnvironment

logger = logging.getLogger("qwm.game_mode.mode")

class GameModeManager:
    """Manages transitioning into and out of NVIDIA Game Mode."""
    
    def __init__(self, wm_state, config):
        self.state = wm_state
        self.config = config
        
    def activate(self, window_xid: Optional[int] = None, pid: Optional[int] = None):
        if self.state.game_mode.active:
            return
            
        logger.info("Activating GAME MODE")
        self.state.game_mode.active = True
        self.state.game_mode.active_process_id = pid
        
        # 1. Kill compositor
        # TODO: call compositor.kill()
        
        # 2. NVIDIA PowerMizer to MAX_PERF
        PowerMizerController.set_mode(PowerMizerMode.MAX_PERF)
        
        # 3. Disable G-Sync composition pipeline (if using G-Sync)
        GSyncController.disable_composition_pipeline()
        
        # 4. Set process priority (if pid known)
        # TODO: call utils.process.set_priority(pid, -10)
        
    def deactivate(self):
        if not self.state.game_mode.active:
            return
            
        logger.info("Deactivating GAME MODE")
        self.state.game_mode.active = False
        self.state.game_mode.active_process_id = None
        
        # 1. Restore PowerMizer
        PowerMizerController.set_mode(PowerMizerMode.ADAPTIVE)
        
        # 2. Re-enable composition pipeline
        GSyncController.enable_composition_pipeline()
        
        # 3. Restart compositor
        # TODO: call compositor.start()
