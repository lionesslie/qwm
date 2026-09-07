import os
import threading
import logging

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger("qwm.config.watcher")


class _DebouncedHandler(FileSystemEventHandler):
    def __init__(self, target_path, callback, debounce_ms=300):
        self.target_path = os.path.abspath(target_path)
        self.callback = callback
        self.debounce_seconds = debounce_ms / 1000.0
        self._timer = None
        self._lock = threading.Lock()

    def _matches(self, event):
        try:
            return os.path.abspath(event.src_path) == self.target_path
        except Exception:
            return False

    def _schedule(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_seconds, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self):
        try:
            self.callback()
        except Exception:
            logger.exception("config reload callback failed")

    def on_modified(self, event):
        if self._matches(event):
            self._schedule()

    def on_created(self, event):
        if self._matches(event):
            self._schedule()

    def on_moved(self, event):
        if os.path.abspath(getattr(event, "dest_path", "")) == self.target_path:
            self._schedule()


class ConfigWatcher:
    def __init__(self, config_path, on_change, debounce_ms=300):
        self.config_path = config_path
        self.on_change = on_change
        self.debounce_ms = debounce_ms
        self.observer = None
        self.handler = None

    def start(self):
        watch_dir = os.path.dirname(os.path.abspath(self.config_path))
        self.handler = _DebouncedHandler(self.config_path, self.on_change, self.debounce_ms)
        self.observer = Observer()
        self.observer.schedule(self.handler, watch_dir, recursive=False)
        self.observer.daemon = True
        self.observer.start()
        logger.info("config watcher started for %s", self.config_path)

    def stop(self):
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2)
