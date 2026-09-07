#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packages

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_PREFIX = "/opt/qwm"
CONFIG_DIR = os.path.expanduser("~/.config/qwm")
XSESSION_PATH = "/usr/share/xsessions/qwm.desktop"
QWM_START_PATH = "/usr/bin/qwm-start"
QWMCTL_PATH = "/usr/local/bin/qwmctl"

COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"


class InstallSummary:
    def __init__(self):
        self.installed = []
        self.skipped = []
        self.warnings = []

    def ok(self, msg):
        self.installed.append(msg)
        print(f"{COLOR_GREEN}[OK]{COLOR_RESET} {msg}")

    def skip(self, msg):
        self.skipped.append(msg)
        print(f"{COLOR_YELLOW}[ATLANDI]{COLOR_RESET} {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"{COLOR_RED}[UYARI]{COLOR_RESET} {msg}")

    def info(self, msg):
        print(f"{COLOR_BLUE}[BILGI]{COLOR_RESET} {msg}")

    def print_report(self, uninstalled=False):
        print()
        print(f"{COLOR_BLUE}===== QWM Kurulum Ozeti ====={COLOR_RESET}")
        header = "Kaldirilanlar" if uninstalled else "Kurulanlar"
        print(f"{COLOR_GREEN}{header} ({len(self.installed)}):{COLOR_RESET}")
        for item in self.installed:
            print(f"  - {item}")
        print(f"{COLOR_YELLOW}Atlananlar ({len(self.skipped)}):{COLOR_RESET}")
        for item in self.skipped:
            print(f"  - {item}")
        if self.warnings:
            print(f"{COLOR_RED}Uyarilar ({len(self.warnings)}):{COLOR_RESET}")
            for item in self.warnings:
                print(f"  - {item}")
        print()
        if uninstalled:
            print(f"{COLOR_GREEN}QWM kaldirildi.{COLOR_RESET}")
        else:
            print(f"{COLOR_GREEN}Sonraki adim:{COLOR_RESET} Oturumu kapatip login ekranindan 'QWM' oturumunu secin.")


def require_root():
    return os.geteuid() == 0


def run(cmd, summary=None, check=True, **kwargs):
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except subprocess.CalledProcessError as exc:
        if summary:
            summary.warn(f"komut basarisiz: {' '.join(cmd)} ({exc})")
        raise
    except FileNotFoundError:
        if summary:
            summary.warn(f"komut bulunamadi: {cmd[0]}")
        raise


def install_system_packages(distro, summary):
    pm = packages.get_package_manager(distro)
    if not pm:
        summary.warn(f"desteklenmeyen dagitim: {distro}, sistem paketleri manuel kurulmali")
        return

    generic_names = ["git", "build-tools", "python3", "python3-pip"]
    if distro != "arch":
        generic_names.append("python-xlib")

    if not require_root():
        summary.warn("root yetkisi yok, sistem paketleri atlaniyor (sudo ile tekrar calistirin)")
        return

    try:
        run(pm["update"], summary=summary, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    to_install = [packages.translate_package(distro, name) for name in generic_names]
    try:
        run(pm["install"] + to_install, summary=summary,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        summary.ok(f"sistem paketleri kuruldu: {', '.join(to_install)}")
    except Exception:
        summary.warn("bazi sistem paketleri kurulamadi")


def install_picom(distro, summary):
    if packages.is_installed("picom") or packages.is_installed("picom-jonaburg"):
        summary.skip("picom zaten kurulu")
        return

    if not require_root():
        summary.warn("root yetkisi yok, picom kurulumu atlaniyor")
        return

    pm = packages.get_package_manager(distro)
    if pm and packages.package_available(distro, "picom"):
        try:
            run(pm["install"] + [packages.translate_package(distro, "picom")], summary=summary,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            summary.ok("picom paket deposundan kuruldu")
            return
        except Exception:
            pass

    build_picom_from_source(summary)


def build_picom_from_source(summary):
    if not packages.is_installed("git") or not packages.is_installed("meson"):
        summary.warn("picom kaynak koddan derlenemedi: git/meson eksik")
        return
    with tempfile.TemporaryDirectory() as tmp:
        repo_url = "https://github.com/yshui/picom.git"
        try:
            run(["git", "clone", "--recursive", repo_url, tmp], summary=summary)
            run(["meson", "setup", "--buildtype=release", "build"], cwd=tmp, summary=summary)
            run(["ninja", "-C", "build"], cwd=tmp, summary=summary)
            run(["ninja", "-C", "build", "install"], cwd=tmp, summary=summary)
            summary.ok("picom kaynak koddan derlenip kuruldu")
        except Exception:
            summary.warn("picom kaynak kod derlemesi basarisiz oldu")


def install_or_build(name, distro, summary, build_fn):
    if packages.is_installed(name):
        summary.skip(f"{name} zaten kurulu")
        return

    pm = packages.get_package_manager(distro)
    if require_root() and pm and packages.package_available(distro, name):
        try:
            run(pm["install"] + [packages.translate_package(distro, name)], summary=summary,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            summary.ok(f"{name} paket deposundan kuruldu")
            return
        except Exception:
            pass

    build_fn(summary)


def build_alacritty(summary):
    if not packages.is_installed("cargo"):
        summary.warn("alacritty kaynak koddan derlenemedi: cargo (rust) eksik")
        return
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run(["git", "clone", "https://github.com/alacritty/alacritty.git", tmp], summary=summary)
            run(["cargo", "build", "--release"], cwd=tmp, summary=summary)
            binary = os.path.join(tmp, "target", "release", "alacritty")
            if os.path.exists(binary):
                shutil.copy(binary, "/usr/local/bin/alacritty")
                os.chmod("/usr/local/bin/alacritty", 0o755)
                summary.ok("alacritty kaynak koddan derlenip /usr/local/bin altina kuruldu")
        except Exception:
            summary.warn("alacritty derlemesi basarisiz oldu")


def build_rofi(summary):
    if not packages.is_installed("meson") or not packages.is_installed("ninja"):
        summary.warn("rofi kaynak koddan derlenemedi: meson/ninja eksik")
        return
    with tempfile.TemporaryDirectory() as tmp:
        try:
            run(["git", "clone", "--recursive", "https://github.com/davatorium/rofi.git", tmp], summary=summary)
            run(["meson", "setup", "build"], cwd=tmp, summary=summary)
            run(["ninja", "-C", "build"], cwd=tmp, summary=summary)
            run(["ninja", "-C", "build", "install"], cwd=tmp, summary=summary)
            summary.ok("rofi kaynak koddan derlenip kuruldu")
        except Exception:
            summary.warn("rofi derlemesi basarisiz oldu")


def build_feh_noop(summary):
    summary.warn("feh paket deposunda bulunamadi ve kaynak kod derleme destegi yok, manuel kurun")


def check_nvidia(summary):
    driver = packages.detect_nvidia_driver()
    if driver is False:
        summary.info("NVIDIA GPU tespit edilmedi")
    elif driver is None:
        summary.warn("NVIDIA GPU tespit edildi ancak surucu kurulu degil, kurulum onerilir")
    else:
        summary.ok(f"NVIDIA surucu tespit edildi: {driver}")


def install_python_dependencies(summary):
    requirements = os.path.join(REPO_ROOT, "requirements.txt")
    pip_cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", requirements]
    try:
        run(pip_cmd, summary=summary, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        summary.ok("python bagimliliklari (pip) kuruldu")
        return
    except Exception:
        pass

    if packages.is_installed("pipx"):
        try:
            for pkg in ("python-xlib", "watchdog", "tomli"):
                run(["pipx", "install", "--force", pkg], summary=summary, check=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            summary.ok("python bagimliliklari pipx ile kuruldu")
            return
        except Exception:
            pass
    summary.warn("python bagimliliklari otomatik kurulamadi, manuel 'pip install -r requirements.txt' calistirin")


def copy_qwm_package(summary):
    if not require_root():
        summary.warn(f"root yetkisi yok, {INSTALL_PREFIX} dizinine kopyalama atlaniyor")
        return False
    if os.path.exists(INSTALL_PREFIX):
        shutil.rmtree(INSTALL_PREFIX)
    shutil.copytree(os.path.join(REPO_ROOT, "qwm"), os.path.join(INSTALL_PREFIX, "qwm"))
    shutil.copy(os.path.join(REPO_ROOT, "config.qc"), INSTALL_PREFIX)
    summary.ok(f"qwm paketi {INSTALL_PREFIX} dizinine kopyalandi")
    return True


def setup_user_config(summary):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    target = os.path.join(CONFIG_DIR, "config.qc")
    if os.path.exists(target):
        summary.skip("~/.config/qwm/config.qc zaten var, degistirilmedi")
    else:
        shutil.copy(os.path.join(REPO_ROOT, "config.qc"), target)
        summary.ok("varsayilan config.qc ~/.config/qwm icine kopyalandi")

    wallpaper_src = os.path.join(REPO_ROOT, "assets", "qwm-logo.png")
    wallpaper_dst = os.path.join(CONFIG_DIR, "wallpaper.jpg")
    if os.path.exists(wallpaper_src) and not os.path.exists(wallpaper_dst):
        try:
            shutil.copy(wallpaper_src, wallpaper_dst)
        except Exception:
            pass


def write_qwm_start_script(summary):
    if not require_root():
        summary.warn(f"root yetkisi yok, {QWM_START_PATH} olusturulamadi")
        return
    content = f"""#!/bin/sh
export XDG_SESSION_TYPE=x11
export QWM_HOME="{INSTALL_PREFIX}"
export PYTHONPATH="{INSTALL_PREFIX}:$PYTHONPATH"
exec {sys.executable} -m qwm.main "$@"
"""
    with open(QWM_START_PATH, "w") as f:
        f.write(content)
    os.chmod(QWM_START_PATH, 0o755)
    summary.ok(f"{QWM_START_PATH} olusturuldu")


def write_qwmctl_symlink(summary):
    if not require_root():
        summary.warn("root yetkisi yok, qwmctl kurulumu atlaniyor")
        return
    src = os.path.join(REPO_ROOT, "qwmctl")
    if os.path.exists(QWMCTL_PATH) or os.path.islink(QWMCTL_PATH):
        os.remove(QWMCTL_PATH)
    shutil.copy(src, QWMCTL_PATH)
    os.chmod(QWMCTL_PATH, 0o755)
    summary.ok(f"{QWMCTL_PATH} kuruldu")


def write_xsession_file(summary):
    if not require_root():
        summary.warn(f"root yetkisi yok, {XSESSION_PATH} olusturulamadi")
        return
    src = os.path.join(REPO_ROOT, "installer", "xsession", "qwm.desktop")
    os.makedirs(os.path.dirname(XSESSION_PATH), exist_ok=True)
    shutil.copy(src, XSESSION_PATH)
    summary.ok(f"{XSESSION_PATH} olusturuldu")


def generate_companion_configs(summary):
    colors_path = os.path.join(CONFIG_DIR, "config.qc")
    active = "#89b4fa"
    background = "#1e1e2e"

    rofi_dir = os.path.expanduser("~/.config/rofi")
    os.makedirs(rofi_dir, exist_ok=True)
    rofi_theme = os.path.join(rofi_dir, "qwm-theme.rasi")
    with open(rofi_theme, "w") as f:
        f.write(f"""* {{
    background: {background};
    foreground: #cdd6f4;
    active: {active};
    border-color: {active};
}}
window {{ background-color: @background; border: 2px; border-color: @border-color; border-radius: 12px; }}
element selected {{ background-color: @active; text-color: @background; }}
""")
    summary.ok("rofi temasi olusturuldu: ~/.config/rofi/qwm-theme.rasi")

    alacritty_dir = os.path.expanduser("~/.config/alacritty")
    os.makedirs(alacritty_dir, exist_ok=True)
    alacritty_conf = os.path.join(alacritty_dir, "alacritty.toml")
    if not os.path.exists(alacritty_conf):
        with open(alacritty_conf, "w") as f:
            f.write(f"""[colors.primary]
background = "{background}"
foreground = "#cdd6f4"

[window]
opacity = 0.95
""")
        summary.ok("alacritty.toml olusturuldu: ~/.config/alacritty/alacritty.toml")
    else:
        summary.skip("~/.config/alacritty/alacritty.toml zaten var")


def uninstall(summary):
    if require_root():
        for path in (XSESSION_PATH, QWM_START_PATH, QWMCTL_PATH):
            if os.path.exists(path):
                os.remove(path)
                summary.ok(f"{path} kaldirildi")
        if os.path.exists(INSTALL_PREFIX):
            shutil.rmtree(INSTALL_PREFIX)
            summary.ok(f"{INSTALL_PREFIX} kaldirildi")
    else:
        summary.warn("root yetkisi yok, sistem geneli dosyalar kaldirilamadi")

    if os.path.exists(CONFIG_DIR):
        summary.info(f"kullanici config dizini korunuyor: {CONFIG_DIR} (elle silinebilir)")


def main():
    parser = argparse.ArgumentParser(description="QWM kurulum betigi")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--skip-build", action="store_true", help="kaynak koddan derlemeyi atla")
    args = parser.parse_args()

    summary = InstallSummary()

    if args.uninstall:
        uninstall(summary)
        summary.print_report(uninstalled=True)
        return 0

    distro = packages.detect_distro()
    summary.info(f"tespit edilen dagitim ailesi: {distro}")

    install_system_packages(distro, summary)
    install_picom(distro, summary)

    if not args.skip_build:
        install_or_build("alacritty", distro, summary, build_alacritty)
        install_or_build("rofi", distro, summary, build_rofi)
        install_or_build("feh", distro, summary, build_feh_noop)

    check_nvidia(summary)
    install_python_dependencies(summary)
    copy_qwm_package(summary)
    setup_user_config(summary)
    write_qwm_start_script(summary)
    write_qwmctl_symlink(summary)
    write_xsession_file(summary)
    generate_companion_configs(summary)

    summary.print_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
