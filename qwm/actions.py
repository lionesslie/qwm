"""Tus kisayollarina baglanan eylemler. Her fonksiyon (wm, arg) alir."""
import os
import subprocess

from Xlib import X


def spawn(wm, cmd):
    try:
        subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        print(f"[QWM] Komut calistirilamadi '{cmd}': {exc}")


def kill_window(wm, _):
    win = wm.get_focused()
    if not win:
        return
    if wm.supports_protocol(win, "WM_DELETE_WINDOW"):
        wm.send_client_message(win, "WM_PROTOCOLS", [wm.atom("WM_DELETE_WINDOW"), X.CurrentTime])
    else:
        try:
            wm.display.kill_client(win.id)
        except Exception:
            pass
    wm.display.sync()


def focus_next(wm, _):
    wm.focus_cycle(1)


def focus_prev(wm, _):
    wm.focus_cycle(-1)


def resize_master(wm, delta):
    ws = wm.current_workspace()
    ws.master_ratio = min(0.9, max(0.1, ws.master_ratio + delta))
    wm.arrange()


def toggle_fullscreen(wm, _):
    wm.toggle_fullscreen()


def toggle_floating(wm, _):
    wm.toggle_floating_focused()


def swap_master(wm, _):
    wm.swap_with_master()


def switch_workspace(wm, idx):
    wm.switch_workspace(idx)


def move_to_workspace(wm, idx):
    wm.move_focused_to_workspace(idx)


def quit_wm(wm, _):
    wm.quit()


def reload_config(wm, _):
    wm.reload_config()


ACTIONS = {
    "spawn": spawn,
    "kill_window": kill_window,
    "focus_next": focus_next,
    "focus_prev": focus_prev,
    "resize_master": resize_master,
    "toggle_fullscreen": toggle_fullscreen,
    "toggle_floating": toggle_floating,
    "swap_master": swap_master,
    "switch_workspace": switch_workspace,
    "move_to_workspace": move_to_workspace,
    "quit_wm": quit_wm,
    "reload_config": reload_config,
}