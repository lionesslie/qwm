#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import argparse
import tempfile
import glob

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


def deploy_bundled_configs(summary):
    bundle_root = os.path.join(REPO_ROOT, "configs")
    if not os.path.isdir(bundle_root):
        return

    home_config = os.path.expanduser("~/.config")
    copied, skipped = 0, 0

    for dirpath, _, filenames in os.walk(bundle_root):
        rel_dir = os.path.relpath(dirpath, bundle_root)
        dest_dir = home_config if rel_dir == "." else os.path.join(home_config, rel_dir)
        os.makedirs(dest_dir, exist_ok=True)
        for filename in filenames:
            src = os.path.join(dirpath, filename)
            dst = os.path.join(dest_dir, filename)
            if os.path.exists(dst):
                skipped += 1
                continue
            shutil.copy(src, dst)
            if filename.endswith(".sh"):
                os.chmod(dst, 0o755)
            copied += 1

    if copied:
        summary.ok(f"configs/ paketi ~/.config icine kopyalandi ({copied} dosya)")
    if skipped:
        summary.skip(f"configs/ icindeki {skipped} dosya zaten mevcut oldugu icin atlandi")


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


def resolve_target_user(cfg_user):
    if cfg_user:
        return cfg_user
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        return sudo_user
    return os.environ.get("USER", "root")


def setup_autologin_gdm(user, summary):
    for path in ("/etc/gdm3/custom.conf", "/etc/gdm/custom.conf"):
        if os.path.exists(os.path.dirname(path)):
            lines = []
            if os.path.exists(path):
                with open(path) as f:
                    lines = f.readlines()
            lines = [l for l in lines if not l.strip().startswith(("AutomaticLoginEnable", "AutomaticLogin="))]
            if "[daemon]" not in "".join(lines):
                lines.append("[daemon]\n")
            out = []
            in_daemon = False
            for line in lines:
                out.append(line)
                if line.strip() == "[daemon]":
                    in_daemon = True
                    out.append("AutomaticLoginEnable=True\n")
                    out.append(f"AutomaticLogin={user}\n")
            with open(path, "w") as f:
                f.writelines(out)
            summary.ok(f"GDM autologin ayarlandi: {path}")
            return True
    summary.warn("GDM config dizini bulunamadi, autologin ayarlanamadi")
    return False


def setup_autologin_sddm(user, summary):
    conf_dir = "/etc/sddm.conf.d"
    os.makedirs(conf_dir, exist_ok=True)
    path = os.path.join(conf_dir, "qwm-autologin.conf")
    with open(path, "w") as f:
        f.write(f"[Autologin]\nUser={user}\nSession=qwm.desktop\n")
    summary.ok(f"SDDM autologin ayarlandi: {path}")
    return True


def setup_autologin_lightdm(user, summary):
    conf_dir = "/etc/lightdm/lightdm.conf.d"
    if not os.path.exists("/etc/lightdm"):
        summary.warn("lightdm config dizini bulunamadi")
        return False
    os.makedirs(conf_dir, exist_ok=True)
    path = os.path.join(conf_dir, "50-qwm-autologin.conf")
    with open(path, "w") as f:
        f.write(f"[Seat:*]\nautologin-user={user}\nautologin-session=qwm\n")
    summary.ok(f"LightDM autologin ayarlandi: {path}")
    return True


def setup_autologin_tty(user, tty, summary):
    override_dir = f"/etc/systemd/system/getty@tty{tty}.service.d"
    os.makedirs(override_dir, exist_ok=True)
    override_path = os.path.join(override_dir, "autologin.conf")
    with open(override_path, "w") as f:
        f.write(
            "[Service]\n"
            "ExecStart=\n"
            f"ExecStart=-/sbin/agetty --autologin {user} --noclear %I $TERM\n"
        )
    summary.ok(f"tty{tty} autologin ayarlandi: {override_path}")

    profile_path = os.path.expanduser(f"~{user}/.bash_profile")
    snippet = (
        "\nif [ -z \"$DISPLAY\" ] && [ \"$(tty)\" = \"/dev/tty%s\" ]; then\n"
        "    exec startx\n"
        "fi\n" % tty
    )
    try:
        existing = ""
        if os.path.exists(profile_path):
            with open(profile_path) as f:
                existing = f.read()
        if "exec startx" not in existing:
            with open(profile_path, "a") as f:
                f.write(snippet)
            summary.ok(f".bash_profile guncellendi: {profile_path}")
        else:
            summary.skip(".bash_profile zaten startx cagrisi iceriyor")
    except OSError:
        summary.warn(f"{profile_path} yazilamadi, kullanici home dizinini kontrol edin")

    xinitrc_path = os.path.expanduser(f"~{user}/.xinitrc")
    if not os.path.exists(xinitrc_path):
        with open(xinitrc_path, "w") as f:
            f.write("#!/bin/sh\nexec /usr/bin/qwm-start\n")
        os.chmod(xinitrc_path, 0o755)
        summary.ok(f".xinitrc olusturuldu: {xinitrc_path}")
    else:
        summary.skip(".xinitrc zaten var, degistirilmedi")

    try:
        run(["systemctl", "daemon-reload"], summary=summary, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return True


def setup_system_autologin(cfg, summary):
    if not require_root():
        summary.warn("root yetkisi yok, sistem autologin ayarlanamadi")
        return

    user = resolve_target_user(cfg.get("target_user", ""))
    method = cfg.get("method", "display_manager")

    if method == "tty":
        setup_autologin_tty(user, cfg.get("tty", 1), summary)
        return

    dm_name, service = packages.detect_display_manager()
    if not dm_name:
        summary.warn("desteklenen bir display manager bulunamadi, tty yontemine dusuluyor")
        setup_autologin_tty(user, cfg.get("tty", 1), summary)
        return

    if dm_name == "gdm":
        setup_autologin_gdm(user, summary)
    elif dm_name == "sddm":
        setup_autologin_sddm(user, summary)
    elif dm_name == "lightdm":
        setup_autologin_lightdm(user, summary)

    try:
        run(["systemctl", "enable", service], summary=summary, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


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


def cleanup_autologin(summary):
    candidates = [
        "/etc/sddm.conf.d/qwm-autologin.conf",
        "/etc/lightdm/lightdm.conf.d/50-qwm-autologin.conf",
    ]
    for path in candidates:
        if os.path.exists(path):
            os.remove(path)
            summary.ok(f"{path} kaldirildi")

    for tty_conf in glob.glob("/etc/systemd/system/getty@tty*.service.d/autologin.conf"):
        os.remove(tty_conf)
        parent = os.path.dirname(tty_conf)
        if not os.listdir(parent):
            os.rmdir(parent)
        summary.ok(f"{tty_conf} kaldirildi")

    for gdm_path in ("/etc/gdm3/custom.conf", "/etc/gdm/custom.conf"):
        if os.path.exists(gdm_path):
            with open(gdm_path) as f:
                lines = f.readlines()
            new_lines = [l for l in lines if not l.strip().startswith(("AutomaticLoginEnable", "AutomaticLogin="))]
            if new_lines != lines:
                with open(gdm_path, "w") as f:
                    f.writelines(new_lines)
                summary.ok(f"{gdm_path} icindeki qwm autologin satirlari kaldirildi")


def uninstall(summary):
    if require_root():
        for path in (XSESSION_PATH, QWM_START_PATH, QWMCTL_PATH):
            if os.path.exists(path):
                os.remove(path)
                summary.ok(f"{path} kaldirildi")
        if os.path.exists(INSTALL_PREFIX):
            shutil.rmtree(INSTALL_PREFIX)
            summary.ok(f"{INSTALL_PREFIX} kaldirildi")
        cleanup_autologin(summary)
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
    deploy_bundled_configs(summary)
    write_qwm_start_script(summary)
    write_qwmctl_symlink(summary)
    write_xsession_file(summary)
    generate_companion_configs(summary)

    try:
        sys.path.insert(0, INSTALL_PREFIX)
        from qwm.config.loader import load_config
        final_config, _ = load_config(os.path.join(CONFIG_DIR, "config.qc"))
        if final_config.get("system_autologin", {}).get("enabled"):
            setup_system_autologin(final_config["system_autologin"], summary)
        else:
            summary.info("system_autologin.enabled = false, otomatik giris atlandi")
    except Exception:
        summary.warn("config okunamadigindan system_autologin uygulanamadi")

    summary.print_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
