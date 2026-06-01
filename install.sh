#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    QWM UNIVERSAL INSTALLER                               ║
# ║              Q Window Manager — NVIDIA Optimized X11 WM                 ║
# ║                                                                          ║
# ║  Desteklenen Sistemler:                                                  ║
# ║    • Arch Linux (vanilla)                                                ║
# ║    • Manjaro Linux                                                       ║
# ║    • EndeavourOS                                                         ║
# ║    • Garuda Linux                                                        ║
# ║    • ArcoLinux                                                           ║
# ║    • BlackArch                                                           ║
# ║    • Artix Linux (OpenRC / runit / s6)                                  ║
# ║    • Parabola GNU/Linux                                                  ║
# ║    • Diğer tüm Arch tabanlı dağıtımlar                                  ║
# ║                                                                          ║
# ║  Kullanım:                                                               ║
# ║    chmod +x install.sh                                                   ║
# ║    ./install.sh                                                          ║
# ║    ./install.sh --help                                                   ║
# ║    ./install.sh --no-nvidia    (NVIDIA olmayan sistemler)                ║
# ║    ./install.sh --no-dm        (Display manager kurma)                   ║
# ║    ./install.sh --dm lightdm   (Farklı DM seç)                          ║
# ║    ./install.sh --aur paru     (AUR helper seç)                         ║
# ║    ./install.sh --uninstall    (QWM kaldır)                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SABITLER VE RENKLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

readonly QWM_VERSION="0.1.0"
readonly QWM_DIR="$HOME/qwm"
readonly QWM_CONFIG_DIR="$HOME/.config/qwm"
readonly QWM_LOG_DIR="$HOME/.local/share/qwm"
readonly QWM_VENV="$QWM_DIR/venv"
readonly QWM_BIN="/usr/local/bin/qwm"
readonly QWM_MSG_BIN="/usr/local/bin/qwm-msg"
readonly XSESSIONS_DIR="/usr/share/xsessions"
readonly LOG_FILE="/tmp/qwm_install_$(date +%Y%m%d_%H%M%S).log"

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLAG DEFAULTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FLAG_NVIDIA=true
FLAG_DM=true
FLAG_DM_CHOICE="auto"
FLAG_AUR_HELPER="auto"
FLAG_UNINSTALL=false
FLAG_YES=false
FLAG_DEBUG=false
FLAG_NO_REBOOT=false
FLAG_SKIP_UPDATE=false

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOG FONKSİYONLARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_raw()     { echo -e "$*" | tee -a "$LOG_FILE"; }
log_info()    { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
log_warn()    { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
log_error()   { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; }
log_step()    { echo -e "\n${CYAN}${BOLD}[►]${NC}${BOLD} $*${NC}" | tee -a "$LOG_FILE"; }
log_sub()     { echo -e "    ${DIM}↳${NC} $*" | tee -a "$LOG_FILE"; }
log_debug()   { [[ "$FLAG_DEBUG" == true ]] && echo -e "${DIM}[D] $*${NC}" | tee -a "$LOG_FILE" || true; }
log_success() { echo -e "${GREEN}${BOLD}[✓] $*${NC}" | tee -a "$LOG_FILE"; }
log_fatal()   {
    echo -e "\n${RED}${BOLD}╔══════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║  FATAL HATA: $*${NC}"
    echo -e "${RED}${BOLD}╚══════════════════════════════════════════╝${NC}"
    echo -e "${DIM}Log dosyası: $LOG_FILE${NC}"
    exit 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YARDIM MENÜSÜ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat << EOF

${CYAN}${BOLD}QWM Universal Installer v${QWM_VERSION}${NC}

${BOLD}KULLANIM:${NC}
  ./install.sh [SEÇENEKLER]

${BOLD}SEÇENEKLER:${NC}
  ${GREEN}--help${NC}              Bu yardım mesajını göster
  ${GREEN}--no-nvidia${NC}         NVIDIA sürücü kurulumunu atla
  ${GREEN}--no-dm${NC}             Display manager kurulumunu atla
  ${GREEN}--dm <isim>${NC}         Display manager seç: sddm, lightdm, gdm, ly
  ${GREEN}--aur <isim>${NC}        AUR helper seç: paru, yay, trizen
  ${GREEN}--yes${NC}               Tüm onaylara otomatik evet de
  ${GREEN}--skip-update${NC}       Sistem güncellemesini atla
  ${GREEN}--no-reboot${NC}         Kurulum sonrası yeniden başlatma sorma
  ${GREEN}--debug${NC}             Ayrıntılı debug çıktısı
  ${GREEN}--uninstall${NC}         QWM'i sistemden kaldır

${BOLD}ÖRNEKLER:${NC}
  ./install.sh                          # Tam kurulum (önerilen)
  ./install.sh --no-nvidia              # NVIDIA'sız kurulum
  ./install.sh --dm lightdm             # LightDM ile kurulum
  ./install.sh --yes --no-reboot        # Otomatik kurulum
  ./install.sh --aur paru               # paru AUR helper ile
  ./install.sh --uninstall              # Kaldır

${BOLD}LOG:${NC}
  Kurulum logu: $LOG_FILE

EOF
    exit 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ARGÜMAN PARSER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)        show_help ;;
            --no-nvidia)      FLAG_NVIDIA=false; shift ;;
            --no-dm)          FLAG_DM=false; shift ;;
            --dm)             FLAG_DM_CHOICE="$2"; shift 2 ;;
            --aur)            FLAG_AUR_HELPER="$2"; shift 2 ;;
            --yes|-y)         FLAG_YES=true; shift ;;
            --debug)          FLAG_DEBUG=true; shift ;;
            --no-reboot)      FLAG_NO_REBOOT=true; shift ;;
            --skip-update)    FLAG_SKIP_UPDATE=true; shift ;;
            --uninstall)      FLAG_UNINSTALL=true; shift ;;
            *)
                log_error "Bilinmeyen argüman: $1"
                show_help
                ;;
        esac
    done
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BANNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << 'BANNER'
  ██████╗ ██╗    ██╗███╗   ███╗
 ██╔═══██╗██║    ██║████╗ ████║
 ██║   ██║██║ █╗ ██║██╔████╔██║
 ██║▄▄ ██║██║███╗██║██║╚██╔╝██║
 ╚██████╔╝╚███╔███╔╝██║ ╚═╝ ██║
  ╚══▀▀═╝  ╚══╝╚══╝ ╚═╝     ╚═╝
BANNER
    echo -e "${NC}"
    echo -e "${WHITE}${BOLD}  Q Window Manager — NVIDIA Optimized X11 Tiling WM${NC}"
    echo -e "${DIM}  Universal Arch Linux Installer v${QWM_VERSION}${NC}"
    echo -e "${DIM}  Log: $LOG_FILE${NC}"
    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SİSTEM ALGILAMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

detect_system() {
    log_step "Sistem Algılanıyor..."

    # ── Root kontrolü ──────────────────────────────────────────────────────
    if [[ $EUID -eq 0 ]]; then
        log_fatal "Root olarak çalıştırmayın! Normal kullanıcı ile çalıştırın."
    fi
    log_info "Kullanıcı: $USER (root değil ✓)"

    # ── Arch tabanlı mı? ───────────────────────────────────────────────────
    if ! command -v pacman &>/dev/null; then
        log_fatal "pacman bulunamadı! Bu script sadece Arch tabanlı sistemler içindir."
    fi
    log_info "pacman bulundu ✓"

    # ── Dağıtım tespiti ────────────────────────────────────────────────────
    DISTRO="unknown"
    DISTRO_NAME="Unknown"

    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        DISTRO_NAME="${PRETTY_NAME:-$NAME}"

        case "${ID:-}" in
            arch)        DISTRO="arch" ;;
            manjaro)     DISTRO="manjaro" ;;
            endeavouros) DISTRO="endeavouros" ;;
            garuda)      DISTRO="garuda" ;;
            arcolinux)   DISTRO="arcolinux" ;;
            blackarch)   DISTRO="blackarch" ;;
            artix)       DISTRO="artix" ;;
            parabola)    DISTRO="parabola" ;;
            *)
                # ID_LIKE kontrolü
                case "${ID_LIKE:-}" in
                    *arch*) DISTRO="arch-like" ;;
                    *)      DISTRO="arch-unknown" ;;
                esac
                ;;
        esac
    fi
    log_info "Dağıtım: ${DISTRO_NAME}"

    # ── Init sistemi tespiti ───────────────────────────────────────────────
    INIT_SYSTEM="unknown"
    if command -v systemctl &>/dev/null && systemctl --version &>/dev/null; then
        INIT_SYSTEM="systemd"
    elif command -v rc-service &>/dev/null; then
        INIT_SYSTEM="openrc"
    elif command -v sv &>/dev/null; then
        INIT_SYSTEM="runit"
    elif command -v s6-rc &>/dev/null; then
        INIT_SYSTEM="s6"
    fi
    log_info "Init sistemi: ${INIT_SYSTEM}"

    # ── Kernel tespiti ─────────────────────────────────────────────────────
    KERNEL_VERSION=$(uname -r)
    KERNEL_TYPE="standard"
    if echo "$KERNEL_VERSION" | grep -q "lts"; then
        KERNEL_TYPE="lts"
    elif echo "$KERNEL_VERSION" | grep -q "zen"; then
        KERNEL_TYPE="zen"
    elif echo "$KERNEL_VERSION" | grep -q "hardened"; then
        KERNEL_TYPE="hardened"
    elif echo "$KERNEL_VERSION" | grep -q "cachyos"; then
        KERNEL_TYPE="cachyos"
    fi
    log_info "Kernel: ${KERNEL_VERSION} (${KERNEL_TYPE})"

    # ── NVIDIA tespiti ─────────────────────────────────────────────────────
    NVIDIA_DETECTED=false
    NVIDIA_GPU=""
    NVIDIA_DRIVER_INSTALLED=false

    if lspci 2>/dev/null | grep -qi "nvidia"; then
        NVIDIA_DETECTED=true
        NVIDIA_GPU=$(lspci 2>/dev/null | grep -i "nvidia" | \
                     grep -i "vga\|3d\|display" | \
                     sed 's/.*: //' | head -1)
        log_info "NVIDIA GPU: ${NVIDIA_GPU}"

        if lsmod 2>/dev/null | grep -q "^nvidia"; then
            NVIDIA_DRIVER_INSTALLED=true
            log_info "NVIDIA sürücü: Zaten yüklü"
        else
            log_warn "NVIDIA sürücü: Henüz yüklü değil"
        fi
    else
        log_warn "NVIDIA GPU tespit edilemedi — NVIDIA kurulumu atlanacak"
        FLAG_NVIDIA=false
    fi

    # ── Mevcut Display Manager ─────────────────────────────────────────────
    EXISTING_DM="none"
    for dm in sddm lightdm gdm lxdm slim ly xdm; do
        if command -v "$dm" &>/dev/null; then
            EXISTING_DM="$dm"
            break
        fi
    done

    if [[ "$EXISTING_DM" != "none" ]]; then
        log_warn "Mevcut DM bulundu: ${EXISTING_DM}"
    else
        log_info "Mevcut DM: Yok"
    fi

    # ── Python tespiti ─────────────────────────────────────────────────────
    PYTHON_CMD=""
    PYTHON_VERSION=""
    for py in python3.12 python3.11 python3 python; do
        if command -v "$py" &>/dev/null; then
            PY_VER=$($py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
            MAJOR=$(echo "$PY_VER" | cut -d. -f1)
            MINOR=$(echo "$PY_VER" | cut -d. -f2)
            if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 11 ]]; then
                PYTHON_CMD="$py"
                PYTHON_VERSION="$PY_VER"
                break
            fi
        fi
    done

    if [[ -z "$PYTHON_CMD" ]]; then
        log_warn "Python 3.11+ bulunamadı — kurulacak"
        PYTHON_CMD="python"
        PYTHON_VERSION="kurulacak"
    else
        log_info "Python: ${PYTHON_VERSION} (${PYTHON_CMD})"
    fi

    # ── AUR Helper tespiti ─────────────────────────────────────────────────
    AUR_CMD=""
    if [[ "$FLAG_AUR_HELPER" == "auto" ]]; then
        for helper in paru yay trizen pikaur aurman; do
            if command -v "$helper" &>/dev/null; then
                AUR_CMD="$helper"
                break
            fi
        done
    else
        AUR_CMD="$FLAG_AUR_HELPER"
    fi

    if [[ -n "$AUR_CMD" ]]; then
        log_info "AUR helper: ${AUR_CMD}"
    else
        log_warn "AUR helper bulunamadı — paru kurulacak"
    fi

    # ── Mevcut X11 kontrolü ────────────────────────────────────────────────
    X11_INSTALLED=false
    if command -v Xorg &>/dev/null || command -v X &>/dev/null; then
        X11_INSTALLED=true
        log_info "X11: Zaten kurulu"
    fi

    # ── Özet ──────────────────────────────────────────────────────────────
    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Sistem Özeti:${NC}"
    echo -e "  Dağıtım    : ${CYAN}${DISTRO_NAME}${NC}"
    echo -e "  Init       : ${CYAN}${INIT_SYSTEM}${NC}"
    echo -e "  Kernel     : ${CYAN}${KERNEL_VERSION}${NC}"
    echo -e "  GPU        : ${CYAN}${NVIDIA_GPU:-"NVIDIA Yok"}${NC}"
    echo -e "  Python     : ${CYAN}${PYTHON_VERSION}${NC}"
    echo -e "  AUR Helper : ${CYAN}${AUR_CMD:-"kurulacak (paru)"}${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ONAY FONKSİYONU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

confirm() {
    local msg="$1"
    local default="${2:-y}"

    if [[ "$FLAG_YES" == true ]]; then
        log_sub "Otomatik onay: $msg"
        return 0
    fi

    local prompt
    if [[ "$default" == "y" ]]; then
        prompt="[E/h]"
    else
        prompt="[e/H]"
    fi

    echo -ne "${YELLOW}${BOLD}  ? ${NC}${msg} ${DIM}${prompt}${NC} "
    read -r answer

    case "${answer,,}" in
        y|e|yes|evet|"")
            [[ "$default" == "y" ]] && return 0 || return 1
            ;;
        n|h|no|hayir|hayır)
            [[ "$default" == "n" ]] && return 0 || return 1
            ;;
        *)
            [[ "$default" == "y" ]] && return 0 || return 1
            ;;
    esac
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAKET KURULUM FONKSİYONLARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pacman_install() {
    local packages=("$@")
    local to_install=()

    # Yüklü olmayanları filtrele
    for pkg in "${packages[@]}"; do
        if ! pacman -Qi "$pkg" &>/dev/null; then
            to_install+=("$pkg")
        else
            log_sub "${pkg}: zaten kurulu"
        fi
    done

    if [[ ${#to_install[@]} -gt 0 ]]; then
        log_sub "Kuruluyor: ${to_install[*]}"
        sudo pacman -S --needed --noconfirm "${to_install[@]}" >> "$LOG_FILE" 2>&1 || {
            log_error "Paket kurulum hatası: ${to_install[*]}"
            log_sub "Log için bak: $LOG_FILE"
            return 1
        }
        log_info "Kuruldu: ${to_install[*]}"
    fi
}

aur_install() {
    local packages=("$@")
    local to_install=()

    if [[ -z "$AUR_CMD" ]]; then
        log_warn "AUR helper yok — atlanıyor: ${packages[*]}"
        return 0
    fi

    for pkg in "${packages[@]}"; do
        if ! pacman -Qi "$pkg" &>/dev/null; then
            to_install+=("$pkg")
        else
            log_sub "${pkg}: zaten kurulu"
        fi
    done

    if [[ ${#to_install[@]} -gt 0 ]]; then
        log_sub "AUR'dan kuruluyor: ${to_install[*]}"
        "$AUR_CMD" -S --needed --noconfirm "${to_install[@]}" >> "$LOG_FILE" 2>&1 || {
            log_warn "AUR kurulum uyarısı: ${to_install[*]} — devam ediliyor"
            return 0
        }
        log_info "AUR'dan kuruldu: ${to_install[*]}"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUR HELPER KURULUMU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_aur_helper() {
    if [[ -n "$AUR_CMD" ]] && command -v "$AUR_CMD" &>/dev/null; then
        log_info "AUR helper mevcut: ${AUR_CMD}"
        return 0
    fi

    log_step "AUR Helper Kuruluyor (paru)..."

    # git ve base-devel gerekli
    pacman_install git base-devel

    local tmp_dir
    tmp_dir=$(mktemp -d)
    cd "$tmp_dir"

    git clone https://aur.archlinux.org/paru-bin.git >> "$LOG_FILE" 2>&1 || {
        # paru-bin başarısız olursa paru dene
        git clone https://aur.archlinux.org/paru.git >> "$LOG_FILE" 2>&1 || {
            log_warn "paru kurulamadı — yay deneniyor"
            git clone https://aur.archlinux.org/yay-bin.git >> "$LOG_FILE" 2>&1 || {
                log_warn "AUR helper kurulamadı — AUR paketleri atlanacak"
                cd "$HOME"
                rm -rf "$tmp_dir"
                return 0
            }
            cd yay-bin
            makepkg -si --noconfirm >> "$LOG_FILE" 2>&1
            AUR_CMD="yay"
            cd "$HOME"
            rm -rf "$tmp_dir"
            log_info "yay kuruldu"
            return 0
        }
        cd paru
    }

    local dir_name
    dir_name=$(ls -d */ 2>/dev/null | head -1 | tr -d '/')
    if [[ -z "$dir_name" ]]; then
        cd paru-bin 2>/dev/null || cd paru 2>/dev/null || {
            log_warn "AUR helper kurulamadı"
            cd "$HOME"
            rm -rf "$tmp_dir"
            return 0
        }
    else
        cd "$dir_name"
    fi

    makepkg -si --noconfirm >> "$LOG_FILE" 2>&1 || {
        log_warn "AUR helper build başarısız"
        cd "$HOME"
        rm -rf "$tmp_dir"
        return 0
    }

    AUR_CMD="paru"
    cd "$HOME"
    rm -rf "$tmp_dir"
    log_info "paru başarıyla kuruldu"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SİSTEM GÜNCELLEMESİ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

update_system() {
    if [[ "$FLAG_SKIP_UPDATE" == true ]]; then
        log_warn "Sistem güncellemesi atlandı (--skip-update)"
        return 0
    fi

    log_step "Sistem Güncelleniyor..."
    log_warn "Bu işlem birkaç dakika sürebilir..."

    sudo pacman -Syu --noconfirm >> "$LOG_FILE" 2>&1 || {
        log_warn "Tam güncelleme başarısız — devam ediliyor"
    }

    log_info "Sistem güncellendi"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEMEL BAĞIMLILIKLAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_base_deps() {
    log_step "Temel Bağımlılıklar Kuruluyor..."

    # ── Build araçları ─────────────────────────────────────────────────────
    log_sub "Build araçları..."
    pacman_install \
        base-devel \
        git \
        wget \
        curl \
        unzip \
        tar

    # ── Python ────────────────────────────────────────────────────────────
    log_sub "Python 3.11+..."
    pacman_install \
        python \
        python-pip \
        python-setuptools \
        python-wheel \
        python-virtualenv

    # Python versiyonunu güncelle
    PYTHON_CMD=$(command -v python3 || command -v python)
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python: $PYTHON_VERSION"

    # ── X11 core ──────────────────────────────────────────────────────────
    log_sub "X11 sunucu ve araçları..."
    pacman_install \
        xorg-server \
        xorg-xinit \
        xorg-xrandr \
        xorg-xsetroot \
        xorg-xev \
        xorg-xprop \
        xorg-xwininfo \
        xorg-xlsclients \
        xorg-xdpyinfo \
        xorg-xmodmap \
        xorg-xrdb \
        xorg-setxkbmap \
        xorg-xset

    # ── X11 geliştirme kütüphaneleri ──────────────────────────────────────
    log_sub "X11 kütüphaneleri..."
    pacman_install \
        libx11 \
        libxinerama \
        libxft \
        libxrandr \
        libxcomposite \
        libxdamage \
        libxfixes \
        libxrender \
        libxtst \
        libxi

    # ── Temel araçlar ─────────────────────────────────────────────────────
    log_sub "Sistem araçları..."
    pacman_install \
        procps-ng \
        psmisc \
        inotify-tools \
        util-linux \
        lsof \
        pciutils \
        usbutils
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NVIDIA KURULUMU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_nvidia() {
    if [[ "$FLAG_NVIDIA" == false ]]; then
        log_warn "NVIDIA kurulumu atlandı"
        return 0
    fi

    log_step "NVIDIA Sürücüleri Kuruluyor..."
    log_sub "GPU: ${NVIDIA_GPU}"
    log_sub "Kernel tipi: ${KERNEL_TYPE}"

    # ── Kernel tipine göre sürücü seç ─────────────────────────────────────
    case "$KERNEL_TYPE" in
        lts)
            log_sub "LTS kernel için nvidia-lts seçildi"
            NVIDIA_PKG="nvidia-lts"
            ;;
        zen|cachyos)
            log_sub "Zen/CachyOS kernel — DKMS kullanılıyor"
            NVIDIA_PKG="nvidia-dkms"
            ;;
        hardened)
            log_sub "Hardened kernel — DKMS kullanılıyor"
            NVIDIA_PKG="nvidia-dkms"
            ;;
        *)
            # Standart kernel
            NVIDIA_PKG="nvidia"

            # Vanilla Arch'ta nvidia paketi standart kerneli gerektirir
            # Eğer linux-headers kurulu değilse dkms kullan
            if ! pacman -Qi linux-headers &>/dev/null; then
                log_sub "linux-headers bulunamadı — nvidia-dkms kullanılıyor"
                NVIDIA_PKG="nvidia-dkms"
            fi
            ;;
    esac

    # ── NVIDIA ana sürücü ─────────────────────────────────────────────────
    log_sub "Ana NVIDIA sürücü: ${NVIDIA_PKG}"
    pacman_install \
        "${NVIDIA_PKG}" \
        nvidia-utils \
        nvidia-settings

    # ── DKMS için kernel headers ───────────────────────────────────────────
    if [[ "$NVIDIA_PKG" == "nvidia-dkms" ]]; then
        log_sub "Kernel headers kuruluyor..."
        local headers_pkg="linux-headers"
        case "$KERNEL_TYPE" in
            zen)      headers_pkg="linux-zen-headers" ;;
            hardened) headers_pkg="linux-hardened-headers" ;;
            lts)      headers_pkg="linux-lts-headers" ;;
            cachyos)  headers_pkg="linux-cachyos-headers" ;;
        esac
        pacman_install "$headers_pkg" || log_warn "Headers kurulamadı — devam"
    fi

    # ── 32-bit destek (Steam için) ─────────────────────────────────────────
    log_sub "32-bit kütüphaneler (Steam/Wine için)..."

    # multilib repo aktif mi kontrol et
    if grep -q "^\[multilib\]" /etc/pacman.conf; then
        pacman_install \
            lib32-nvidia-utils \
            lib32-opencl-nvidia || log_warn "32-bit NVIDIA atlandı"
    else
        log_warn "multilib repo aktif değil — 32-bit paketler atlanıyor"
        log_sub "Etkinleştirmek için /etc/pacman.conf'ta [multilib] yorum satırını kaldırın"
    fi

    # ── Ek NVIDIA paketleri ────────────────────────────────────────────────
    log_sub "Ek NVIDIA paketleri..."
    pacman_install \
        opencl-nvidia \
        libvdpau \
        libxnvctrl \
        egl-wayland || true     # Hata olursa devam et

    # ── NVML Python kütüphanesi ────────────────────────────────────────────
    log_sub "nvidia-ml-py (pynvml) kuruluyor..."
    pacman_install python-pip
    # pip ile kurulacak (venv içinde)

    # ── NVIDIA kernel modülü yapılandırması ───────────────────────────────
    log_sub "NVIDIA kernel modülleri yapılandırılıyor..."
    sudo tee /etc/modules-load.d/nvidia.conf > /dev/null << 'EOF'
# QWM tarafından oluşturuldu — NVIDIA kernel modülleri
nvidia
nvidia_modeset
nvidia_uvm
nvidia_drm
EOF

    # ── NVIDIA DRM modesetting (GRUB) ─────────────────────────────────────
    configure_nvidia_grub

    # ── nvidia-xconfig ─────────────────────────────────────────────────────
    log_sub "X11 NVIDIA config oluşturuluyor..."
    sudo nvidia-xconfig --no-logo \
        --allow-glx-with-composite \
        >> "$LOG_FILE" 2>&1 || log_warn "nvidia-xconfig başarısız — manuel yapılandırma gerekebilir"

    # ── Özel xorg.conf ────────────────────────────────────────────────────
    write_nvidia_xorg_conf

    log_info "NVIDIA kurulumu tamamlandı"
}

configure_nvidia_grub() {
    log_sub "GRUB yapılandırılıyor (nvidia_drm.modeset=1)..."

    local grub_conf="/etc/default/grub"

    if [[ ! -f "$grub_conf" ]]; then
        log_warn "GRUB config bulunamadı: $grub_conf"
        # systemd-boot kontrolü
        if [[ -d /boot/loader ]]; then
            configure_nvidia_systemd_boot
        fi
        return 0
    fi

    # Mevcut satırı oku
    local current_cmdline
    current_cmdline=$(grep "^GRUB_CMDLINE_LINUX_DEFAULT" "$grub_conf" | \
                      sed 's/GRUB_CMDLINE_LINUX_DEFAULT=//;s/"//g')

    # nvidia_drm.modeset=1 zaten var mı?
    if echo "$current_cmdline" | grep -q "nvidia_drm.modeset=1"; then
        log_sub "nvidia_drm.modeset=1 zaten mevcut"
        return 0
    fi

    # Yeni satır oluştur
    local new_cmdline="\"${current_cmdline} nvidia_drm.modeset=1\""

    # Değiştir
    sudo sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT=${new_cmdline}|" \
        "$grub_conf"

    # GRUB güncelle
    if command -v grub-mkconfig &>/dev/null; then
        log_sub "GRUB güncelleniyor..."
        sudo grub-mkconfig -o /boot/grub/grub.cfg >> "$LOG_FILE" 2>&1 || \
            log_warn "GRUB güncellenemedi — manuel güncelleme gerekebilir"
    elif command -v update-grub &>/dev/null; then
        sudo update-grub >> "$LOG_FILE" 2>&1 || true
    fi

    log_info "GRUB yapılandırıldı"
}

configure_nvidia_systemd_boot() {
    log_sub "systemd-boot yapılandırılıyor..."

    local loader_dir="/boot/loader/entries"
    if [[ ! -d "$loader_dir" ]]; then
        log_warn "systemd-boot entries dizini bulunamadı"
        return 0
    fi

    for entry in "$loader_dir"/*.conf; do
        if grep -q "options" "$entry" && ! grep -q "nvidia_drm.modeset=1" "$entry"; then
            sudo sed -i '/^options/ s/$/ nvidia_drm.modeset=1/' "$entry"
            log_sub "Güncellendi: $entry"
        fi
    done
}

write_nvidia_xorg_conf() {
    log_sub "Optimize edilmiş xorg.conf yazılıyor..."

    sudo tee /etc/X11/xorg.conf.d/20-nvidia-qwm.conf > /dev/null << 'EOF'
# /etc/X11/xorg.conf.d/20-nvidia-qwm.conf
# QWM için NVIDIA X11 optimizasyonları

Section "Device"
    Identifier     "NVIDIA GPU"
    Driver         "nvidia"

    # NVIDIA logoyu kapat
    Option         "NoLogo" "1"

    # Composition pipeline — başlangıçta kapalı (QWM game mode yönetir)
    # G-Sync için KAPALI olması gerekir
    Option         "ForceCompositionPipeline"     "Off"
    Option         "ForceFullCompositionPipeline" "Off"

    # G-Sync Compatible (Freesync monitörler için)
    Option         "AllowGSYNCCompatible" "1"

    # NV-CONTROL protokolü (nvidia-settings için gerekli)
    Option         "UseNVControlProtocol" "1"

    # Ekran boyutu raporlama
    Option         "UseEdidDpi" "1"
EndSection

Section "Screen"
    Identifier     "Default Screen"
    DefaultDepth   24

    SubSection "Display"
        Depth       24
    EndSubSection
EndSection
EOF
    log_info "xorg.conf.d/20-nvidia-qwm.conf oluşturuldu"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UYGULAMA BAĞIMLILIKLARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_app_deps() {
    log_step "Uygulama Bağımlılıkları Kuruluyor..."

    # ── Terminal emülatörler ───────────────────────────────────────────────
    log_sub "Terminal emülatörler..."
    pacman_install xterm    # Fallback — her zaman kur

    # Alacritty veya Kitty — birini kur
    if ! command -v alacritty &>/dev/null && \
       ! command -v kitty &>/dev/null; then
        pacman_install alacritty || \
        pacman_install kitty || \
        log_warn "GPU hızlandırmalı terminal kurulamadı — xterm kullanılacak"
    fi

    # ── Uygulama başlatıcı ─────────────────────────────────────────────────
    log_sub "Uygulama başlatıcı (rofi/dmenu)..."
    pacman_install rofi || pacman_install dmenu || true

    # ── Compositor ────────────────────────────────────────────────────────
    log_sub "Compositor (picom)..."
    pacman_install picom || log_warn "picom kurulamadı — opsiyonel"

    # ── Ses ───────────────────────────────────────────────────────────────
    log_sub "Ses araçları..."
    pacman_install \
        pipewire \
        pipewire-pulse \
        wireplumber \
        pavucontrol || true

    # ── Ağ ────────────────────────────────────────────────────────────────
    log_sub "Ağ yöneticisi..."
    pacman_install networkmanager nm-connection-editor || true

    # ── Feral GameMode ────────────────────────────────────────────────────
    log_sub "Feral GameMode (oyun optimizasyonu)..."
    pacman_install gamemode || log_warn "gamemode kurulamadı — opsiyonel"

    # lib32-gamemode multilib ile
    if grep -q "^\[multilib\]" /etc/pacman.conf; then
        pacman_install lib32-gamemode || true
    fi

    # ── Steam (opsiyonel) ──────────────────────────────────────────────────
    if confirm "Steam kurulsun mu? (oyun platformu)"; then
        if grep -q "^\[multilib\]" /etc/pacman.conf; then
            pacman_install steam || log_warn "Steam kurulamadı"
        else
            log_warn "Steam için multilib gerekli — atlanıyor"
        fi
    fi

    # ── Yazı tipleri ──────────────────────────────────────────────────────
    log_sub "Yazı tipleri..."
    pacman_install \
        ttf-jetbrains-mono \
        ttf-font-awesome \
        noto-fonts \
        noto-fonts-emoji || true

    # ── Monitör araçları ──────────────────────────────────────────────────
    log_sub "Sistem monitör araçları..."
    pacman_install \
        htop \
        btop || true

    # nvtop — GPU monitör
    pacman_install nvtop || \
        aur_install nvtop || \
        log_warn "nvtop kurulamadı — opsiyonel"

    # ── Xephyr (test için) ─────────────────────────────────────────────────
    log_sub "Xephyr (test ortamı)..."
    pacman_install xorg-server-xephyr || true

    # ── Diğer araçlar ─────────────────────────────────────────────────────
    log_sub "Ek araçlar..."
    pacman_install \
        feh \
        dunst \
        xclip \
        xdotool \
        wmctrl \
        xdo || true
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYTHON ORTAMI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

setup_python_env() {
    log_step "Python Sanal Ortamı Kuruluyor..."

    # ── Venv oluştur ───────────────────────────────────────────────────────
    if [[ -d "$QWM_VENV" ]]; then
        log_warn "Mevcut venv bulundu: $QWM_VENV"
        if confirm "Mevcut venv silinip yeniden oluşturulsun mu?"; then
            rm -rf "$QWM_VENV"
        else
            log_sub "Mevcut venv kullanılıyor"
        fi
    fi

    if [[ ! -d "$QWM_VENV" ]]; then
        log_sub "Sanal ortam oluşturuluyor: $QWM_VENV"
        $PYTHON_CMD -m venv "$QWM_VENV" || \
            log_fatal "Venv oluşturulamadı"
    fi

    # ── Pip güncelle ──────────────────────────────────────────────────────
    log_sub "pip güncelleniyor..."
    "$QWM_VENV/bin/pip" install --upgrade pip >> "$LOG_FILE" 2>&1

    # ── Python paketleri ──────────────────────────────────────────────────
    log_sub "Python kütüphaneleri kuruluyor..."

    local pip_packages=(
        "python-xlib==0.33"
        "psutil>=5.9.0"
        "xcffib>=1.4.0"
    )

    # NVIDIA varsa pynvml ekle
    if [[ "$FLAG_NVIDIA" == true ]] && [[ "$NVIDIA_DETECTED" == true ]]; then
        pip_packages+=("nvidia-ml-py>=12.0.0")
    fi

    for pkg in "${pip_packages[@]}"; do
        log_sub "Kuruluyor: $pkg"
        "$QWM_VENV/bin/pip" install "$pkg" >> "$LOG_FILE" 2>&1 || {
            # Versiyon kısıtlaması olmadan dene
            local pkg_name
            pkg_name=$(echo "$pkg" | cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1)
            log_warn "$pkg başarısız — $pkg_name deniyor"
            "$QWM_VENV/bin/pip" install "$pkg_name" >> "$LOG_FILE" 2>&1 || \
                log_warn "$pkg_name kurulamadı — devam"
        }
    done

    # ── Kurulum doğrula ───────────────────────────────────────────────────
    log_sub "Python paketleri doğrulanıyor..."

    "$QWM_VENV/bin/python" -c "import Xlib; print('  python-xlib ✓')" || \
        log_warn "python-xlib import hatası"

    "$QWM_VENV/bin/python" -c "import psutil; print('  psutil ✓')" || \
        log_warn "psutil import hatası"

    if [[ "$FLAG_NVIDIA" == true ]]; then
        "$QWM_VENV/bin/python" -c "import pynvml; print('  pynvml ✓')" || \
            log_warn "pynvml import hatası"
    fi

    log_info "Python ortamı hazır: $QWM_VENV"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QWM PROJE YAPISI OLUŞTURMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

create_qwm_structure() {
    log_step "QWM Proje Yapısı Oluşturuluyor..."

    # ── Ana dizinler ───────────────────────────────────────────────────────
    local dirs=(
        "$QWM_DIR"
        "$QWM_DIR/core"
        "$QWM_DIR/x11"
        "$QWM_DIR/input"
        "$QWM_DIR/layout"
        "$QWM_DIR/nvidia"
        "$QWM_DIR/compositor"
        "$QWM_DIR/game_mode"
        "$QWM_DIR/ipc"
        "$QWM_DIR/bar"
        "$QWM_DIR/utils"
        "$QWM_DIR/config"
        "$QWM_DIR/scripts"
        "$QWM_DIR/tests"
        "$QWM_CONFIG_DIR"
        "$QWM_LOG_DIR"
        "$HOME/.cache/qwm"
        "$HOME/.cache/nv"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_debug "Dizin: $dir"
    done

    # ── __init__.py dosyaları ──────────────────────────────────────────────
    local packages=(
        "core" "x11" "input" "layout" "nvidia"
        "compositor" "game_mode" "ipc" "bar" "utils"
    )

    for pkg in "${packages[@]}"; do
        local init_file="$QWM_DIR/$pkg/__init__.py"
        if [[ ! -f "$init_file" ]]; then
            cat > "$init_file" << EOF
# QWM — ${pkg} package
# Auto-generated by QWM installer v${QWM_VERSION}
EOF
        fi
    done

    # ── requirements.txt ──────────────────────────────────────────────────
    cat > "$QWM_DIR/requirements.txt" << EOF
# QWM Python Dependencies
# Generated by installer v${QWM_VERSION}
# Install: pip install -r requirements.txt

python-xlib>=0.33
psutil>=5.9.0
xcffib>=1.4.0
$([ "$NVIDIA_DETECTED" = true ] && echo "nvidia-ml-py>=12.0.0" || echo "# nvidia-ml-py>=12.0.0  # NVIDIA yoksa devre dışı")
EOF

    # ── Minimal main.py oluştur (yoksa) ────────────────────────────────────
    if [[ ! -f "$QWM_DIR/main.py" ]]; then
        write_minimal_main_py
    fi

    log_info "QWM dizin yapısı oluşturuldu: $QWM_DIR"
}

write_minimal_main_py() {
    cat > "$QWM_DIR/main.py" << 'PYEOF'
#!/usr/bin/env python3
"""
QWM — Q Window Manager
NVIDIA Optimized X11 Tiling Window Manager

Bu dosya QWM Gemini prompt ile üretilmeli.
Şu an minimal bir başlatıcı görevi görüyor.

Kullanım:
    python main.py
    python main.py --debug
    python main.py --display :0
"""

import sys
import os
import argparse
import logging

# ── Versiyon kontrolü ─────────────────────────────────────────────────────
if sys.version_info < (3, 11):
    print(f"HATA: Python 3.11+ gerekli (mevcut: {sys.version})")
    sys.exit(1)

# ── Import kontrolü ───────────────────────────────────────────────────────
def check_imports() -> bool:
    errors = []

    try:
        import Xlib
        print(f"  ✓ python-xlib {Xlib.__version__}")
    except ImportError as e:
        errors.append(f"  ✗ python-xlib: {e}")

    try:
        import psutil
        print(f"  ✓ psutil {psutil.__version__}")
    except ImportError as e:
        errors.append(f"  ✗ psutil: {e}")

    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        print(f"  ✓ pynvml — GPU: {name}")
        pynvml.nvmlShutdown()
    except ImportError:
        print("  ! pynvml: NVIDIA olmadan çalışılıyor")
    except Exception as e:
        print(f"  ! pynvml: {e} (NVIDIA devre dışı)")

    if errors:
        for err in errors:
            print(err)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="QWM — NVIDIA Optimized X11 Tiling Window Manager"
    )
    parser.add_argument("--debug",    action="store_true", help="Debug modu")
    parser.add_argument("--display",  default=None,        help="X Display")
    parser.add_argument("--config",   default=None,        help="Config dosyası")
    parser.add_argument("--version",  action="store_true", help="Versiyon")
    parser.add_argument("--check",    action="store_true", help="Bağımlılık kontrolü")
    args = parser.parse_args()

    if args.version:
        print("QWM 0.1.0")
        sys.exit(0)

    print("╔══════════════════════════════════════════╗")
    print("║  QWM — Q Window Manager v0.1.0           ║")
    print("║  NVIDIA Optimized X11 Tiling WM          ║")
    print("╚══════════════════════════════════════════╝")
    print()

    print("Bağımlılık kontrolü:")
    if not check_imports():
        print("\nEksik bağımlılıklar var — kurun:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    if args.check:
        print("\nTüm bağımlılıklar tamam!")
        sys.exit(0)

    print()
    print("QWM tam implementasyon için Gemini prompt kullanın.")
    print("Şu an sadece bağımlılık kontrolü yapılıyor.")
    print()
    print("DISPLAY:", os.environ.get("DISPLAY", "Ayarlanmamış"))

    # Config dizini yoksa oluştur
    config_dir = os.path.expanduser("~/.config/qwm")
    os.makedirs(config_dir, exist_ok=True)

    log_dir = os.path.expanduser("~/.local/share/qwm")
    os.makedirs(log_dir, exist_ok=True)

    print("Config dizini:", config_dir)
    print("Log dizini:", log_dir)


if __name__ == "__main__":
    main()
PYEOF
    chmod +x "$QWM_DIR/main.py"
    log_info "Minimal main.py oluşturuldu"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM-WIDE LAUNCHER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_launcher() {
    log_step "QWM Sistem Launcher Kuruluyor..."

    # ── Ana QWM launcher ──────────────────────────────────────────────────
    sudo tee "$QWM_BIN" > /dev/null << LAUNCHER
#!/bin/bash
# /usr/local/bin/qwm — QWM sistem launcher
# QWM Installer v${QWM_VERSION} tarafından oluşturuldu

# ── Kullanıcı tespiti ─────────────────────────────────────────────────────
QWM_USER="\${SUDO_USER:-\$USER}"
QWM_HOME=\$(eval echo "~\$QWM_USER")
QWM_DIR="\$QWM_HOME/qwm"
QWM_VENV="\$QWM_DIR/venv"

# ── Venv kontrolü ────────────────────────────────────────────────────────
if [[ ! -d "\$QWM_VENV" ]]; then
    echo "HATA: QWM venv bulunamadı: \$QWM_VENV"
    echo "Kurulum için: ~/qwm/scripts/install.sh"
    exit 1
fi

# ── NVIDIA ortam değişkenleri (desktop modu) ──────────────────────────────
export __GL_SYNC_TO_VBLANK=1
export __GL_MaxFramesAllowed=2
export __GL_THREADED_OPTIMIZATIONS=1
export __GL_SHADER_DISK_CACHE=1
export __GL_SHADER_DISK_CACHE_PATH="\$HOME/.cache/nv"

# Proton/Wine
export PROTON_ENABLE_NVAPI=1
export DXVK_NVAPI_ENABLE=1

# ── XDG ───────────────────────────────────────────────────────────────────
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=QWM
export XDG_CONFIG_HOME="\${XDG_CONFIG_HOME:-\$HOME/.config}"
export XDG_DATA_HOME="\${XDG_DATA_HOME:-\$HOME/.local/share}"

# ── Log dizini ────────────────────────────────────────────────────────────
mkdir -p "\$HOME/.local/share/qwm"
mkdir -p "\$HOME/.cache/nv"

# ── QWM başlat ────────────────────────────────────────────────────────────
exec "\$QWM_VENV/bin/python" "\$QWM_DIR/main.py" "\$@"
LAUNCHER

    sudo chmod +x "$QWM_BIN"
    log_info "QWM launcher: $QWM_BIN"

    # ── qwm-msg IPC client ────────────────────────────────────────────────
    sudo tee "$QWM_MSG_BIN" > /dev/null << 'MSG'
#!/bin/bash
# /usr/local/bin/qwm-msg — QWM IPC client

SOCKET="${XDG_RUNTIME_DIR:-/tmp}/qwm-${USER}.sock"

if [[ ! -S "$SOCKET" ]]; then
    echo "Hata: QWM socket bulunamadı: $SOCKET"
    echo "QWM çalışıyor mu? systemctl status qwm"
    exit 1
fi

if [[ $# -eq 0 ]]; then
    echo "Kullanım: qwm-msg <komut> [argümanlar]"
    echo ""
    echo "Komutlar:"
    echo "  query windows       Açık pencereler"
    echo "  query workspaces    Çalışma alanları"
    echo "  query gpu           GPU metrikleri"
    echo "  query game_mode     Oyun modu durumu"
    echo "  command game_mode on|off|toggle"
    echo "  command workspace N"
    echo "  command quit"
    exit 0
fi

echo "$*" | socat - "UNIX-CONNECT:$SOCKET" 2>/dev/null || {
    echo "Hata: QWM ile iletişim kurulamadı"
    exit 1
}
MSG

    sudo chmod +x "$QWM_MSG_BIN"
    log_info "qwm-msg: $QWM_MSG_BIN"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISPLAY MANAGER KURULUMU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

install_display_manager() {
    if [[ "$FLAG_DM" == false ]]; then
        log_warn "Display manager kurulumu atlandı"
        write_xinitrc
        return 0
    fi

    log_step "Display Manager Kuruluyor..."

    # ── DM seçimi ─────────────────────────────────────────────────────────
    local dm_choice="$FLAG_DM_CHOICE"

    if [[ "$dm_choice" == "auto" ]]; then
        # Mevcut DM varsa kullan
        if [[ "$EXISTING_DM" != "none" ]]; then
            dm_choice="$EXISTING_DM"
            log_sub "Mevcut DM kullanılıyor: $dm_choice"
        else
            dm_choice="sddm"    # NVIDIA için varsayılan
            log_sub "Varsayılan DM: sddm (NVIDIA önerisi)"
        fi
    fi

    # ── DM kurulumu ───────────────────────────────────────────────────────
    case "$dm_choice" in
        sddm)
            install_sddm
            ;;
        lightdm)
            install_lightdm
            ;;
        gdm)
            install_gdm
            ;;
        ly)
            install_ly
            ;;
        *)
            log_warn "Bilinmeyen DM: $dm_choice — sddm kuruluyor"
            install_sddm
            ;;
    esac

    # ── Desktop entry ────────────────────────────────────────────────────
    write_desktop_entry

    # ── xinitrc de yaz ────────────────────────────────────────────────────
    write_xinitrc
}

install_sddm() {
    log_sub "SDDM kuruluyor..."
    pacman_install sddm

    # SDDM yapılandırması
    sudo mkdir -p /etc/sddm.conf.d

    sudo tee /etc/sddm.conf.d/qwm.conf > /dev/null << EOF
# QWM için SDDM yapılandırması

[General]
DefaultSession=qwm.desktop
RememberLastSession=true
RememberLastUser=true

[X11]
# NVIDIA için önemli X11 parametreleri
ServerArguments=-nolisten tcp -dpi 96
DisplayCommand=/usr/share/sddm/scripts/Xsetup

[Theme]
Current=
EOF

    # SDDM Xsetup scripti
    sudo tee /usr/share/sddm/scripts/Xsetup > /dev/null << 'EOF'
#!/bin/sh
# SDDM Xsetup — QWM/NVIDIA için

# NVIDIA ayarları (giriş ekranında temel optimizasyon)
if command -v nvidia-settings > /dev/null 2>&1; then
    nvidia-settings -a \
        "CurrentMetaMode=nvidia-auto-select +0+0 \
        { ForceCompositionPipeline = On }" 2>/dev/null || true
fi

# xrandr otomatik algılama
if command -v xrandr > /dev/null 2>&1; then
    xrandr --auto 2>/dev/null || true
fi
EOF
    sudo chmod +x /usr/share/sddm/scripts/Xsetup

    # SDDM servisi
    enable_service "sddm"
    log_info "SDDM kuruldu ve yapılandırıldı"
}

install_lightdm() {
    log_sub "LightDM kuruluyor..."
    pacman_install lightdm lightdm-gtk-greeter

    # LightDM yapılandırması
    sudo tee /etc/lightdm/lightdm.conf.d/qwm.conf > /dev/null << EOF
[Seat:*]
# QWM varsayılan oturum
user-session=qwm
greeter-session=lightdm-gtk-greeter

[LightDM]
# Oturumlar dizini
sessions-directory=/usr/share/xsessions
EOF

    enable_service "lightdm"
    log_info "LightDM kuruldu"
}

install_gdm() {
    log_sub "GDM kuruluyor..."
    pacman_install gdm

    # GDM X11 zorla (Wayland değil)
    sudo sed -i 's/#WaylandEnable=false/WaylandEnable=false/' \
        /etc/gdm/custom.conf 2>/dev/null || true

    enable_service "gdm"
    log_info "GDM kuruldu (X11 modu)"
}

install_ly() {
    log_sub "Ly (TUI display manager) kuruluyor..."
    aur_install ly || pacman_install ly || {
        log_warn "Ly kurulamadı — sddm kuruluyor"
        install_sddm
        return 0
    }

    enable_service "ly"
    log_info "Ly kuruldu"
}

enable_service() {
    local service="$1"

    case "$INIT_SYSTEM" in
        systemd)
            # Önce aktif olan DM'leri devre dışı bırak
            for dm in sddm lightdm gdm lxdm slim ly xdm; do
                if [[ "$dm" != "$service" ]]; then
                    sudo systemctl disable "$dm" >> "$LOG_FILE" 2>&1 || true
                fi
            done
            sudo systemctl enable "$service" >> "$LOG_FILE" 2>&1 && \
                log_info "${service} servisi etkinleştirildi"
            ;;
        openrc)
            sudo rc-update add "$service" default >> "$LOG_FILE" 2>&1 && \
                log_info "${service} OpenRC'ye eklendi"
            ;;
        runit)
            sudo ln -sf "/etc/runit/sv/${service}" \
                "/run/runit/service/" 2>/dev/null && \
                log_info "${service} runit'e eklendi"
            ;;
        s6)
            sudo s6-rc-bundle-update add default "$service" >> \
                "$LOG_FILE" 2>&1 && \
                log_info "${service} s6'ya eklendi"
            ;;
        *)
            log_warn "Init sistemi bilinmiyor — $service manuel başlatın"
            ;;
    esac
}

write_desktop_entry() {
    log_sub "Desktop entry oluşturuluyor..."
    sudo mkdir -p "$XSESSIONS_DIR"

    sudo tee "$XSESSIONS_DIR/qwm.desktop" > /dev/null << EOF
[Desktop Entry]
Name=QWM
Comment=Q Window Manager — NVIDIA Optimized X11 Tiling WM
Exec=$QWM_BIN
TryExec=$QWM_BIN
Type=Application
DesktopNames=QWM
Keywords=tiling;x11;nvidia;gaming;wm;qwm
EOF

    sudo chmod 644 "$XSESSIONS_DIR/qwm.desktop"
    log_info "Desktop entry: $XSESSIONS_DIR/qwm.desktop"
}

write_xinitrc() {
    log_sub ".xinitrc oluşturuluyor..."

    # Mevcut varsa yedekle
    if [[ -f "$HOME/.xinitrc" ]]; then
        cp "$HOME/.xinitrc" "$HOME/.xinitrc.bak.$(date +%Y%m%d)"
        log_sub "Mevcut .xinitrc yedeklendi"
    fi

    cat > "$HOME/.xinitrc" << XINITRC
#!/bin/bash
# ~/.xinitrc — QWM için X11 başlangıç scripti
# QWM Installer v${QWM_VERSION} tarafından oluşturuldu

# ── XDG ───────────────────────────────────────────────────────────────────
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=QWM

# ── NVIDIA OpenGL (desktop modu) ──────────────────────────────────────────
export __GL_SYNC_TO_VBLANK=1
export __GL_MaxFramesAllowed=2
export __GL_THREADED_OPTIMIZATIONS=1
export __GL_SHADER_DISK_CACHE=1
export __GL_SHADER_DISK_CACHE_PATH="\$HOME/.cache/nv"

# Proton/Wine/DXVK
export PROTON_ENABLE_NVAPI=1
export DXVK_NVAPI_ENABLE=1

# ── Xresources ────────────────────────────────────────────────────────────
[[ -f ~/.Xresources ]] && xrdb -merge ~/.Xresources

# ── X11 Temel Ayarları ────────────────────────────────────────────────────
xset r rate 200 30          # Tuş tekrar (ms delay, Hz rate)
xset m 0 0                  # Fare hızlandırması kapat
xset s off                  # Ekran koruyucu kapat
xset -dpms                  # DPMS kapat
xset s noblank              # Ekran kararmasın

# ── Arkaplan Servisleri ───────────────────────────────────────────────────
# Bildirim daemon (varsa)
command -v dunst && dunst &

# NetworkManager applet (varsa)
command -v nm-applet && nm-applet &

# Ses (varsa)
command -v pipewire && pipewire &
command -v wireplumber && wireplumber &

# ── QWM Başlat ────────────────────────────────────────────────────────────
exec $QWM_BIN
XINITRC

    chmod +x "$HOME/.xinitrc"
    log_info ".xinitrc oluşturuldu"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# XRESOURCES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

write_xresources() {
    log_step ".Xresources Yazılıyor..."

    if [[ -f "$HOME/.Xresources" ]]; then
        cp "$HOME/.Xresources" "$HOME/.Xresources.bak.$(date +%Y%m%d)"
        log_sub "Mevcut .Xresources yedeklendi"
    fi

    cat > "$HOME/.Xresources" << 'XRES'
! ~/.Xresources — QWM için X11 kaynak ayarları

! ── DPI ──────────────────────────────────────────────────────────────────
! 1080p için 96, 1440p için 109, 4K için 163
Xft.dpi: 96

! ── Font Rendering ────────────────────────────────────────────────────────
Xft.antialias:  true
Xft.hinting:    true
Xft.hintstyle:  hintfull
Xft.rgba:       rgb
Xft.lcdfilter:  lcddefault

! ── QWM Renk Teması ──────────────────────────────────────────────────────
*background:    #0D0D1A
*foreground:    #E8E8F0
*cursorColor:   #00FF88

! Siyah
*color0:        #1A1A2E
*color8:        #333355

! Kırmızı
*color1:        #FF4444
*color9:        #FF6666

! Yeşil (QWM ana rengi)
*color2:        #00FF88
*color10:       #44FFAA

! Sarı
*color3:        #FFAA00
*color11:       #FFCC44

! Mavi
*color4:        #0088FF
*color12:       #44AAFF

! Mor
*color5:        #AA44FF
*color13:       #CC88FF

! Cyan
*color6:        #00CCFF
*color14:       #44DDFF

! Beyaz
*color7:        #CCCCDD
*color15:       #EEEEFF

! ── XTerm Ayarları ───────────────────────────────────────────────────────
XTerm*faceName:         JetBrains Mono
XTerm*faceSize:         10
XTerm*saveLines:        10000
XTerm*scrollBar:        false
XTerm*borderWidth:      0
XTerm*internalBorder:   8
XTerm*termName:         xterm-256color
XTerm*utf8:             1
XTerm*locale:           true
XTerm*dynamicColors:    true
XTerm*selectToClipboard: true
XRES

    log_info ".Xresources oluşturuldu"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCRIPTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

write_scripts() {
    log_step "Yardımcı Scriptler Yazılıyor..."

    # ── Debug scripti ─────────────────────────────────────────────────────
    cat > "$QWM_DIR/scripts/debug.sh" << DEBUGSH
#!/bin/bash
# QWM Debug — Xephyr ile güvenli test ortamı

DISPLAY_NUM=:99

echo "QWM Debug Modu — Xephyr İçinde Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Eski Xephyr kapat
pkill -f "Xephyr \$DISPLAY_NUM" 2>/dev/null || true
sleep 0.5

# Xephyr başlat
if ! command -v Xephyr &>/dev/null; then
    echo "HATA: Xephyr kurulu değil"
    echo "Kur: sudo pacman -S xorg-server-xephyr"
    exit 1
fi

Xephyr -br -ac -noreset -screen 1280x720 \$DISPLAY_NUM &
XEPHYR_PID=\$!
echo "Xephyr PID: \$XEPHYR_PID"
sleep 1

# QWM başlat
DISPLAY=\$DISPLAY_NUM $QWM_BIN --debug &
QWM_PID=\$!
echo "QWM PID: \$QWM_PID"
sleep 1

# Terminal aç
DISPLAY=\$DISPLAY_NUM xterm &

echo ""
echo "Test ortamı hazır. Kapatmak için:"
echo "  pkill Xephyr"
wait \$XEPHYR_PID
kill \$QWM_PID 2>/dev/null || true
DEBUGSH

    # ── Test scripti ──────────────────────────────────────────────────────
    cat > "$QWM_DIR/scripts/test.sh" << TESTSH
#!/bin/bash
# QWM bağımlılık testi

source "$QWM_VENV/bin/activate"
python "$QWM_DIR/main.py" --check
TESTSH

    # ── GPU durum scripti ─────────────────────────────────────────────────
    cat > "$QWM_DIR/scripts/gpu_status.sh" << 'GPUSH'
#!/bin/bash
# NVIDIA GPU durumu

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  QWM — NVIDIA GPU Durumu"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v nvidia-smi &>/dev/null; then
    echo "nvidia-smi bulunamadı"
    exit 1
fi

nvidia-smi --query-gpu=\
name,\
driver_version,\
temperature.gpu,\
utilization.gpu,\
utilization.memory,\
memory.used,\
memory.total,\
power.draw,\
power.limit,\
clocks.current.graphics,\
clocks.current.memory \
--format=csv,noheader,nounits | \
awk -F',' '{
    printf "GPU       : %s\n", $1
    printf "Sürücü    : %s\n", $2
    printf "Sıcaklık  : %s°C\n", $3
    printf "GPU Kull.  : %s%%\n", $4
    printf "VRAM Kull. : %s%%\n", $5
    printf "VRAM       : %s / %s MB\n", $6, $7
    printf "Güç        : %s / %s W\n", $8, $9
    printf "Core Clock : %s MHz\n", $10
    printf "Mem Clock  : %s MHz\n", $11
}'

echo ""
echo "PowerMizer:"
nvidia-settings -q GPUPowerMizerMode 2>/dev/null | \
    grep "Attribute" || echo "  nvidia-settings erişilemedi"

echo ""
echo "G-Sync:"
nvidia-settings -q AllowGSYNC 2>/dev/null | \
    grep "Attribute" || echo "  G-Sync bilgisi alınamadı"
GPUSH

    # İzinleri ayarla
    chmod +x "$QWM_DIR/scripts/"*.sh

    log_info "Scriptler oluşturuldu: $QWM_DIR/scripts/"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GAMEMODE YAPILANDIRMASI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

configure_gamemode() {
    if ! command -v gamemoded &>/dev/null; then
        log_warn "gamemode kurulu değil — atlanıyor"
        return 0
    fi

    log_step "Feral GameMode Yapılandırılıyor..."

    mkdir -p "$HOME/.config"

    cat > "$HOME/.config/gamemode.ini" << EOF
[general]
; QWM tarafından yönetilir
reaper_freq=5
defaultgov=performance
softrealtime=auto
renice=10

[filter]
; Kara liste — bunlar için game mode aktif olmaz
blacklist=kwin_x11
blacklist=plasmashell
blacklist=sddm

[gpu]
; NVIDIA GPU optimizasyonları
apply_gpu_optimisations=accept-responsibility
gpu_device=0
nv_powermizer_mode=1

[custom]
; QWM ile entegrasyon
start=notify-send "Game Mode" "Aktif" 2>/dev/null || true
end=notify-send "Game Mode" "Deaktif" 2>/dev/null || true
EOF

    # Kullanıcıyı gamemode grubuna ekle
    if getent group gamemode &>/dev/null; then
        sudo usermod -aG gamemode "$USER"
        log_info "Kullanıcı gamemode grubuna eklendi"
    fi

    # GameMode servisi
    if [[ "$INIT_SYSTEM" == "systemd" ]]; then
        systemctl --user enable gamemoded >> "$LOG_FILE" 2>&1 || true
        log_info "GameMode servisi etkinleştirildi"
    fi

    log_info "Feral GameMode yapılandırıldı"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KALDıRMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

uninstall_qwm() {
    log_step "QWM Kaldırılıyor..."

    echo -e "${RED}${BOLD}UYARI: Bu işlem QWM'i tamamen kaldıracak!${NC}"
    if ! confirm "Devam etmek istediğinize emin misiniz?" "n"; then
        log_info "Kaldırma iptal edildi"
        exit 0
    fi

    # Desktop entry
    sudo rm -f "$XSESSIONS_DIR/qwm.desktop" && \
        log_info "Desktop entry kaldırıldı"

    # Launcher
    sudo rm -f "$QWM_BIN" "$QWM_MSG_BIN" && \
        log_info "Launcher kaldırıldı"

    # xorg.conf
    sudo rm -f /etc/X11/xorg.conf.d/20-nvidia-qwm.conf && \
        log_info "NVIDIA xorg.conf kaldırıldı"

    # SDDM config
    sudo rm -f /etc/sddm.conf.d/qwm.conf && \
        log_info "SDDM config kaldırıldı"

    # QWM dizini
    if confirm "QWM dizini silinsin mi? ($QWM_DIR)"; then
        rm -rf "$QWM_DIR"
        log_info "QWM dizini silindi"
    fi

    # Config dizini
    if confirm "Config dizini silinsin mi? ($QWM_CONFIG_DIR)"; then
        rm -rf "$QWM_CONFIG_DIR"
        log_info "Config dizini silindi"
    fi

    # Log dizini
    if confirm "Log dizini silinsin mi? ($QWM_LOG_DIR)"; then
        rm -rf "$QWM_LOG_DIR"
        log_info "Log dizini silindi"
    fi

    log_success "QWM kaldırıldı"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KURULUM DOĞRULAMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

verify_installation() {
    log_step "Kurulum Doğrulanıyor..."

    local pass=0
    local fail=0
    local warn=0

    check_item() {
        local desc="$1"
        local cmd="$2"
        local required="${3:-true}"

        if eval "$cmd" &>/dev/null; then
            echo -e "    ${GREEN}[✓]${NC} $desc"
            ((pass++))
        else
            if [[ "$required" == "true" ]]; then
                echo -e "    ${RED}[✗]${NC} $desc"
                ((fail++))
            else
                echo -e "    ${YELLOW}[!]${NC} $desc (opsiyonel)"
                ((warn++))
            fi
        fi
    }

    echo ""
    echo -e "  ${BOLD}── Sistem ────────────────────────────────${NC}"
    check_item "Arch tabanlı"         "command -v pacman"
    check_item "Python 3.11+"         "$PYTHON_CMD -c 'import sys; assert sys.version_info >= (3,11)'"
    check_item "X11 server"           "command -v Xorg || command -v X"
    check_item "xrandr"               "command -v xrandr"

    echo ""
    echo -e "  ${BOLD}── NVIDIA ────────────────────────────────${NC}"
    if [[ "$FLAG_NVIDIA" == true ]]; then
        check_item "NVIDIA kernel modülü" "lsmod | grep -q nvidia"
        check_item "nvidia-smi"           "command -v nvidia-smi"
        check_item "nvidia-settings"      "command -v nvidia-settings"
        check_item "GPU yanıt veriyor"    "nvidia-smi --query-gpu=name --format=csv,noheader"
        check_item "xorg.conf.d (NVIDIA)" "test -f /etc/X11/xorg.conf.d/20-nvidia-qwm.conf"
    else
        echo -e "    ${YELLOW}[!]${NC} NVIDIA kurulumu atlandı"
    fi

    echo ""
    echo -e "  ${BOLD}── Python Kütüphaneleri ──────────────────${NC}"
    check_item "venv"         "test -d $QWM_VENV"
    check_item "python-xlib"  "$QWM_VENV/bin/python -c 'import Xlib'"
    check_item "psutil"       "$QWM_VENV/bin/python -c 'import psutil'"
    if [[ "$NVIDIA_DETECTED" == true ]]; then
        check_item "pynvml"   "$QWM_VENV/bin/python -c 'import pynvml'"
    fi

    echo ""
    echo -e "  ${BOLD}── QWM Dosyaları ─────────────────────────${NC}"
    check_item "QWM dizini"       "test -d $QWM_DIR"
    check_item "main.py"          "test -f $QWM_DIR/main.py"
    check_item "requirements.txt" "test -f $QWM_DIR/requirements.txt"
    check_item "qwm launcher"     "test -x $QWM_BIN"
    check_item "qwm-msg"          "test -x $QWM_MSG_BIN"

    echo ""
    echo -e "  ${BOLD}── Display Manager ───────────────────────${NC}"
    if [[ "$FLAG_DM" == true ]]; then
        check_item "qwm.desktop"  "test -f $XSESSIONS_DIR/qwm.desktop"
        check_item "xinitrc"      "test -f $HOME/.xinitrc"

        case "$INIT_SYSTEM" in
            systemd)
                local dm_active=false
                for dm in sddm lightdm gdm ly; do
                    if systemctl is-enabled "$dm" &>/dev/null; then
                        dm_active=true
                        echo -e "    ${GREEN}[✓]${NC} DM etkin: $dm"
                        break
                    fi
                done
                [[ "$dm_active" == false ]] && {
                    echo -e "    ${RED}[✗]${NC} Hiçbir DM etkin değil"
                    ((fail++))
                }
                ;;
        esac
    fi

    echo ""
    echo -e "  ${BOLD}── Opsiyonel ─────────────────────────────${NC}"
    check_item "alacritty/kitty"  "command -v alacritty || command -v kitty" false
    check_item "rofi/dmenu"       "command -v rofi || command -v dmenu" false
    check_item "picom"            "command -v picom" false
    check_item "gamemode"         "command -v gamemoded" false
    check_item "Xephyr (test)"    "command -v Xephyr" false
    check_item "nvtop"            "command -v nvtop" false

    # Sonuç
    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}Sonuç:${NC} ${GREEN}${pass} başarılı${NC} | ${RED}${fail} başarısız${NC} | ${YELLOW}${warn} opsiyonel${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    return $fail
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KURULUM SONU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << 'SUCCESS'
  ╔══════════════════════════════════════════════════════════╗
  ║            QWM KURULUMU TAMAMLANDI!                      ║
  ╚══════════════════════════════════════════════════════════╝
SUCCESS
    echo -e "${NC}"

    echo -e "${BOLD}  Sonraki Adımlar:${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} QWM implementasyonunu Gemini ile oluşturun:"
    echo -e "     ${DIM}(prompt dosyasını Gemini'ye verin)${NC}"
    echo ""
    echo -e "  ${CYAN}2.${NC} Bağımlılıkları test edin:"
    echo -e "     ${GREEN}$QWM_DIR/scripts/test.sh${NC}"
    echo ""
    echo -e "  ${CYAN}3.${NC} Xephyr ile güvenli test:"
    echo -e "     ${GREEN}$QWM_DIR/scripts/debug.sh${NC}"
    echo ""
    echo -e "  ${CYAN}4.${NC} GPU durumunu kontrol edin:"
    echo -e "     ${GREEN}$QWM_DIR/scripts/gpu_status.sh${NC}"
    echo ""
    echo -e "  ${CYAN}5.${NC} Sistemi yeniden başlatın:"
    echo -e "     ${GREEN}sudo reboot${NC}"
    echo ""
    echo -e "  ${CYAN}6.${NC} Giriş ekranında ${BOLD}QWM${NC}'i seçin"
    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${DIM}Kurulum logu: $LOG_FILE${NC}"
    echo -e "  ${DIM}QWM dizini : $QWM_DIR${NC}"
    echo -e "  ${DIM}Config     : $QWM_CONFIG_DIR${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$FLAG_NO_REBOOT" == false ]]; then
        if confirm "Şimdi yeniden başlatılsın mı? (Önerilen)"; then
            log_info "Yeniden başlatılıyor..."
            sleep 2
            sudo reboot
        fi
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANA AKIŞ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    # Log dosyası başlat
    echo "QWM Install Log — $(date)" > "$LOG_FILE"
    echo "Args: $*" >> "$LOG_FILE"

    parse_args "$@"
    show_banner
    detect_system

    # Kaldırma modu
    if [[ "$FLAG_UNINSTALL" == true ]]; then
        uninstall_qwm
        exit 0
    fi

    # Kurulum onayı
    echo -e "${BOLD}  Kurulacaklar:${NC}"
    echo -e "    ${GREEN}✓${NC} Temel X11 bağımlılıkları"
    echo -e "    ${GREEN}✓${NC} Python 3.11+ ve sanal ortam"
    [[ "$FLAG_NVIDIA" == true ]] && \
        echo -e "    ${GREEN}✓${NC} NVIDIA sürücüleri (${KERNEL_TYPE} kernel)"
    echo -e "    ${GREEN}✓${NC} QWM dizin yapısı"
    echo -e "    ${GREEN}✓${NC} Uygulama bağımlılıkları"
    [[ "$FLAG_DM" == true ]] && \
        echo -e "    ${GREEN}✓${NC} Display Manager"
    echo ""

    if ! confirm "Kurulum başlasın mı?"; then
        echo "Kurulum iptal edildi"
        exit 0
    fi

    echo ""

    # ── Kurulum adımları ──────────────────────────────────────────────────
    update_system
    install_aur_helper
    install_base_deps
    install_nvidia
    install_app_deps
    setup_python_env
    create_qwm_structure
    install_launcher
    install_display_manager
    write_xresources
    write_scripts
    configure_gamemode

    # ── Doğrulama ────────────────────────────────────────────────────────
    verify_installation || log_warn "Bazı doğrulamalar başarısız — log'u inceleyin"

    # ── Tamamlandı ────────────────────────────────────────────────────────
    show_completion
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ÇALIŞTIR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main "$@"