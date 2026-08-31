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
    wm.display.flush()


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


def center_floating(wm, _):
    wm.center_floating_focused()


def grow_floating(wm, _):
    wm.resize_floating_focused(1)


def shrink_floating(wm, _):
    wm.resize_floating_focused(-1)


def swap_master(wm, _):
    wm.swap_with_master()


def move_window_next(wm, _):
    wm.move_window(1)


def move_window_prev(wm, _):
    wm.move_window(-1)


def cycle_layout(wm, _):
    wm.cycle_layout()


def toggle_monocle(wm, _):
    wm.toggle_monocle()


def toggle_gaps(wm, _):
    wm.toggle_gaps()


def toggle_scratchpad(wm, cmd):
    wm.toggle_scratchpad(cmd)


def toggle_game_mode(wm, _):
    wm.toggle_game_mode()


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
    "center_floating": center_floating,
    "grow_floating": grow_floating,
    "shrink_floating": shrink_floating,
    "swap_master": swap_master,
    "move_window_next": move_window_next,
    "move_window_prev": move_window_prev,
    "cycle_layout": cycle_layout,
    "toggle_monocle": toggle_monocle,
    "toggle_gaps": toggle_gaps,
    "toggle_scratchpad": toggle_scratchpad,
    "toggle_game_mode": toggle_game_mode,
    "switch_workspace": switch_workspace,
    "move_to_workspace": move_to_workspace,
    "quit_wm": quit_wm,
    "reload_config": reload_config,
}
