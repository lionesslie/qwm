import os
import shutil
import signal
import subprocess
import logging
import tempfile

logger = logging.getLogger("qwm.render.compositor")

CONFIG_TEMPLATE = """
backend = "{backend}";
vsync = {vsync};
glx-no-stencil = {glx_no_stencil};
glx-no-rebind-pixmap = {glx_no_rebind_pixmap};
use-damage = true;

corner-radius = {corner_radius};
rounded-corners-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];

shadow = {shadow};
shadow-radius = 18;
shadow-opacity = 0.55;
shadow-offset-x = -14;
shadow-offset-y = -14;
shadow-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];

blur-method = "{blur_method}";
blur-strength = 6;
blur-background = {blur};
blur-background-exclude = [
  "window_type = 'desktop'"
];

fading = {fading};
fade-in-step = {fade_step};
fade-out-step = {fade_step};
fade-delta = 6;

animations = {animations};
animation-stiffness = 220;
animation-window-mass = 0.5;
animation-dampening = 22;
animation-clamping = true;
animation-for-open-window = "zoom";
animation-for-unmap-window = "zoom";
animation-for-workspace-switch-in = "slide-left";
animation-for-workspace-switch-out = "slide-right";

unredirect-fullscreen = {unredirect_fullscreen};

mark-wmwin-focused = true;
mark-ovredir-focused = true;
detect-rounded-corners = true;
detect-client-opacity = true;
detect-transient = true;
use-ewmh-active-win = true;

wintypes:
{{
  dock = {{ shadow = false; }};
  dnd = {{ shadow = false; }};
  popup_menu = {{ opacity = 0.95; }};
  dropdown_menu = {{ opacity = 0.95; }};
}};
"""


class CompositorManager:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, "picom.conf")
        self.user_config_path = os.path.expanduser("~/.config/picom/picom.conf")
        self.process = None
        self.binary = self._find_binary()

    def _find_binary(self):
        for name in ("picom", "picom-jonaburg", "picom-ftlabs-animations"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def generate_config(self, compositor_cfg, animations_cfg, unredirect_fullscreen=False):
        if os.path.exists(self.user_config_path):
            self.config_path = self.user_config_path
            logger.info("kullanicinin kendi picom.conf dosyasi kullaniliyor: %s", self.user_config_path)
            return self.config_path

        self.config_path = os.path.join(self.config_dir, "picom.conf")
        os.makedirs(self.config_dir, exist_ok=True)
        content = CONFIG_TEMPLATE.format(
            backend=compositor_cfg.get("backend", "glx"),
            vsync=str(compositor_cfg.get("vsync", True)).lower(),
            glx_no_stencil=str(compositor_cfg.get("glx_no_stencil", True)).lower(),
            glx_no_rebind_pixmap=str(compositor_cfg.get("glx_no_rebind_pixmap", True)).lower(),
            corner_radius=compositor_cfg.get("corner_radius", 12),
            shadow=str(compositor_cfg.get("shadow", True)).lower(),
            blur=str(compositor_cfg.get("blur", True)).lower(),
            blur_method="dual_kawase" if compositor_cfg.get("blur", True) else "none",
            fading=str(animations_cfg.get("enabled", True)).lower(),
            fade_step=0.06 if animations_cfg.get("enabled", True) else 1.0,
            animations=str(animations_cfg.get("enabled", True)).lower(),
            unredirect_fullscreen=str(unredirect_fullscreen).lower(),
        )
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.config_dir)
        with os.fdopen(tmp_fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, self.config_path)
        return self.config_path

    def start(self):
        if not self.binary:
            logger.warning("picom bulunamadi, compositor devre disi")
            return False
        if self.process and self.process.poll() is None:
            return True
        self.process = subprocess.Popen(
            [self.binary, "--config", self.config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("compositor baslatildi: %s", self.binary)
        return True

    def reload(self):
        if self.process and self.process.poll() is None:
            try:
                os.kill(self.process.pid, signal.SIGUSR1)
                return True
            except ProcessLookupError:
                pass
        return self.start()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
