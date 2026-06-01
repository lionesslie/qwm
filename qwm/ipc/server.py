import os
import socket
import logging
import threading
from pathlib import Path

logger = logging.getLogger("qwm.ipc.server")

class IPCServer:
    def __init__(self):
        self.socket_path = Path("/tmp/qwm.sock")
        self._running = False
        self._thread = None
        
    def start(self):
        if self.socket_path.exists():
            self.socket_path.unlink()
            
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(self.socket_path))
        self.server.listen(1)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"IPC Server listening on {self.socket_path}")
        
    def stop(self):
        self._running = False
        if self.socket_path.exists():
            self.socket_path.unlink()
            
    def _loop(self):
        while self._running:
            try:
                self.server.settimeout(1.0)
                conn, _ = self.server.accept()
                with conn:
                    data = conn.recv(1024)
                    if data:
                        cmd = data.decode('utf-8').strip()
                        logger.debug(f"IPC received: {cmd}")
                        conn.sendall(b"OK\n")
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"IPC Error: {e}")
