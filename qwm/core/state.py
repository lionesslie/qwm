from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class WindowState:
    xid: int
    floating: bool = False
    fullscreen: bool = False
    urgent: bool = False
    workspace: int = 1

@dataclass
class GameModeState:
    active: bool = False
    active_process_id: Optional[int] = None
    saved_powermizer_mode: Optional[int] = None
    saved_compositor_pid: Optional[int] = None

@dataclass
class QWMState:
    """Global state repository for QWM."""
    running: bool = True
    windows: Dict[int, WindowState] = field(default_factory=dict)
    active_window: Optional[int] = None
    active_workspace: int = 1
    game_mode: GameModeState = field(default_factory=GameModeState)
