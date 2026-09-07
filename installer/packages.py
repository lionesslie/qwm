import os
import re
import shutil
import subprocess


def read_os_release():
    data = {}
    path = "/etc/os-release"
    if not os.path.exists(path):
        return data
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key] = value.strip('"')
    return data


DISTRO_FAMILIES = {
    "arch": {"pacman"},
    "debian": {"debian", "ubuntu", "linuxmint", "pop"},
    "fedora": {"fedora", "rhel", "centos", "rocky", "almalinux"},
    "opensuse": {"opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"},
}


def detect_distro():
    info = read_os_release()
    id_like = (info.get("ID_LIKE", "") + " " + info.get("ID", "")).lower()
    distro_id = info.get("ID", "").lower()

    if "arch" in id_like or distro_id == "arch" or distro_id == "manjaro":
        return "arch"
    if any(name in id_like for name in DISTRO_FAMILIES["debian"]) or distro_id in DISTRO_FAMILIES["debian"]:
        return "debian"
    if any(name in id_like for name in DISTRO_FAMILIES["fedora"]) or distro_id in DISTRO_FAMILIES["fedora"]:
        return "fedora"
    if "suse" in id_like or "suse" in distro_id:
        return "opensuse"
    return "unknown"


PACKAGE_MANAGERS = {
    "arch": {
        "bin": "pacman",
        "install": ["pacman", "-S", "--noconfirm", "--needed"],
        "update": ["pacman", "-Sy"],
    },
    "debian": {
        "bin": "apt-get",
        "install": ["apt-get", "install", "-y"],
        "update": ["apt-get", "update"],
    },
    "fedora": {
        "bin": "dnf",
        "install": ["dnf", "install", "-y"],
        "update": ["dnf", "check-update"],
    },
    "opensuse": {
        "bin": "zypper",
        "install": ["zypper", "install", "-y"],
        "update": ["zypper", "refresh"],
    },
}

PACKAGE_NAME_MAP = {
    "arch": {
        "python-xlib": "python-xlib",
        "picom": "picom",
        "git": "git",
        "build-tools": "base-devel",
        "alacritty": "alacritty",
        "rofi": "rofi",
        "feh": "feh",
        "i3lock": "i3lock",
        "python3": "python",
        "python3-pip": "python-pip",
        "cargo": "cargo",
        "meson": "meson",
        "ninja": "ninja",
    },
    "debian": {
        "python-xlib": "python3-xlib",
        "picom": "picom",
        "git": "git",
        "build-tools": "build-essential",
        "alacritty": "alacritty",
        "rofi": "rofi",
        "feh": "feh",
        "i3lock": "i3lock",
        "python3": "python3",
        "python3-pip": "python3-pip",
        "cargo": "cargo",
        "meson": "meson",
        "ninja": "ninja-build",
    },
    "fedora": {
        "python-xlib": "python3-xlib",
        "picom": "picom",
        "git": "git",
        "build-tools": "@development-tools",
        "alacritty": "alacritty",
        "rofi": "rofi",
        "feh": "feh",
        "i3lock": "i3lock",
        "python3": "python3",
        "python3-pip": "python3-pip",
        "cargo": "cargo",
        "meson": "meson",
        "ninja": "ninja-build",
    },
    "opensuse": {
        "python-xlib": "python3-xlib",
        "picom": "picom",
        "git": "git",
        "build-tools": "patterns-devel-base-devel_basis",
        "alacritty": "alacritty",
        "rofi": "rofi",
        "feh": "feh",
        "i3lock": "i3lock",
        "python3": "python3",
        "python3-pip": "python3-pip",
        "cargo": "cargo",
        "meson": "meson",
        "ninja": "ninja",
    },
}


def get_package_manager(distro):
    return PACKAGE_MANAGERS.get(distro)


def translate_package(distro, generic_name):
    return PACKAGE_NAME_MAP.get(distro, {}).get(generic_name, generic_name)


def package_available(distro, generic_name):
    pkg = translate_package(distro, generic_name)
    pm = get_package_manager(distro)
    if not pm:
        return False
    try:
        if distro == "arch":
            out = subprocess.run(["pacman", "-Si", pkg], capture_output=True, timeout=10)
            return out.returncode == 0
        if distro == "debian":
            out = subprocess.run(["apt-cache", "show", pkg], capture_output=True, timeout=10)
            return out.returncode == 0 and out.stdout.strip() != b""
        if distro == "fedora":
            out = subprocess.run(["dnf", "info", pkg], capture_output=True, timeout=15)
            return out.returncode == 0
        if distro == "opensuse":
            out = subprocess.run(["zypper", "info", pkg], capture_output=True, timeout=15)
            return out.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return False


def is_installed(binary_name):
    return shutil.which(binary_name) is not None


def detect_display_manager():
    candidates = {
        "gdm": ["gdm3", "gdm"],
        "sddm": ["sddm"],
        "lightdm": ["lightdm"],
    }
    for dm_name, services in candidates.items():
        for service in services:
            unit_path = f"/lib/systemd/system/{service}.service"
            alt_path = f"/usr/lib/systemd/system/{service}.service"
            if os.path.exists(unit_path) or os.path.exists(alt_path):
                return dm_name, service
    return None, None


def detect_nvidia_driver():
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], timeout=5)
            return out.decode().strip()
        except Exception:
            return "unknown"
    try:
        lspci = subprocess.check_output(["lspci"], timeout=5).decode()
        if "NVIDIA" in lspci:
            return None
    except Exception:
        pass
    return False
