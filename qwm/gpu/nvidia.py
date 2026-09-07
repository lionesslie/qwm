import shutil
import subprocess
import logging

logger = logging.getLogger("qwm.gpu.nvidia")


def has_nvidia():
    return shutil.which("nvidia-smi") is not None


def has_nvidia_settings():
    return shutil.which("nvidia-settings") is not None


def get_gpu_info():
    if not has_nvidia():
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version,temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            timeout=3,
        ).decode().strip()
        name, driver, temp, util = [p.strip() for p in out.split(",")]
        return {"name": name, "driver": driver, "temp_c": int(temp), "util_pct": int(util)}
    except Exception:
        logger.debug("nvidia-smi bilgisi alinamadi", exc_info=True)
        return None


def get_temperature():
    info = get_gpu_info()
    return info["temp_c"] if info else None


def is_prime_optimus():
    try:
        out = subprocess.check_output(["lspci"], timeout=3).decode()
        gpu_lines = [l for l in out.splitlines() if "VGA" in l or "3D controller" in l]
        vendors = set()
        for line in gpu_lines:
            if "NVIDIA" in line:
                vendors.add("nvidia")
            elif "Intel" in line:
                vendors.add("intel")
            elif "AMD" in line or "ATI" in line:
                vendors.add("amd")
        return "nvidia" in vendors and len(vendors) > 1
    except Exception:
        return False


def env_for_performance():
    return {
        "__GL_YIELD": "USLEEP",
        "__GL_SYNC_TO_VBLANK": "1",
    }


def env_for_prime_offload():
    return {
        "__NV_PRIME_RENDER_OFFLOAD": "1",
        "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
        "__VK_LAYER_NV_optimus": "NVIDIA_only",
    }


def nvidia_offload_command(command_args):
    env_pairs = env_for_prime_offload()
    return command_args, env_pairs


def apply_force_composition_pipeline(dry_run=True):
    if not has_nvidia_settings():
        logger.warning("nvidia-settings bulunamadi, force composition pipeline atlandi")
        return False
    try:
        query = subprocess.check_output(
            ["nvidia-settings", "-q", "CurrentMetaMode", "-t"],
            timeout=3,
        ).decode()
    except Exception:
        logger.warning("mevcut metamode okunamadi")
        return False

    if "ForceFullCompositionPipeline" in query:
        logger.info("ForceFullCompositionPipeline zaten aktif")
        return True

    if dry_run:
        logger.info("oneri: nvidia-settings ile metamode 'ForceFullCompositionPipeline=On' eklenmeli (sudo gerekebilir)")
        return False

    new_mode = query.strip()
    if "ForceFullCompositionPipeline" not in new_mode:
        new_mode = new_mode.rstrip("} ") + ", ForceFullCompositionPipeline=On}"
    try:
        subprocess.check_call(
            ["nvidia-settings", "--assign", f"CurrentMetaMode={new_mode}"],
            timeout=5,
        )
        return True
    except Exception:
        logger.exception("force composition pipeline uygulanamadi")
        return False


def check_xorg_conf_recommendations():
    recommendations = [
        'Option "TripleBuffer" "True"',
        'Option "AllowIndirectGLXProtocol" "off"',
        'Option "metamodes" "... ForceFullCompositionPipeline=On"',
    ]
    return recommendations


class NvidiaOptimizer:
    def __init__(self, config):
        self.config = config
        self.available = has_nvidia()
        self.is_optimus = is_prime_optimus() if self.available else False

    def bootstrap(self):
        if not self.available:
            logger.info("NVIDIA GPU bulunamadi, optimizasyon atlanacak")
            return
        info = get_gpu_info()
        if info:
            logger.info("NVIDIA GPU: %s (driver %s)", info["name"], info["driver"])
        if self.config.get("force_composition_pipeline", True):
            apply_force_composition_pipeline(dry_run=True)

    def compositor_overrides(self):
        if not self.available:
            return {}
        return {
            "backend": "glx",
            "vsync": True,
            "glx_no_stencil": True,
            "glx_no_rebind_pixmap": True,
        }
