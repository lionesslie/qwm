import time
import threading
import queue
import logging

logger = logging.getLogger("qwm.render.animator")


def linear(t):
    return t


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    return t ** 3


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t ** 3
    return 1 - ((-2 * t + 2) ** 3) / 2


EASINGS = {
    "linear": linear,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_cubic": ease_in_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,
}


class Animation:
    __slots__ = ("start_values", "end_values", "duration", "easing_fn", "on_update", "on_complete", "start_time")

    def __init__(self, start_values, end_values, duration_ms, easing_name, on_update, on_complete=None):
        self.start_values = start_values
        self.end_values = end_values
        self.duration = max(duration_ms, 1) / 1000.0
        self.easing_fn = EASINGS.get(easing_name, ease_out_cubic)
        self.on_update = on_update
        self.on_complete = on_complete
        self.start_time = time.monotonic()

    def step(self, now):
        elapsed = now - self.start_time
        t = min(1.0, elapsed / self.duration)
        eased = self.easing_fn(t)
        values = tuple(
            s + (e - s) * eased for s, e in zip(self.start_values, self.end_values)
        )
        self.on_update(values)
        if t >= 1.0:
            if self.on_complete:
                self.on_complete()
            return True
        return False


class AnimationScheduler:
    def __init__(self, fps=60):
        self.fps = fps
        self.frame_interval = 1.0 / fps
        self._queue = queue.Queue()
        self._animations = []
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, name="qwm-animator", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)

    def submit(self, animation):
        self._queue.put(animation)

    def _run(self):
        while self._running:
            frame_start = time.monotonic()
            while True:
                try:
                    anim = self._queue.get_nowait()
                    self._animations.append(anim)
                except queue.Empty:
                    break

            if self._animations:
                now = time.monotonic()
                finished = []
                for anim in self._animations:
                    try:
                        if anim.step(now):
                            finished.append(anim)
                    except Exception:
                        logger.exception("animation step failed")
                        finished.append(anim)
                for anim in finished:
                    self._animations.remove(anim)

            elapsed = time.monotonic() - frame_start
            sleep_time = self.frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
