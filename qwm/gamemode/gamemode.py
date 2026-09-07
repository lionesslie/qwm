import os
import shutil
import subprocess
import logging

logger = logging.getLogger("qwm.gamemode")


def has_gamemoded():
    return shutil.which("gamemoderun") is not None or shutil.which("gamemoded") is not None


def set_cpu_governor(governor="performance"):
    if shutil.which("cpupower") is None:
        return False
    try:
        subprocess.run(
            ["cpupower", "frequency-set", "-g", governor],
            check=True, timeout=3,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        logger.debug("cpu governor degistirilemedi, sudo gerekebilir", exc_info=True)
        return False


def integrate_gamemode(pid):
    if not has_gamemoded():
        return False
    try:
        import dbus
        bus = dbus.SessionBus()
        proxy = bus.get_object("com.feralinteractive.GameMode", "/com/feralinteractive/GameMode")
        proxy.RegisterGame(pid, dbus_interface="com.feralinteractive.GameMode")
        return True
    except Exception:
        logger.debug("gamemode dbus entegrasyonu basarisiz", exc_info=True)
        return False


class GameModeController:
    def __init__(self, config, compositor, animator_enabled_ref):
        self.config = config
        self.compositor = compositor
        self.active = False
        self.previous_governor = None
        self.animator_enabled_ref = animator_enabled_ref
        self._registered_pids = set()

    def on_window_fullscreen(self, managed_window):
        if not self.config.get("enabled", True):
            return
        if self.active:
            return
        self.active = True
        logger.info("game mode etkin: %s", managed_window.wm_class)

        if self.config.get("disable_animations_on_game", True):
            self.animator_enabled_ref["enabled"] = False

        if self.config.get("unredirect_fullscreen", True) and self.compositor:
            self.compositor.reload()

        set_cpu_governor("performance")

        if managed_window.pid and has_gamemoded():
            if integrate_gamemode(managed_window.pid):
                self._registered_pids.add(managed_window.pid)

    def on_window_unfullscreen(self, managed_window):
        if not self.active:
            return
        still_fullscreen = False
        self.active = still_fullscreen
        if not still_fullscreen:
            logger.info("game mode devre disi")
            if self.config.get("disable_animations_on_game", True):
                self.animator_enabled_ref["enabled"] = True
            set_cpu_governor("powersave")
            if self.compositor:
                self.compositor.reload()

    def env_for_game_process(self):
        from qwm.gpu.nvidia import env_for_performance
        env = dict(os.environ)
        env.update(env_for_performance())
        return env
