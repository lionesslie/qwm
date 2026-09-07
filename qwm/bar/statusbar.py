import time
import threading
import logging
from datetime import datetime

from Xlib import X

from qwm.gpu.nvidia import get_temperature

logger = logging.getLogger("qwm.bar")


class StatusBar:
    def __init__(self, display, screen, height=24, background="#1e1e2e", foreground="#cdd6f4"):
        self.display = display
        self.screen = screen
        self.height = height
        self.window = None
        self.gc = None
        self._running = False
        self._thread = None
        self.background = background
        self.foreground = foreground
        self.workspace_name = "1"
        self.window_title = ""

    def _hex_pixel(self, hex_color):
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return (r << 16) | (g << 8) | b

    def create(self):
        width = self.screen.width_in_pixels
        self.window = self.screen.root.create_window(
            0, 0, width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self._hex_pixel(self.background),
            override_redirect=True,
            event_mask=X.ExposureMask,
        )
        self.gc = self.window.create_gc(
            foreground=self._hex_pixel(self.foreground),
            background=self._hex_pixel(self.background),
        )
        self.window.map()
        self.display.flush()

    def update(self, workspace_name=None, window_title=None):
        if workspace_name is not None:
            self.workspace_name = workspace_name
        if window_title is not None:
            self.window_title = window_title
        self._draw()

    def _draw(self):
        if not self.window:
            return
        now = datetime.now().strftime("%H:%M:%S")
        temp = get_temperature()
        temp_str = f"GPU {temp}C" if temp is not None else ""
        text = f"  [{self.workspace_name}]  {self.window_title[:60]}"
        right_text = f"{temp_str}   {now}  "
        try:
            self.window.clear_area(0, 0, self.screen.width_in_pixels, self.height)
            self.window.draw_text(self.gc, 4, self.height - 7, text.encode())
            x = max(0, self.screen.width_in_pixels - len(right_text) * 7)
            self.window.draw_text(self.gc, x, self.height - 7, right_text.encode())
            self.display.flush()
        except Exception:
            logger.debug("statusbar cizim hatasi", exc_info=True)

    def start(self):
        if not self.window:
            self.create()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="qwm-statusbar")
        self._thread.start()

    def _loop(self):
        while self._running:
            self._draw()
            time.sleep(1)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
