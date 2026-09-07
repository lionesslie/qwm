import os
import time
import select
import queue
import shlex
import subprocess
import logging
import threading

from Xlib import X, Xatom, error
from Xlib.display import Display
from Xlib.ext import randr

from .ewmh import EWMH
from .window import ManagedWindow, Geometry
from .workspace import WorkspaceManager, Monitor
from .layout import apply_layout
from .events import EventDispatcher

from qwm.input.keybinds import KeybindManager
from qwm.input.mouse import MouseController, BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT
from qwm.render.animator import AnimationScheduler, Animation
from qwm.render.compositor import CompositorManager
from qwm.render.decorations import DecorationConfig
from qwm.gpu.nvidia import NvidiaOptimizer
from qwm.gamemode.gamemode import GameModeController

logger = logging.getLogger("qwm.wm")

MOD_KEY_MASKS = {"super": X.Mod4Mask, "alt": X.Mod1Mask}


class WindowManager:
    def __init__(self, config, config_path):
        self.config = config
        self.config_path = config_path

        self.display = Display()
        self.screen = self.display.screen()
        self.root = self.screen.root

        self.ewmh = EWMH(self.display, self.root)
        self.windows = {}
        self.dispatcher = EventDispatcher()
        self.command_queue = queue.Queue()

        mod_name = config["general"].get("mod_key", "super")
        self.mod_mask = MOD_KEY_MASKS.get(mod_name, X.Mod4Mask)

        ws_cfg = config["workspaces"]
        self.workspaces = WorkspaceManager(
            ws_cfg["count"], ws_cfg["names"], config["general"]["default_layout"]
        )

        self.decorations = DecorationConfig.from_config(config["general"], config["colors"])

        self.keybinds = KeybindManager(self.display, self.root, self._on_keybind)
        self.mouse = MouseController(self.display, self.root, self.mod_mask, self._on_drag_end)

        config_dir = os.path.dirname(os.path.abspath(config_path)) or os.path.expanduser("~/.config/qwm")
        self.compositor = CompositorManager(config_dir)

        self.animator_enabled = {"enabled": config["animations"].get("enabled", True)}
        self.animator = AnimationScheduler(fps=config["animations"].get("fps", 60))

        self.nvidia = NvidiaOptimizer(config["nvidia"])
        self.gamemode = GameModeController(config["gamemode"], self.compositor, self.animator_enabled)

        self.focused_window_id = None
        self.scratchpad_window_id = None
        self._suppress_enter_until = 0.0
        self._running = False
        self._register_handlers()

    def _register_handlers(self):
        self.dispatcher.register(X.MapRequest, self._on_map_request)
        self.dispatcher.register(X.UnmapNotify, self._on_unmap_notify)
        self.dispatcher.register(X.DestroyNotify, self._on_destroy_notify)
        self.dispatcher.register(X.ConfigureRequest, self._on_configure_request)
        self.dispatcher.register(X.EnterNotify, self._on_enter_notify)
        self.dispatcher.register(X.KeyPress, self._on_key_press)
        self.dispatcher.register(X.ButtonPress, self._on_button_press)
        self.dispatcher.register(X.ButtonRelease, self._on_button_release)
        self.dispatcher.register(X.MotionNotify, self._on_motion_notify)
        self.dispatcher.register(X.ClientMessage, self._on_client_message)
        self.dispatcher.register(X.PropertyNotify, self._on_property_notify)

    def start(self):
        try:
            self.root.change_attributes(
                event_mask=(
                    X.SubstructureRedirectMask
                    | X.SubstructureNotifyMask
                    | X.EnterWindowMask
                    | X.PropertyChangeMask
                )
            )
            self.display.sync()
        except error.BadAccess:
            logger.error("baska bir window manager zaten calisiyor")
            raise SystemExit(1)

        self.ewmh.setup_supporting_wm_check()
        self.ewmh.set_supported()
        self.ewmh.set_number_of_desktops(len(self.workspaces.workspaces))
        self.ewmh.set_desktop_names([ws.name for ws in self.workspaces.workspaces])
        self.ewmh.set_current_desktop(0)
        self.ewmh.set_desktop_viewport()
        self.ewmh.set_desktop_geometry(self.screen.width_in_pixels, self.screen.height_in_pixels)

        self._detect_monitors()
        self.keybinds.grab_all(self.config["keybinds"])
        self.mouse.grab_buttons()

        self.compositor.generate_config(self.config["compositor"], self.config["animations"])
        if self.config["compositor"].get("enabled", True):
            self.compositor.start()

        self.nvidia.bootstrap()
        self.animator.start()

        self._apply_wallpaper()
        self._run_autostart()
        self._adopt_existing_windows()

        self._running = True
        logger.info("qwm baslatildi (%d workspace)", len(self.workspaces.workspaces))
        self._event_loop()

    def stop(self):
        self._running = False
        self.animator.stop()
        self.compositor.stop()
        self.keybinds.ungrab_all()
        self.display.close()

    def _detect_monitors(self):
        monitors = []
        try:
            resources = self.root.xrandr_get_screen_resources()
            for output in resources.outputs:
                info = self.display.xrandr_get_output_info(output, resources.config_timestamp)
                if info.crtc == 0:
                    continue
                crtc_info = self.display.xrandr_get_crtc_info(info.crtc, resources.config_timestamp)
                monitors.append(Monitor(
                    name=info.name,
                    x=crtc_info.x, y=crtc_info.y,
                    width=crtc_info.width, height=crtc_info.height,
                    primary=False,
                ))
        except Exception:
            logger.debug("xrandr bilgisi alinamadi, tek ekran varsayiliyor", exc_info=True)

        if not monitors:
            monitors = [Monitor("default", 0, 0, self.screen.width_in_pixels, self.screen.height_in_pixels, True)]
        self.workspaces.set_monitors(monitors)
        logger.info("monitorler: %s", monitors)

    def _apply_wallpaper(self):
        tool = self.config["apps"].get("wallpaper_tool", "feh")
        path = os.path.expanduser(self.config["apps"].get("wallpaper_path", ""))
        if tool == "feh" and os.path.exists(path):
            try:
                subprocess.Popen(["feh", "--bg-scale", path])
            except FileNotFoundError:
                logger.warning("feh bulunamadi, wallpaper atlandi")

    def _run_autostart(self):
        autostart = self.config.get("autostart", {})
        for _, cmd in autostart.items():
            if not cmd:
                continue
            try:
                subprocess.Popen(shlex.split(cmd))
            except Exception:
                logger.exception("autostart komutu basarisiz: %s", cmd)

    def _adopt_existing_windows(self):
        tree = self.root.query_tree()
        for child in tree.children:
            attrs = child.get_attributes()
            if attrs.override_redirect or attrs.map_state != X.IsViewable:
                continue
            self._manage_window(child)

    def _wm_class_name(self, window):
        wm_class, _ = self.ewmh.get_wm_class(window)
        return wm_class or ""

    def _manage_window(self, window):
        if window.id in self.windows:
            return self.windows[window.id]

        window.change_attributes(event_mask=X.EnterWindowMask | X.PropertyChangeMask)

        wm_class, wm_instance = self.ewmh.get_wm_class(window)
        wm_name = self.ewmh.get_wm_name(window)
        pid = self.ewmh.get_wm_pid(window)

        managed = ManagedWindow(window, window.id, wm_class=wm_class or "", wm_name=wm_name, pid=pid)
        managed.border_width = self.decorations.border_width

        rule = self._match_rule(managed)
        target_ws = self.workspaces.current_index
        if rule:
            if rule.get("floating"):
                managed.floating = True
            if "workspace" in rule:
                target_ws = int(rule["workspace"]) - 1

        managed.workspace = target_ws
        self.windows[window.id] = managed
        self.workspaces.get(target_ws).add(window.id)

        window.change_property(
            self.ewmh.atom["WM_STATE"], self.ewmh.atom["WM_STATE"], 32, [1, 0]
        )
        self.ewmh.set_wm_desktop(window, target_ws)

        try:
            window.configure(border_width=managed.border_width)
        except error.BadWindow:
            pass

        window.map()
        managed.mapped = True

        if target_ws == self.workspaces.current_index:
            self._relayout(target_ws)
        self._update_client_list()
        self.focus_window(window.id)
        return managed

    def _match_rule(self, managed):
        for rule in self.config.get("rules", []):
            if managed.matches_rule(rule):
                return rule
        return None

    def _unmanage_window(self, wid):
        managed = self.windows.pop(wid, None)
        if not managed:
            return
        ws = self.workspaces.find_workspace_of(wid)
        if ws:
            ws.remove(wid)
        if self.focused_window_id == wid:
            self.focused_window_id = None
        self._relayout(self.workspaces.current_index)
        self._update_client_list()

    def _relayout(self, ws_index):
        self._suppress_enter_until = time.monotonic() + 0.15
        ws = self.workspaces.get(ws_index)
        if not ws:
            return
        monitor = ws.monitor
        area = monitor.area() if monitor else (0, 0, self.screen.width_in_pixels, self.screen.height_in_pixels)

        tiled = [
            self.windows[wid] for wid in ws.window_ids
            if wid in self.windows and not self.windows[wid].floating and not self.windows[wid].hidden
        ]
        floating = [
            self.windows[wid] for wid in ws.window_ids
            if wid in self.windows and self.windows[wid].floating and not self.windows[wid].hidden
        ]

        if len(tiled) == 1 and self.windows[tiled[0].id].fullscreen:
            win = tiled[0]
            geom = area
            self._animate_geometry(win, geom)
        else:
            layout_name = ws.layout
            geometries = apply_layout(
                layout_name, tiled, area,
                self.config["general"]["gap_inner"],
                self.config["general"]["gap_outer"],
                master_ratio=ws.master_ratio,
            )
            for win in tiled:
                if win.id in geometries:
                    self._animate_geometry(win, geometries[win.id])

        for win in floating:
            try:
                win.window.map()
            except error.BadWindow:
                pass

    def _animate_geometry(self, managed, geometry):
        x, y, w, h = geometry
        w, h = managed.apply_size_hints(w, h)

        if not self.animator_enabled["enabled"]:
            self._set_geometry_now(managed, x, y, w, h)
            return

        start = managed.geometry.as_tuple()
        end = (x, y, w, h)
        if start == end:
            return

        duration = self.config["animations"].get("duration_ms", 180)
        easing = self.config["animations"].get("easing", "ease_out_cubic")

        def on_update(values):
            vx, vy, vw, vh = (int(v) for v in values)
            self._set_geometry_now(managed, vx, vy, max(1, vw), max(1, vh), configure_border=False)

        anim = Animation(start, end, duration, easing, on_update)
        self.animator.submit(anim)

    def _set_geometry_now(self, managed, x, y, w, h, configure_border=True):
        managed.geometry = Geometry(x, y, w, h)
        try:
            managed.window.configure(x=x, y=y, width=w, height=h)
        except error.BadWindow:
            pass

    def focus_window(self, wid):
        managed = self.windows.get(wid)
        if not managed:
            return
        if self.focused_window_id and self.focused_window_id in self.windows:
            prev = self.windows[self.focused_window_id]
            prev.focused = False
            self._set_border_color(prev)

        managed.focused = True
        self._set_border_color(managed)
        try:
            managed.window.set_input_focus(X.RevertToParent, X.CurrentTime)
            self.ewmh.send_take_focus(managed.window)
        except error.BadWindow:
            pass
        self.ewmh.set_active_window(wid)
        self.focused_window_id = wid
        self.display.flush()

    def _set_border_color(self, managed):
        pixel = self.decorations.active_pixel if managed.focused else self.decorations.inactive_pixel
        try:
            managed.window.change_attributes(border_pixel=pixel)
        except error.BadWindow:
            pass

    def _update_client_list(self):
        self.ewmh.set_client_list(list(self.windows.keys()))

    def _on_map_request(self, event):
        self._manage_window(event.window)

    def _on_unmap_notify(self, event):
        if event.window.id in self.windows:
            managed = self.windows[event.window.id]
            if managed.mapped:
                self._unmanage_window(event.window.id)

    def _on_destroy_notify(self, event):
        self._unmanage_window(event.window.id)

    def _on_configure_request(self, event):
        managed = self.windows.get(event.window.id)
        values = {}
        if event.value_mask & X.CWX:
            values["x"] = event.x
        if event.value_mask & X.CWY:
            values["y"] = event.y
        if event.value_mask & X.CWWidth:
            values["width"] = event.width
        if event.value_mask & X.CWHeight:
            values["height"] = event.height
        if event.value_mask & X.CWBorderWidth:
            values["border_width"] = event.border_width
        if event.value_mask & X.CWStackMode:
            values["stack_mode"] = event.stack_mode

        try:
            event.window.configure(**values)
        except error.BadWindow:
            pass

        if managed and managed.floating:
            if "x" in values:
                managed.geometry.x = values["x"]
            if "y" in values:
                managed.geometry.y = values["y"]
            if "width" in values:
                managed.geometry.width = values["width"]
            if "height" in values:
                managed.geometry.height = values["height"]

    def _on_enter_notify(self, event):
        if not self.config["general"].get("focus_follows_mouse", True):
            return
        if time.monotonic() < self._suppress_enter_until:
            return
        if event.window.id in self.windows:
            self.focus_window(event.window.id)

    def _on_key_press(self, event):
        self.keybinds.dispatch(event)

    def _on_button_press(self, event):
        wid = event.child.id if event.child else event.window.id
        managed = self.windows.get(wid)
        if not managed:
            return
        self.focus_window(wid)
        if event.detail == BUTTON_LEFT:
            managed.floating = True
            self.mouse.begin_move(managed, event.root_x, event.root_y)
        elif event.detail == BUTTON_RIGHT:
            managed.floating = True
            self.mouse.begin_resize(managed, event.root_x, event.root_y)
        elif event.detail == BUTTON_MIDDLE:
            managed.floating = not managed.floating
            self._relayout(self.workspaces.current_index)

    def _on_button_release(self, event):
        self.mouse.end_drag()

    def _on_motion_notify(self, event):
        self.mouse.motion(event.root_x, event.root_y)

    def _on_drag_end(self, managed):
        self._relayout(self.workspaces.current_index)

    def _on_client_message(self, event):
        atom_name = self.display.get_atom_name(event.client_type)
        if atom_name == "_NET_ACTIVE_WINDOW":
            self.focus_window(event.window.id)
        elif atom_name == "_NET_CLOSE_WINDOW":
            self._close_window(event.window.id)
        elif atom_name == "_NET_WM_STATE":
            self._handle_wm_state_message(event)
        elif atom_name == "_NET_CURRENT_DESKTOP":
            index = event.data.data32[0]
            self.switch_workspace(index)

    def _handle_wm_state_message(self, event):
        managed = self.windows.get(event.window.id)
        if not managed:
            return
        action = event.data.data32[0]
        atoms = [event.data.data32[1], event.data.data32[2]]
        fs_atom = self.ewmh.atom["_NET_WM_STATE_FULLSCREEN"]
        if fs_atom in atoms:
            if action == 1 or (action == 2 and not managed.fullscreen):
                self._set_fullscreen(managed, True)
            elif action == 0 or (action == 2 and managed.fullscreen):
                self._set_fullscreen(managed, False)

    def _set_fullscreen(self, managed, enabled):
        managed.fullscreen = enabled
        self.ewmh.set_fullscreen(managed.window, enabled)
        self._relayout(self.workspaces.current_index)
        if enabled:
            self.gamemode.on_window_fullscreen(managed)
        else:
            self.gamemode.on_window_unfullscreen(managed)

    def _on_property_notify(self, event):
        managed = self.windows.get(event.window.id)
        if not managed:
            return
        atom_name = self.display.get_atom_name(event.atom)
        if atom_name in ("WM_NAME", "_NET_WM_NAME"):
            managed.wm_name = self.ewmh.get_wm_name(event.window)

    def _close_window(self, wid):
        managed = self.windows.get(wid)
        if not managed:
            return
        if not self.ewmh.send_delete_window(managed.window):
            try:
                managed.window.destroy()
            except error.BadWindow:
                pass

    def _on_keybind(self, action):
        handler = getattr(self, f"action_{action}", None)
        if handler:
            handler()
        elif action.startswith("workspace_"):
            index = int(action.split("_")[1]) - 1
            self.switch_workspace(index)
        elif action.startswith("move_to_workspace_"):
            index = int(action.split("_")[-1]) - 1
            self.move_focused_to_workspace(index)

    def action_terminal(self):
        self._spawn(self.config["apps"].get("terminal", "alacritty"))

    def action_launcher(self):
        self._spawn(self.config["apps"].get("launcher", "rofi -show drun"))

    def action_close_window(self):
        if self.focused_window_id:
            self._close_window(self.focused_window_id)

    def action_fullscreen(self):
        if self.focused_window_id:
            managed = self.windows[self.focused_window_id]
            self._set_fullscreen(managed, not managed.fullscreen)

    def action_toggle_floating(self):
        if self.focused_window_id:
            managed = self.windows[self.focused_window_id]
            managed.floating = not managed.floating
            self._relayout(self.workspaces.current_index)

    def action_cycle_layout(self):
        ws = self.workspaces.current()
        order = ["master_stack", "grid", "spiral", "monocle"]
        ws.cycle_layout(order)
        self._relayout(ws.index)

    def action_focus_left(self):
        self._cycle_focus(-1)

    def action_focus_right(self):
        self._cycle_focus(1)

    def action_focus_up(self):
        self._cycle_focus(-1)

    def action_focus_down(self):
        self._cycle_focus(1)

    def _cycle_focus(self, direction):
        ws = self.workspaces.current()
        ids = ws.window_ids
        if not ids:
            return
        if self.focused_window_id not in ids:
            self.focus_window(ids[0])
            return
        idx = ids.index(self.focused_window_id)
        new_idx = (idx + direction) % len(ids)
        self.focus_window(ids[new_idx])

    def action_move_left(self):
        self._swap_focused(-1)

    def action_move_right(self):
        self._swap_focused(1)

    def action_move_up(self):
        self._swap_focused(-1)

    def action_move_down(self):
        self._swap_focused(1)

    def _swap_focused(self, direction):
        ws = self.workspaces.current()
        ids = ws.window_ids
        if self.focused_window_id not in ids or len(ids) < 2:
            return
        idx = ids.index(self.focused_window_id)
        new_idx = (idx + direction) % len(ids)
        ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
        self._relayout(ws.index)

    def action_resize_grow(self):
        ws = self.workspaces.current()
        ws.master_ratio = min(0.9, ws.master_ratio + 0.05)
        self._relayout(ws.index)

    def action_resize_shrink(self):
        ws = self.workspaces.current()
        ws.master_ratio = max(0.1, ws.master_ratio - 0.05)
        self._relayout(ws.index)

    def action_reload_config(self):
        self.reload_config()

    def action_quit_wm(self):
        self._running = False

    def action_screenshot(self):
        self._spawn("scrot -e 'mv $f ~/Pictures/ 2>/dev/null'")

    def action_lock_screen(self):
        for candidate in ("i3lock", "xlock"):
            if self._spawn(candidate):
                return

    def action_scratchpad(self):
        term = self.config["apps"].get("terminal", "alacritty")
        if self.scratchpad_window_id and self.scratchpad_window_id in self.windows:
            managed = self.windows[self.scratchpad_window_id]
            managed.hidden = not managed.hidden
            if managed.hidden:
                managed.window.unmap()
            else:
                managed.window.map()
                self.focus_window(managed.id)
        else:
            self._spawn(f"{term} --class qwm-scratchpad")

    def _spawn(self, command):
        try:
            subprocess.Popen(shlex.split(command))
            return True
        except FileNotFoundError:
            logger.warning("komut bulunamadi: %s", command)
            return False

    def switch_workspace(self, index):
        self._suppress_enter_until = time.monotonic() + 0.2
        result = self.workspaces.switch_to(index)
        if not result:
            return
        prev_idx, new_idx = result
        for wid in self.workspaces.get(prev_idx).window_ids:
            managed = self.windows.get(wid)
            if managed and not managed.floating:
                try:
                    managed.window.unmap()
                except error.BadWindow:
                    pass
        self._relayout(new_idx)
        for wid in self.workspaces.get(new_idx).window_ids:
            managed = self.windows.get(wid)
            if managed:
                try:
                    managed.window.map()
                except error.BadWindow:
                    pass
        self.ewmh.set_current_desktop(new_idx)

    def move_focused_to_workspace(self, index):
        if not self.focused_window_id:
            return
        wid = self.focused_window_id
        managed = self.windows[wid]
        from_ws = self.workspaces.find_workspace_of(wid)
        to_ws = self.workspaces.get(index)
        if not to_ws or to_ws is from_ws:
            return
        self.workspaces.move_window(wid, from_ws, to_ws)
        managed.workspace = index
        self.ewmh.set_wm_desktop(managed.window, index)
        try:
            managed.window.unmap()
        except error.BadWindow:
            pass
        self._relayout(from_ws.index)

    def reload_config(self):
        from qwm.config.loader import load_config
        try:
            new_config, _ = load_config(self.config_path)
        except Exception:
            logger.exception("config yeniden yuklenemedi")
            return

        self.config = new_config
        self.decorations = DecorationConfig.from_config(new_config["general"], new_config["colors"])
        self.keybinds.grab_all(new_config["keybinds"])
        self.animator_enabled["enabled"] = new_config["animations"].get("enabled", True)

        self.compositor.generate_config(new_config["compositor"], new_config["animations"])
        self.compositor.reload()

        for managed in self.windows.values():
            managed.border_width = self.decorations.border_width
            try:
                managed.window.configure(border_width=managed.border_width)
            except error.BadWindow:
                pass
            self._set_border_color(managed)

        self._relayout(self.workspaces.current_index)
        logger.info("config yeniden yuklendi")

    def _event_loop(self):
        fd = self.display.fileno()
        while self._running:
            try:
                readable, _, _ = select.select([fd], [], [], 0.05)
            except (OSError, ValueError):
                break

            if readable:
                while self.display.pending_events():
                    try:
                        event = self.display.next_event()
                    except Exception:
                        logger.exception("event okuma hatasi")
                        continue
                    try:
                        self.dispatcher.dispatch(event)
                    except Exception:
                        logger.exception("event isleme hatasi: %s", event)

            self._drain_commands()

        self.stop()

    def _drain_commands(self):
        while True:
            try:
                cmd = self.command_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_ipc_command(cmd)
            except Exception:
                logger.exception("ipc komutu basarisiz: %s", cmd)

    def _handle_ipc_command(self, cmd):
        parts = cmd.get("args", [])
        name = cmd.get("cmd")
        if name == "reload":
            self.reload_config()
        elif name == "restart":
            self._running = False
        elif name == "kill-focused":
            self.action_close_window()
        elif name == "workspace" and parts:
            self.switch_workspace(int(parts[0]) - 1)
        elif name == "layout" and parts:
            ws = self.workspaces.current()
            ws.layout = parts[0]
            self._relayout(ws.index)
        result_queue = cmd.get("result_queue")
        if result_queue:
            result_queue.put("ok")

    def submit_ipc_command(self, cmd):
        self.command_queue.put(cmd)
