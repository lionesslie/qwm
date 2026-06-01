import threading
import time
import logging
from dataclasses import dataclass
from typing import Optional

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

logger = logging.getLogger("qwm.nvidia.nvml")

@dataclass
class NvidiaMetrics:
    gpu_utilization_percent: int
    memory_used_mb: int
    temperature_celsius: int
    power_draw_watts: float
    graphics_clock_mhz: int
    memory_clock_mhz: int
    fan_speed_percent: int
    pcie_throughput_rx: int
    pcie_throughput_tx: int
    performance_state: str

class NvmlMonitor:
    """Background thread for real-time GPU metrics."""
    
    def __init__(self, poll_interval_ms: int = 2000):
        self.poll_interval = poll_interval_ms / 1000.0
        self.game_mode_interval = 0.5
        self.in_game_mode = False
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._metrics: Optional[NvidiaMetrics] = None
        self._handle = None
        
        if HAS_PYNVML:
            try:
                pynvml.nvmlInit()
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            except pynvml.NVMLError as e:
                logger.error(f"Failed to initialize NVML monitor: {e}")
                self._handle = None
                
    def start(self):
        if not self._handle:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("NVML Monitor thread started")
        
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
            
    def set_game_mode(self, active: bool):
        self.in_game_mode = active
            
    def snapshot(self) -> Optional[NvidiaMetrics]:
        with self._lock:
            return self._metrics
            
    def _monitor_loop(self):
        while self._running:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self._handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
                temp = pynvml.nvmlDeviceGetTemperature(self._handle, pynvml.NVML_TEMPERATURE_GPU)
                
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(self._handle) / 1000.0
                except pynvml.NVMLError:
                    power = 0.0
                    
                gclock = pynvml.nvmlDeviceGetClockInfo(self._handle, pynvml.NVML_CLOCK_GRAPHICS)
                mclock = pynvml.nvmlDeviceGetClockInfo(self._handle, pynvml.NVML_CLOCK_MEM)
                
                try:
                    fan = pynvml.nvmlDeviceGetFanSpeed(self._handle)
                except pynvml.NVMLError:
                    fan = 0
                    
                try:
                    tx = pynvml.nvmlDeviceGetPcieThroughput(self._handle, pynvml.NVML_PCIE_UTIL_TX_BYTES)
                    rx = pynvml.nvmlDeviceGetPcieThroughput(self._handle, pynvml.NVML_PCIE_UTIL_RX_BYTES)
                except pynvml.NVMLError:
                    tx, rx = 0, 0
                    
                try:
                    pstate = pynvml.nvmlDeviceGetPerformanceState(self._handle)
                    pstate_str = f"P{pstate}"
                except pynvml.NVMLError:
                    pstate_str = "Unknown"
                    
                metrics = NvidiaMetrics(
                    gpu_utilization_percent=util.gpu,
                    memory_used_mb=mem.used // (1024 * 1024),
                    temperature_celsius=temp,
                    power_draw_watts=power,
                    graphics_clock_mhz=gclock,
                    memory_clock_mhz=mclock,
                    fan_speed_percent=fan,
                    pcie_throughput_rx=rx,
                    pcie_throughput_tx=tx,
                    performance_state=pstate_str
                )
                
                with self._lock:
                    self._metrics = metrics
                    
                # Threshold events
                if temp > 95:
                    logger.critical(f"GPU Temperature CRITICAL: {temp}°C")
                elif temp > 85:
                    logger.warning(f"GPU Temperature HIGH: {temp}°C")
                    
            except pynvml.NVMLError as e:
                logger.error(f"NVML polling error: {e}")
                
            sleep_time = self.game_mode_interval if self.in_game_mode else self.poll_interval
            time.sleep(sleep_time)
