#!/usr/bin/env python3
"""
QWM Kurulum Betigi
===================
    sudo python3 install.py              # kur
    sudo python3 install.py --uninstall  # kaldir
"""
import argparse
import os
import pwd
import shutil
import subprocess
import sys

INSTALL_DIR = "/opt/qwm"
BIN_WRAPPER = "/usr/bin/qwm"
SESSION_SCRIPT = "/usr/bin/qwm-session"
DESKTOP_FILE = "/usr/share/xsessions/qwm.desktop"
SKEL_CONFIG_DIR = "/etc/skel/.config/qwm"
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd)


def require_root():
    if os.geteuid() != 0:
        sys.exit("HATA: sudo ile calistirin -> sudo python3 install.py")


def detect_package_manager():
    for pm in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(pm):
            return pm
    return None


def install_dependencies():
    pm = detect_package_manager()
    print(f"[*] Paket yoneticisi: {pm or 'bulunamadi'}")
    if pm is None:
        print("[!] Elle kurun: python3-xlib, xterm, dmenu, lightdm")
        return

    packages = {
        "apt-get": ["python3", "python3-pip", "python3-xlib", "xterm", "dmenu",
                    "lightdm", "lightdm-gtk-greeter"],
        "dnf":     ["python3", "python3-pip", "python3-xlib", "xterm", "dmenu", "lightdm"],
        "pacman":  ["python", "python-pip", "python-xlib", "xterm", "dmenu",
                    "lightdm", "lightdm-gtk-greeter"],
        "zypper":  ["python3", "python3-pip", "python3-Xlib", "xterm", "dmenu", "lightdm"],
    }[pm]

    print("[*] Bagimliliklar kuruluyor...")
    if pm == "apt-get":
        run(["apt-get", "update"]); run(["apt-get", "install", "-y", *packages])
    elif pm == "dnf":
        run(["dnf", "install", "-y", *packages])
    elif pm == "pacman":
        run(["pacman", "-Sy", "--noconfirm", *packages])
    elif pm == "zypper":
        run(["zypper", "--non-interactive", "install", *packages])

    run([sys.executable, "-m", "pip", "install", "--break-system-packages", "python-xlib"])


def copy_project_files():
    print(f"[*] Kopyalaniyor -> {INSTALL_DIR}")
    if os.path.isdir(INSTALL_DIR):
        shutil.rmtree(INSTALL_DIR)
    shutil.copytree(os.path.join(HERE, "qwm"), os.path.join(INSTALL_DIR, "qwm"))


def write_wrapper():
    with open(BIN_WRAPPER, "w") as f:
        f.write(f'#!/usr/bin/env bash\nexport PYTHONPATH="{INSTALL_DIR}:$PYTHONPATH"\nexec python3 -m qwm "$@"\n')
    os.chmod(BIN_WRAPPER, 0o755)
    print(f"[*] Olusturuldu: {BIN_WRAPPER}")


def write_session_script():
    with open(SESSION_SCRIPT, "w") as f:
        f.write(f"""#!/usr/bin/env bash
# QWM - LightDM oturum baslatici
export PYTHONPATH="{INSTALL_DIR}:$PYTHONPATH"
export __GL_SYNC_TO_VBLANK="${{__GL_SYNC_TO_VBLANK:-0}}"
export __GL_YIELD="${{__GL_YIELD:-USLEEP}}"
exec python3 -m qwm
""")
    os.chmod(SESSION_SCRIPT, 0o755)
    print(f"[*] Olusturuldu: {SESSION_SCRIPT}")


def write_desktop_entry():
    os.makedirs(os.path.dirname(DESKTOP_FILE), exist_ok=True)
    with open(DESKTOP_FILE, "w") as f:
        f.write(f"""[Desktop Entry]
Name=QWM
Comment=NVIDIA icin optimize edilmis Python tabanli tiling pencere yoneticisi
Exec={SESSION_SCRIPT}
TryExec={SESSION_SCRIPT}
Type=Application
DesktopNames=QWM
""")
    print(f"[*] LightDM oturumu eklendi: {DESKTOP_FILE}")


def install_default_config_for(home_dir, uid, gid):
    cfg_dir = os.path.join(home_dir, ".config", "qwm")
    cfg_path = os.path.join(cfg_dir, "config.py")
    os.makedirs(cfg_dir, exist_ok=True)
    if not os.path.exists(cfg_path):
        shutil.copy(os.path.join(HERE, "qwm", "default_config.py"), cfg_path)
        os.chown(cfg_dir, uid, gid)
        os.chown(cfg_path, uid, gid)
        print(f"[*] Ornek config: {cfg_path}")


def setup_user_configs():
    os.makedirs(SKEL_CONFIG_DIR, exist_ok=True)
    shutil.copy(os.path.join(HERE, "qwm", "default_config.py"),
                os.path.join(SKEL_CONFIG_DIR, "config.py"))

    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        pw = pwd.getpwnam(sudo_user)
        install_default_config_for(pw.pw_dir, pw.pw_uid, pw.pw_gid)


def install():
    require_root()
    print("=== QWM Kurulumu ===")
    install_dependencies()
    copy_project_files()
    write_wrapper()
    write_session_script()
    write_desktop_entry()
    setup_user_configs()
    print("""
=== Kurulum Tamamlandi! ===
1) Once test edin (onerilir):
     ./test-xephyr.sh
2) Sorunsuzsa oturumu kapatin, LightDM'de "QWM" oturumunu secin.

Config: ~/.config/qwm/config.py
Log:    ~/.local/share/qwm/qwm.log

ONEMLI: Guvenlik agi olarak baska bir WM'i de kurulu tutun (orn: openbox),
QWM sorun cikarirsa LightDM oturum seciciden ona gecebilirsiniz.
""")


def uninstall():
    require_root()
    for path in (BIN_WRAPPER, SESSION_SCRIPT, DESKTOP_FILE):
        if os.path.exists(path):
            os.remove(path)
            print(f"  silindi: {path}")
    if os.path.isdir(INSTALL_DIR):
        shutil.rmtree(INSTALL_DIR)
        print(f"  silindi: {INSTALL_DIR}")
    print("QWM kaldirildi. (~/.config/qwm/config.py korundu)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    uninstall() if args.uninstall else install()