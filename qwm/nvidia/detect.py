import os
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False

logger = logging.getLogger("qwm.nvidia.detect")

@dataclass
class NvidiaCapabilityMatrix:
    gpu_name: str
    driver_version: str
    cuda_version: str
    vram_total_mb: int
    architecture: str
    supports_gsync: bool
    supports_vrr: bool
    supports_dlss: bool
    supports_reflex: bool
    max_clocks_mhz: Dict[str, int]
    tdp_watts: int
    pcie_gen: int
    pcie_width: int

def is_nvidia_loaded() -> bool:
    """Check if nvidia kernel module is loaded via /proc/modules."""
    try:
        with open("/proc/modules", "r") as f:
            for line in f:
                if line.startswith("nvidia "):
                    return True
    except FileNotFoundError:
        pass
    return False

def build_capability_matrix() -> Optional[NvidiaCapabilityMatrix]:
    """Initialize NVML and build the GPU capability matrix."""
    if not is_nvidia_loaded():
        logger.warning("NVIDIA kernel module not loaded. NVIDIA optimizations disabled.")
        return None
        
    if not HAS_PYNVML:
        logger.warning("pynvml not installed. Cannot query GPU capabilities.")
        return None
        
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            logger.warning("NVML initialized but no NVIDIA GPUs found.")
            return None
            
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode('utf-8')
            
        driver_version = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver_version, bytes):
            driver_version = driver_version.decode('utf-8')
            
        try:
            cuda_version_int = pynvml.nvmlSystemGetCudaDriverVersion()
            cuda_version = f"{cuda_version_int // 1000}.{(cuda_version_int % 100) // 10}"
        except pynvml.NVMLError:
            cuda_version = "Unknown"
            
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_total_mb = mem_info.total // (1024 * 1024)
        
        try:
            power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle)
            tdp_watts = power_limit // 1000
        except pynvml.NVMLError:
            tdp_watts = 0
            
        try:
            pcie_gen = pynvml.nvmlDeviceGetMaxPcieLinkGeneration(handle)
            pcie_width = pynvml.nvmlDeviceGetMaxPcieLinkWidth(handle)
        except pynvml.NVMLError:
            pcie_gen = 0
            pcie_width = 0
            
        try:
            max_graphics_clock = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
            max_mem_clock = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_MEM)
            max_clocks_mhz = {"graphics": max_graphics_clock, "memory": max_mem_clock}
        except pynvml.NVMLError:
            max_clocks_mhz = {"graphics": 0, "memory": 0}

        # Simplified Architecture string logic
        arch = "Unknown"
        if "RTX 40" in name: arch = "Ada Lovelace"
        elif "RTX 30" in name: arch = "Ampere"
        elif "RTX 20" in name or "GTX 16" in name: arch = "Turing"
        elif "GTX 10" in name: arch = "Pascal"
        elif "GTX 9" in name: arch = "Maxwell"

        supports_dlss = arch in ["Turing", "Ampere", "Ada Lovelace"]
        supports_reflex = arch in ["Turing", "Ampere", "Ada Lovelace"] or "GTX 9" in name
        
        # G-Sync / VRR support requires querying X / nvidia-settings which is done later
        supports_gsync = False
        supports_vrr = False

        matrix = NvidiaCapabilityMatrix(
            gpu_name=name,
            driver_version=driver_version,
            cuda_version=cuda_version,
            vram_total_mb=vram_total_mb,
            architecture=arch,
            supports_gsync=supports_gsync,
            supports_vrr=supports_vrr,
            supports_dlss=supports_dlss,
            supports_reflex=supports_reflex,
            max_clocks_mhz=max_clocks_mhz,
            tdp_watts=tdp_watts,
            pcie_gen=pcie_gen,
            pcie_width=pcie_width
        )
        
        logger.info(f"NVIDIA Capability Matrix Built: {matrix.gpu_name} (Driver {matrix.driver_version})")
        return matrix
        
    except pynvml.NVMLError as e:
        logger.error(f"NVML Error during detection: {e}")
        return None
