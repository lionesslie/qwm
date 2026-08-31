#!/usr/bin/env bash
# QWM'i ana oturumuna dokunmadan, izole bir pencerede test eder.
set -e

if ! command -v Xephyr &> /dev/null; then
    echo "Xephyr bulunamadi, kuruluyor..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y xserver-xephyr
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y xorg-x11-server-Xephyr
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm xorg-server-xephyr
    fi
fi

echo "Xephyr aciliyor (1280x800)..."
Xephyr -br -ac -noreset -screen 1280x800 :1 &
XEPHYR_PID=$!
sleep 1

echo "QWM Xephyr icinde baslatiliyor (DISPLAY=:1)..."
DISPLAY=:1 PYTHONPATH="$(pwd)" python3 -m qwm

kill $XEPHYR_PID 2>/dev/null || true