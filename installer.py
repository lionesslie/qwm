#!/usr/bin/env python3
import os
import shutil
import subprocess
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".config", "qwm")


def run(cmd, sudo=False):
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    print(">> " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def detect_pm():
    if shutil.which("apt-get"):
        return "apt"
    if shutil.which("pacman"):
        return "pacman"
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("zypper"):
        return "zypper"
    return None


def install_packages(pm):
    packages = {
        "apt": ["golang-go", "git", "alacritty", "rofi", "feh", "picom",
                "build-essential", "libx11-dev", "x11-xserver-utils"],
        "pacman": ["go", "git", "alacritty", "rofi", "feh", "picom",
                   "base-devel", "xorg-xrandr", "xorg-xset"],
        "dnf": ["golang", "git", "alacritty", "rofi", "feh", "picom",
                "xorg-x11-server-utils"],
        "zypper": ["go", "git", "alacritty", "rofi", "feh", "picom",
                   "xrandr", "xset"],
    }
    if pm == "apt":
        run(["apt-get", "update"], sudo=True)
        run(["apt-get", "install", "-y"] + packages["apt"], sudo=True)
    elif pm == "pacman":
        run(["pacman", "-Sy", "--noconfirm"] + packages["pacman"], sudo=True)
    elif pm == "dnf":
        run(["dnf", "install", "-y"] + packages["dnf"], sudo=True)
    elif pm == "zypper":
        run(["zypper", "install", "-y"] + packages["zypper"], sudo=True)
    else:
        print("Paket yoneticisi bulunamadi, bagimliliklari manuel kurun.")


def build_qwm():
    print("QWM derleniyor...")
    subprocess.run(["go", "mod", "tidy"], cwd=PROJECT_DIR, check=True)
    subprocess.run(["go", "build", "-o", "qwm", "."], cwd=PROJECT_DIR, check=True)
    binary = os.path.join(PROJECT_DIR, "qwm")
    subprocess.run(["sudo", "pkill", "-9", "qwm"], check=False)
    time.sleep(1)
    run(["cp", binary, "/usr/local/bin/qwm"], sudo=True)
    run(["chmod", "+x", "/usr/local/bin/qwm"], sudo=True)


def install_launcher_script():
    script = "#!/bin/bash\nexport XDG_CURRENT_DESKTOP=QWM\nexec /usr/local/bin/qwm\n"
    tmp = "/tmp/qwm-start"
    with open(tmp, "w") as f:
        f.write(script)
    run(["cp", tmp, "/usr/local/bin/qwm-start"], sudo=True)
    run(["chmod", "+x", "/usr/local/bin/qwm-start"], sudo=True)


def install_xsession():
    content = (
        "[Desktop Entry]\n"
        "Name=QWM\n"
        "Comment=Go tabanli tiling pencere yoneticisi\n"
        "Exec=/usr/local/bin/qwm-start\n"
        "Type=Application\n"
    )
    tmp = "/tmp/qwm-xsession.desktop"
    with open(tmp, "w") as f:
        f.write(content)
    run(["mkdir", "-p", "/usr/share/xsessions"], sudo=True)
    run(["cp", tmp, "/usr/share/xsessions/qwm.desktop"], sudo=True)


def install_app_launcher():
    apps_dir = os.path.join(HOME, ".local", "share", "applications")
    os.makedirs(apps_dir, exist_ok=True)
    content = (
        "[Desktop Entry]\n"
        "Name=QWM Baslat\n"
        "Comment=QWM tiling pencere yoneticisini baslat\n"
        "Exec=/usr/local/bin/qwm-start\n"
        "Icon=preferences-system-windows\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=System;Utility;\n"
    )
    with open(os.path.join(apps_dir, "qwm.desktop"), "w") as f:
        f.write(content)


def parse_sections(content):
    sections = {}
    current = "__preamble__"
    sections[current] = []
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
            sections.setdefault(current, [])
        sections[current].append(line)
    return sections


def install_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    target = os.path.join(CONFIG_DIR, "config.qc")
    source = os.path.join(PROJECT_DIR, "config.qc")

    if not os.path.exists(target):
        shutil.copy(source, target)
        print("Config olusturuldu: " + target)
        return

    with open(source, "r", encoding="utf-8") as f:
        template_content = f.read()
    with open(target, "r", encoding="utf-8") as f:
        user_content = f.read()

    template_sections = parse_sections(template_content)
    user_sections = parse_sections(user_content)

    missing_blocks = []
    for header, lines in template_sections.items():
        if header == "__preamble__":
            continue
        if header not in user_sections:
            missing_blocks.append("".join(lines))

    if missing_blocks:
        backup = target + ".bak"
        shutil.copy(target, backup)
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n# --- QWM guncellemesiyle eklenen yeni ayarlar ---\n")
            for block in missing_blocks:
                f.write("\n" + block)
        print("config.qc guncellendi, eksik bolumler eklendi. Yedek: " + backup)
    else:
        print("config.qc zaten guncel.")


def main():
    print("=== QWM Kurulum Sihirbazi ===")
    pm = detect_pm()
    if pm is None:
        print("Desteklenen paket yoneticisi bulunamadi.")
    else:
        install_packages(pm)
    if not shutil.which("go"):
        print("UYARI: Go bulunamadi, derleme basarisiz olabilir.")
    build_qwm()
    install_launcher_script()
    install_xsession()
    install_app_launcher()
    install_config()
    print("")
    print("Kurulum tamamlandi!")
    print("Log dosyasi: ~/.cache/qwm/qwm.log")
    print("Ayarlar: ~/.config/qwm/config.qc")


if __name__ == "__main__":
    main()