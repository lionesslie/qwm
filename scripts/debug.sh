#!/usr/bin/env bash
# debug.sh - Launch QWM in a nested Xephyr session for testing

set -e

# Configuration
SCREEN_SIZE="1280x720"
DISPLAY_NUM=":100"

# Temizlik trap'i — her durumda Xephyr'i kapat
cleanup() {
    echo "=> Temizleniyor..."
    kill "$QWM_PID" 2>/dev/null || true
    kill "$XEPHYR_PID" 2>/dev/null || true
    wait "$QWM_PID" 2>/dev/null || true
    wait "$XEPHYR_PID" 2>/dev/null || true
    echo "=> Kapatıldı."
}
trap cleanup EXIT INT TERM

echo "=> Xephyr başlatılıyor: $DISPLAY_NUM ($SCREEN_SIZE)"
Xephyr "$DISPLAY_NUM" -ac -screen "$SCREEN_SIZE" -br -reset -terminate &
XEPHYR_PID=$!

# Xephyr hazır olana kadar bekle (en fazla 10 saniye)
echo "=> Xephyr bekleniyor..."
for i in $(seq 1 10); do
    if DISPLAY="$DISPLAY_NUM" xdpyinfo &>/dev/null 2>&1; then
        echo "=> Xephyr hazır (${i}s)"
        break
    fi
    sleep 1
    if [[ $i -eq 10 ]]; then
        echo "HATA: Xephyr 10 saniyede başlamadı. Xephyr kurulu mu?"
        exit 1
    fi
done

echo "=> QWM başlatılıyor (debug modu)..."
# Doğru modül çağrısı: 'python3 -m qwm' (pyproject entry point: qwm.main:main)
DISPLAY="$DISPLAY_NUM" python3 -m qwm --debug &
QWM_PID=$!

echo "=> QWM PID=$QWM_PID. Çıkmak için Ctrl+C."

# QWM bitene kadar bekle
wait "$QWM_PID"
echo "=> QWM çıktı (exit kod: $?)"
