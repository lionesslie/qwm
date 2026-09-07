import os
import socket
import threading
import json
import logging
import queue

logger = logging.getLogger("qwm.ipc")

DEFAULT_SOCKET_PATH = os.path.expanduser("~/.local/share/qwm/qwm.sock")


class IPCServer:
    def __init__(self, wm, socket_path=None):
        self.wm = wm
        self.socket_path = socket_path or DEFAULT_SOCKET_PATH
        self._sock = None
        self._thread = None
        self._running = False

    def start(self):
        os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self.socket_path)
        self._sock.listen(5)
        self._sock.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="qwm-ipc")
        self._thread.start()
        logger.info("ipc socket dinliyor: %s", self.socket_path)

    def _loop(self):
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()

    def _handle_conn(self, conn):
        with conn:
            try:
                data = conn.recv(4096)
                if not data:
                    return
                payload = json.loads(data.decode())
                result_queue = queue.Queue()
                payload["result_queue"] = result_queue
                self.wm.submit_ipc_command(payload)
                try:
                    result = result_queue.get(timeout=2)
                except queue.Empty:
                    result = "timeout"
                conn.sendall(json.dumps({"status": result}).encode())
            except Exception:
                logger.exception("ipc baglanti hatasi")

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass


def send_command(cmd, args=None, socket_path=None):
    socket_path = socket_path or DEFAULT_SOCKET_PATH
    payload = json.dumps({"cmd": cmd, "args": args or []}).encode()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect(socket_path)
        sock.sendall(payload)
        response = sock.recv(4096)
        return json.loads(response.decode()) if response else {"status": "no-response"}
    finally:
        sock.close()
