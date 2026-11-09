#!/usr/bin/env bash
#
# build.sh - qwm'i derler ve (istege bagli) sisteme kurar.
#
# Kurulum, qwm'i bir display manager'in (SDDM, LightDM, GDM, ...) oturum
# listesinde gorunur hale getirir: binary'ler $PREFIX altina (varsayilan
# /usr/local/bin), oturum dosyasi /usr/share/xsessions/qwm.desktop altina
# kopyalanir. Derleme HER ZAMAN mevcut kullanici olarak yapilir (root
# olarak `cargo build` calistirmak ~/.cargo ve target/ dizinlerini root'a
# devredip sonraki derlemeleri bozar); yalnizca sistem dizinlerine kopyalama
# adimlari gerektiginde `sudo` ile yukseltilir.
#
# Kullanim:
#   ./build.sh                  # derle + sisteme kur (gerekirse sudo ister)
#   ./build.sh --build-only     # yalnizca derle, kurma
#   ./build.sh --install-only   # derleme yapma, onceden derlenmis binary'leri kur
#   ./build.sh --no-desktop     # .desktop dosyasini kurma (yalnizca binary'ler)
#   ./build.sh --no-config      # ~/.config/qwm/qwm.toml'u kopyalama
#   ./build.sh --prefix DIR     # binary kurulum dizini (varsayilan /usr/local/bin)
#   ./build.sh --uninstall      # kurulan dosyalari kaldir (config KORUNUR)
#   ./build.sh --help
#
set -euo pipefail

# --- Varsayilanlar ---
PREFIX="/usr/local/bin"
XSESSIONS_DIR="/usr/share/xsessions"
DO_BUILD=1
DO_INSTALL=1
DO_DESKTOP=1
DO_CONFIG=1
DO_UNINSTALL=0

# --- Yardimci ciktilar ---
c_green() { printf '\033[32m%s\033[0m\n' "$1"; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$1"; }
c_red() { printf '\033[31m%s\033[0m\n' "$1" >&2; }
info() { c_green "==> $1"; }
warn() { c_yellow "!!  $1"; }
err() { c_red "xx  $1"; }

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

# --- Argument parsing ---
while [ $# -gt 0 ]; do
    case "$1" in
        --build-only)
            DO_INSTALL=0
            ;;
        --install-only)
            DO_BUILD=0
            ;;
        --no-desktop)
            DO_DESKTOP=0
            ;;
        --no-config)
            DO_CONFIG=0
            ;;
        --prefix)
            shift
            PREFIX="${1:?--prefix icin bir dizin verilmeli}"
            ;;
        --prefix=*)
            PREFIX="${1#*=}"
            ;;
        --uninstall)
            DO_UNINSTALL=1
            DO_BUILD=0
            DO_INSTALL=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            err "bilinmeyen secenek: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

# --- Proje kokune gec (bu script'in bulundugu dizin) ---
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "Cargo.toml" ] || ! grep -q '^\[workspace\]' Cargo.toml; then
    err "bu script'in yani sira bir Cargo workspace (qwm/Cargo.toml) bulunamadi: $SCRIPT_DIR"
    exit 1
fi

# --- Gercek kullaniciyi/HOME'u tespit et (sudo altinda bile dogru) ---
REAL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
if [ -n "${SUDO_USER:-}" ]; then
    REAL_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
else
    REAL_HOME="${HOME:-$(eval echo "~$REAL_USER")}"
fi
REAL_HOME="${REAL_HOME:-$HOME}"

need_root_copy() {
    # Hedef dizine yazma izni var mi kontrol eder; yoksa sudo kullanilacak.
    [ -w "$(dirname "$1")" ] 2>/dev/null
}

sudo_if_needed() {
    # $1: hedef dosyanin bulunacagi dizin. O dizine yazamiyorsak sudo ile
    # calistir, yazabiliyorsak (ornegin zaten root'sak ya da PREFIX
    # kullanicinin kendi dizinindeyse) dogrudan calistir.
    local target_dir="$1"
    shift
    if [ "$(id -u)" -eq 0 ] || [ -w "$target_dir" ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        err "root yetkisi gerekiyor ama 'sudo' bulunamadi: $target_dir icin $*"
        err "lutfen bu adimi root olarak elle calistirin."
        return 1
    fi
}

# --- Uninstall ---
if [ "$DO_UNINSTALL" -eq 1 ]; then
    info "qwm kaldiriliyor (config DOKUNULMADAN birakilacak: ~/.config/qwm/)"
    for bin in qwm qwmctl; do
        target="$PREFIX/$bin"
        if [ -e "$target" ]; then
            sudo_if_needed "$PREFIX" rm -f "$target"
            info "silindi: $target"
        fi
    done
    desktop_file="$XSESSIONS_DIR/qwm.desktop"
    if [ -e "$desktop_file" ]; then
        sudo_if_needed "$XSESSIONS_DIR" rm -f "$desktop_file"
        info "silindi: $desktop_file"
    fi
    info "kaldirma tamamlandi."
    exit 0
fi

# --- Derleme ---
if [ "$DO_BUILD" -eq 1 ]; then
    if ! command -v cargo >/dev/null 2>&1; then
        err "cargo bulunamadi. Once Rust toolchain'i kurun: https://rustup.rs"
        exit 1
    fi

    # Root olarak build CALISTIRILMAZ: cargo cache'inin sahipligini bozar.
    if [ "$(id -u)" -eq 0 ] && [ -z "${SUDO_USER:-}" ]; then
        warn "root olarak dogrudan calistiriliyorsunuz; 'cargo build' yine de"
        warn "mevcut kullanici (root) olarak yapilacak. Normal kullanicinizla"
        warn "('./build.sh' veya gerekirse 'sudo ./build.sh') calistirmaniz onerilir."
    fi

    info "cargo build --release --workspace calistiriliyor..."
    cargo build --release --workspace

    info "derleme tamamlandi: target/release/{qwm,qwmctl}"
fi

[ "$DO_INSTALL" -eq 0 ] && exit 0

# --- Binary kurulumu ---
for bin in qwm qwmctl; do
    src="target/release/$bin"
    if [ ! -x "$src" ]; then
        err "'$src' bulunamadi. Once derleyin: ./build.sh --build-only"
        exit 1
    fi
done

info "binary'ler kuruluyor: $PREFIX"
mkdir -p "$PREFIX" 2>/dev/null || sudo_if_needed "$PREFIX" mkdir -p "$PREFIX"
for bin in qwm qwmctl; do
    sudo_if_needed "$PREFIX" install -Dm755 "target/release/$bin" "$PREFIX/$bin"
    info "kuruldu: $PREFIX/$bin"
done

# --- .desktop (display manager) kurulumu ---
if [ "$DO_DESKTOP" -eq 1 ]; then
    if [ ! -f "docs/qwm.desktop" ]; then
        warn "docs/qwm.desktop bulunamadi, oturum dosyasi atlaniyor"
    else
        info ".desktop dosyasi kuruluyor: $XSESSIONS_DIR/qwm.desktop"
        # Exec satirinin PREFIX ile tutarli olmasini garanti et (ornegin
        # qwm /usr/local/bin'e kuruldu ama o yol $PATH'te degilse mutlak
        # yol yazmak gerekir).
        tmp_desktop="$(mktemp)"
        sed "s#^Exec=.*#Exec=$PREFIX/qwm#" docs/qwm.desktop > "$tmp_desktop"
        sudo_if_needed "$XSESSIONS_DIR" mkdir -p "$XSESSIONS_DIR"
        sudo_if_needed "$XSESSIONS_DIR" install -Dm644 "$tmp_desktop" "$XSESSIONS_DIR/qwm.desktop"
        rm -f "$tmp_desktop"
        info "kuruldu: $XSESSIONS_DIR/qwm.desktop (SDDM/LightDM/GDM oturum listesinde gorunmeli)"
    fi
fi

# --- Varsayilan config ---
if [ "$DO_CONFIG" -eq 1 ]; then
    config_dir="$REAL_HOME/.config/qwm"
    config_file="$config_dir/qwm.toml"
    if [ -f "$config_file" ]; then
        info "config zaten var, dokunulmadi: $config_file"
    elif [ -f "docs/default-config.toml" ]; then
        mkdir -p "$config_dir"
        cp docs/default-config.toml "$config_file"
        if [ -n "${SUDO_USER:-}" ]; then
            chown -R "$REAL_USER:$REAL_USER" "$config_dir" 2>/dev/null || true
        fi
        info "varsayilan config kopyalandi: $config_file"
    else
        warn "docs/default-config.toml bulunamadi, config kopyalanmadi"
    fi
fi

echo
info "kurulum tamamlandi."
echo "  - $PREFIX/qwm bir onceki X oturum yoneticisinin listesinde 'qwm' olarak gorunmeli."
echo "  - Elle denemek icin: exec qwm (ornegin ~/.xinitrc icinden)."
echo "  - Kaldirmak icin: ./build.sh --uninstall"
