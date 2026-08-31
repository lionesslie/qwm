"""QWM cekirdek pencere yoneticisi - saf Xlib ile yazilmistir."""
import importlib
import os
import signal
import sys

from Xlib import X, XK, Xatom, display, error
from Xlib.protocol import event as Xevent

from qwm import actions


class Workspace:
    def __init__(self, index, master_ratio):
        self.index = index
        self.windows = []
        self.floating = []
        self.focused = None
        self.master_ratio = master_ratio


class WM:
    MOD_MASKS = {
        "super": X.Mod4Mask, "alt": X.Mod1Mask,
        "ctrl": X.ControlMask, "control": X.ControlMask,
        "shift": X.ShiftMask,
    }

    def __init__(self, config_module):
        self.config = config_module
        self.display = display.Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.screen_w = self.screen.width_in_pixels
        self.screen_h = self.screen.height_in_pixels

        self._atom_cache = {}
        self.managed = {}
        self.pending_unmaps = set()
        self.drag = None
        self.running = False
        self._wm_detected = False

        # Onemli: hata isleyiciyi baglamayi baglamadan ONCE ayarla,
        # cunku change_attributes asenkron bir istektir; hata gec gelir.
        self.display.set_error_handler(self._error_handler)

        self.mod_mask = self.MOD_MASKS.get(getattr(config_module, "MOD_KEY", "super"), X.Mod4Mask)
        self.workspaces = [
            Workspace(i, getattr(config_module, "MASTER_RATIO", 0.55))
            for i in range(getattr(config_module, "WORKSPACE_COUNT", 9))
        ]
        self.current_ws = 0

        self._become_wm()
        self.numlock_mask = self._get_numlock_mask()
        self.setup_colors()
        self.setup_ewmh()
        self.grab_keys()
        self.grab_buttons()

        self.handlers = {
            X.MapRequest: self.on_map_request,
            X.UnmapNotify: self.on_unmap_notify,
            X.DestroyNotify: self.on_destroy_notify,
            X.ConfigureRequest: self.on_configure_request,
            X.KeyPress: self.on_key_press,
            X.ButtonPress: self.on_button_press,
            X.MotionNotify: self.on_motion_notify,
            X.ButtonRelease: self.on_button_release,
            X.EnterNotify: self.on_enter_notify,
            X.ClientMessage: self.on_client_message,
        }

        signal.signal(signal.SIGCHLD, self._reap_children)
        signal.signal(signal.SIGTERM, lambda *_: self.quit())
        signal.signal(signal.SIGINT, lambda *_: self.quit())

    # ------------------------------------------------------------------
    # KURULUM
    # ------------------------------------------------------------------
    def _error_handler(self, err, request=None):
        # X hatalari asenkrondur; burada crash etmek yerine loglayip devam ederiz.
        if isinstance(err, error.BadAccess):
            self._wm_detected = True
        print(f"[QWM] X hatasi yakalandi (yok sayildi): {err}")

    def _become_wm(self):
        self.root.change_attributes(
            event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self.display.sync()
        if self._wm_detected:
            sys.exit("[QWM] HATA: Ekranda baska bir pencere yoneticisi zaten calisiyor.")

    def _get_numlock_mask(self):
        modifier_masks = [X.ShiftMask, X.LockMask, X.ControlMask, X.Mod1Mask,
                           X.Mod2Mask, X.Mod3Mask, X.Mod4Mask, X.Mod5Mask]
        try:
            numlock_kc = self.display.keysym_to_keycode(XK.XK_Num_Lock)
            modmap = self.display.get_modifier_mapping()
            for i, codes in enumerate(modmap):
                if numlock_kc in codes:
                    return modifier_masks[i]
        except Exception:
            pass
        return X.Mod2Mask

    def setup_colors(self):
        self.focused_pixel = self._alloc_color(self.config.FOCUSED_BORDER_COLOR)
        self.unfocused_pixel = self._alloc_color(self.config.UNFOCUSED_BORDER_COLOR)

    def _alloc_color(self, hexstr):
        hexstr = hexstr.lstrip("#")
        r, g, b = (int(hexstr[i:i + 2], 16) * 257 for i in (0, 2, 4))
        return self.screen.default_colormap.alloc_color(r, g, b).pixel

    def setup_ewmh(self):
        names = ("_NET_SUPPORTED", "_NET_NUMBER_OF_DESKTOPS", "_NET_CURRENT_DESKTOP",
                  "_NET_ACTIVE_WINDOW", "_NET_WM_STATE", "_NET_WM_STATE_FULLSCREEN",
                  "_NET_WM_NAME", "_NET_SUPPORTING_WM_CHECK", "_NET_WM_WINDOW_TYPE",
                  "_NET_WM_WINDOW_TYPE_DIALOG")
        supported = [self.atom(n) for n in names]
        self.root.change_property(self.atom("_NET_SUPPORTED"), Xatom.ATOM, 32, supported)
        self.root.change_property(self.atom("_NET_NUMBER_OF_DESKTOPS"), Xatom.CARDINAL, 32,
                                   [len(self.workspaces)])
        self.set_net_current_desktop(0)

        check_win = self.root.create_window(-1, -1, 1, 1, 0, self.screen.root_depth)
        check_win.change_property(self.atom("_NET_WM_NAME"), self.atom("UTF8_STRING"), 8, b"QWM")
        check_win.change_property(self.atom("_NET_SUPPORTING_WM_CHECK"), Xatom.WINDOW, 32,
                                   [check_win.id])
        self.root.change_property(self.atom("_NET_SUPPORTING_WM_CHECK"), Xatom.WINDOW, 32,
                                   [check_win.id])

    def grab_keys(self):
        self.root.ungrab_key(X.AnyKey, X.AnyModifier)
        self.keymap = {}
        for keystr, act in self.config.KEYBINDINGS.items():
            modmask, keysym = self._parse_keystring(keystr)
            keycode = self.display.keysym_to_keycode(keysym)
            if keycode == 0:
                print(f"[QWM] UYARI: '{keystr}' taninmadi, atlaniyor.")
                continue
            self.keymap[(keycode, modmask)] = act
            for extra in (0, X.LockMask, self.numlock_mask, X.LockMask | self.numlock_mask):
                self.root.grab_key(keycode, modmask | extra, True,
                                    X.GrabModeAsync, X.GrabModeAsync)

    def _parse_keystring(self, keystr):
        parts = keystr.split("-")
        keyname, mods = parts[-1], parts[:-1]
        modmask = 0
        for m in mods:
            modmask |= self.MOD_MASKS.get(m.lower(), 0)
        keysym = XK.string_to_keysym(keyname)
        return modmask, keysym

    def grab_buttons(self):
        for button in (1, 3):
            for extra in (0, X.LockMask, self.numlock_mask, X.LockMask | self.numlock_mask):
                self.root.grab_button(
                    button, self.mod_mask | extra, True,
                    X.ButtonPressMask | X.ButtonReleaseMask | X.PointerMotionMask,
                    X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE)

    def _reap_children(self, signum, frame):
        try:
            while True:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
        except ChildProcessError:
            pass

    # ------------------------------------------------------------------
    # YARDIMCI
    # ------------------------------------------------------------------
    def atom(self, name):
        if name not in self._atom_cache:
            self._atom_cache[name] = self.display.intern_atom(name)
        return self._atom_cache[name]

    def current_workspace(self):
        return self.workspaces[self.current_ws]

    def get_focused(self):
        return self.current_workspace().focused

    def supports_protocol(self, win, proto_name):
        try:
            protocols = win.get_wm_protocols()
        except Exception:
            return False
        return self.atom(proto_name) in protocols

    def send_client_message(self, win, msgtype_name, data):
        data = (list(data) + [0] * 5)[:5]
        ev = Xevent.ClientMessage(window=win, client_type=self.atom(msgtype_name), data=(32, data))
        try:
            win.send_event(ev, event_mask=X.NoEventMask)
        except Exception:
            pass

    def set_net_current_desktop(self, idx):
        self.root.change_property(self.atom("_NET_CURRENT_DESKTOP"), Xatom.CARDINAL, 32, [idx])

    def set_net_active_window(self, win):
        try:
            self.root.change_property(self.atom("_NET_ACTIVE_WINDOW"), Xatom.WINDOW, 32, [win.id])
        except Exception:
            pass

    def should_float(self, win):
        try:
            hints = win.get_wm_normal_hints()
            if hints and hints.min_width and hints.min_width == hints.max_width \
                    and hints.min_height == hints.max_height:
                return True
        except Exception:
            pass
        try:
            if win.get_wm_transient_for():
                return True
        except Exception:
            pass
        try:
            wtype = win.get_full_property(self.atom("_NET_WM_WINDOW_TYPE"), X.AnyPropertyType)
            if wtype and self.atom("_NET_WM_WINDOW_TYPE_DIALOG") in wtype.value:
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # PENCERE YONETIMI
    # ------------------------------------------------------------------
    def manage_window(self, win):
        if win.id in self.managed:
            return
        try:
            attrs = win.get_attributes()
        except Exception:
            return
        if attrs.override_redirect:
            return

        try:
            win.change_attributes(event_mask=(X.EnterWindowMask | X.FocusChangeMask |
                                               X.PropertyChangeMask | X.StructureNotifyMask))
            win.configure(border_width=self.config.BORDER_WIDTH)
        except Exception:
            return

        is_float = self.should_float(win)
        ws = self.current_workspace()
        self.managed[win.id] = {"window": win, "workspace": self.current_ws,
                                 "floating": is_float, "fullscreen": False}

        if is_float:
            ws.floating.append(win)
            try:
                geom = win.get_geometry()
                w = geom.width if geom.width > 50 else 400
                h = geom.height if geom.height > 50 else 300
            except Exception:
                w, h = 400, 300
            win.configure(x=(self.screen_w - w) // 2, y=(self.screen_h - h) // 2, width=w, height=h)
        else:
            ws.windows.insert(0, win)

        try:
            win.map()
        except Exception:
            pass
        self.arrange()
        self.focus_window(win)
        self.display.sync()

    def unmanage_window(self, win_id):
        info = self.managed.pop(win_id, None)
        if not info:
            return
        ws = self.workspaces[info["workspace"]]
        for lst in (ws.windows, ws.floating):
            for w in list(lst):
                if w.id == win_id:
                    lst.remove(w)
        if ws.focused and ws.focused.id == win_id:
            ws.focused = None
        if info["workspace"] == self.current_ws:
            self.arrange()
            self.focus_first_available()

    def make_floating(self, win):
        info = self.managed.get(win.id)
        if not info or info["floating"]:
            return
        ws = self.workspaces[info["workspace"]]
        if win in ws.windows:
            ws.windows.remove(win)
        ws.floating.append(win)
        info["floating"] = True
        self.arrange()

    # ------------------------------------------------------------------
    # DOSEME (TILING) DUZENI
    # ------------------------------------------------------------------
    def arrange(self):
        ws = self.current_workspace()
        go, gi, bw = self.config.GAP_OUTER, self.config.GAP_INNER, self.config.BORDER_WIDTH
        tiled = [w for w in ws.windows if not self.managed.get(w.id, {}).get("fullscreen")]
        n = len(tiled)

        try:
            if n == 1:
                w = tiled[0]
                w.configure(x=go, y=go,
                            width=max(1, self.screen_w - 2 * go - 2 * bw),
                            height=max(1, self.screen_h - 2 * go - 2 * bw))
            elif n > 1:
                avail_w = self.screen_w - 2 * go - gi
                master_w = int(avail_w * ws.master_ratio)
                stack_w = avail_w - master_w

                master = tiled[0]
                master.configure(x=go, y=go,
                                  width=max(1, master_w - 2 * bw),
                                  height=max(1, self.screen_h - 2 * go - 2 * bw))

                stack = tiled[1:]
                count = len(stack)
                total_h = self.screen_h - 2 * go - gi * (count - 1)
                each_h = total_h // count
                y = go
                x = go + master_w + gi
                for i, w in enumerate(stack):
                    h = each_h if i < count - 1 else total_h - each_h * (count - 1)
                    w.configure(x=x, y=y, width=max(1, stack_w - 2 * bw), height=max(1, h - 2 * bw))
                    y += h + gi

            for w in ws.floating:
                w.configure(stack_mode=X.Above)
        except Exception as exc:
            print(f"[QWM] arrange() hatasi: {exc}")

        self.display.sync()

    # ------------------------------------------------------------------
    # ODAK (FOCUS)
    # ------------------------------------------------------------------
    def focus_window(self, win):
        ws = self.current_workspace()
        if ws.focused and ws.focused.id != win.id:
            try:
                ws.focused.change_attributes(border_pixel=self.unfocused_pixel)
            except Exception:
                pass
        ws.focused = win
        try:
            win.change_attributes(border_pixel=self.focused_pixel)
            win.configure(stack_mode=X.Above)
            self.display.set_input_focus(win, X.RevertToPointerRoot, X.CurrentTime)
            self.set_net_active_window(win)
        except Exception:
            pass
        self.display.sync()

    def focus_first_available(self):
        ws = self.current_workspace()
        candidates = ws.windows + ws.floating
        if candidates:
            self.focus_window(candidates[0])
        else:
            self.display.set_input_focus(self.root, X.RevertToPointerRoot, X.CurrentTime)

    def focus_cycle(self, direction):
        ws = self.current_workspace()
        windows = ws.windows + ws.floating
        if not windows:
            return
        ids = [w.id for w in windows]
        if ws.focused and ws.focused.id in ids:
            idx = ids.index(ws.focused.id)
            nxt = windows[(idx + direction) % len(windows)]
        else:
            nxt = windows[0]
        self.focus_window(nxt)

    # ------------------------------------------------------------------
    # EYLEMLER
    # ------------------------------------------------------------------
    def toggle_fullscreen(self, window=None):
        win = window or self.get_focused()
        if not win:
            return
        info = self.managed.get(win.id)
        if not info:
            return
        try:
            if info.get("fullscreen"):
                geom = info.pop("saved_geom")
                win.configure(x=geom.x, y=geom.y, width=geom.width, height=geom.height,
                              border_width=self.config.BORDER_WIDTH)
                info["fullscreen"] = False
                self.arrange()
            else:
                info["saved_geom"] = win.get_geometry()
                info["fullscreen"] = True
                win.configure(x=0, y=0, width=self.screen_w, height=self.screen_h,
                              border_width=0, stack_mode=X.Above)
        except Exception as exc:
            print(f"[QWM] toggle_fullscreen hatasi: {exc}")
        self.display.sync()

    def toggle_floating_focused(self):
        win = self.get_focused()
        if not win:
            return
        info = self.managed.get(win.id)
        if not info:
            return
        ws = self.workspaces[info["workspace"]]
        if info["floating"]:
            ws.floating.remove(win)
            ws.windows.append(win)
            info["floating"] = False
        else:
            ws.windows.remove(win)
            ws.floating.append(win)
            info["floating"] = True
            w, h = int(self.screen_w * 0.5), int(self.screen_h * 0.5)
            try:
                win.configure(x=(self.screen_w - w) // 2, y=(self.screen_h - h) // 2, width=w, height=h)
            except Exception:
                pass
        self.arrange()

    def swap_with_master(self):
        ws = self.current_workspace()
        win = ws.focused
        if not win or win not in ws.windows or len(ws.windows) < 2:
            return
        idx = ws.windows.index(win)
        ws.windows[0], ws.windows[idx] = ws.windows[idx], ws.windows[0]
        self.arrange()

    def switch_workspace(self, idx):
        if idx == self.current_ws or not (0 <= idx < len(self.workspaces)):
            return
        old_ws = self.workspaces[self.current_ws]
        for win in old_ws.windows + old_ws.floating:
            self.pending_unmaps.add(win.id)
            try:
                win.unmap()
            except Exception:
                pass

        self.current_ws = idx
        new_ws = self.workspaces[idx]
        for win in new_ws.windows + new_ws.floating:
            try:
                win.map()
            except Exception:
                pass

        self.set_net_current_desktop(idx)
        self.arrange()
        if new_ws.focused:
            self.focus_window(new_ws.focused)
        elif new_ws.windows:
            self.focus_window(new_ws.windows[0])
        self.display.sync()

    def move_focused_to_workspace(self, idx):
        win = self.get_focused()
        if not win or idx == self.current_ws or not (0 <= idx < len(self.workspaces)):
            return
        info = self.managed.get(win.id)
        if not info:
            return
        old_ws = self.workspaces[self.current_ws]
        lst = old_ws.floating if info["floating"] else old_ws.windows
        if win in lst:
            lst.remove(win)
        if old_ws.focused and old_ws.focused.id == win.id:
            old_ws.focused = None

        new_ws = self.workspaces[idx]
        (new_ws.floating if info["floating"] else new_ws.windows).append(win)
        info["workspace"] = idx

        self.pending_unmaps.add(win.id)
        try:
            win.unmap()
        except Exception:
            pass
        self.arrange()
        self.focus_first_available()

    def quit(self):
        self.running = False

    def reload_config(self):
        try:
            importlib.reload(self.config)
            self.grab_keys()
            self.setup_colors()
            self.arrange()
            print("[QWM] Yapilandirma yeniden yuklendi.")
        except Exception as exc:
            print(f"[QWM] Config yeniden yuklenemedi: {exc}")

    # ------------------------------------------------------------------
    # OLAY (EVENT) ISLEYICILERI
    # ------------------------------------------------------------------
    def on_map_request(self, event):
        self.manage_window(event.window)

    def on_unmap_notify(self, event):
        win_id = event.window.id
        if win_id in self.pending_unmaps:
            self.pending_unmaps.discard(win_id)
            return
        self.unmanage_window(win_id)

    def on_destroy_notify(self, event):
        try:
            self.unmanage_window(event.window.id)
        except Exception:
            pass

    def on_configure_request(self, event):
        win = event.window
        mask = event.value_mask
        changes = {}
        if mask & X.CWX: changes["x"] = event.x
        if mask & X.CWY: changes["y"] = event.y
        if mask & X.CWWidth: changes["width"] = event.width
        if mask & X.CWHeight: changes["height"] = event.height
        if mask & X.CWBorderWidth: changes["border_width"] = event.border_width
        if mask & X.CWStackMode: changes["stack_mode"] = event.stack_mode

        info = self.managed.get(win.id)
        if not info or info.get("floating") or info.get("fullscreen"):
            if changes:
                try:
                    win.configure(**changes)
                except Exception:
                    pass
        self.display.sync()

    def on_key_press(self, event):
        state = event.state & ~(X.LockMask | self.numlock_mask)
        act = self.keymap.get((event.detail, state))
        if not act:
            return
        name, arg = act
        fn = actions.ACTIONS.get(name)
        if fn:
            try:
                fn(self, arg)
            except Exception as exc:
                print(f"[QWM] Eylem hatasi '{name}': {exc}")

    def on_button_press(self, event):
        win = event.child
        if win is None or win.id == 0 or win.id == self.root.id:
            return
        try:
            geom = win.get_geometry()
        except Exception:
            return
        self.drag = {"window": win, "button": event.detail,
                     "start_x": event.root_x, "start_y": event.root_y, "geom": geom}
        try:
            win.configure(stack_mode=X.Above)
        except Exception:
            pass
        self.focus_window(win)

    def on_motion_notify(self, event):
        if not self.drag:
            return
        # Kuyruktaki fazla hareket olaylarini atlayarak sursutulmeyi azalt
        while self.display.pending_events() > 0:
            nxt = self.display.next_event()
            if nxt.type == X.MotionNotify:
                event = nxt
            else:
                handler = self.handlers.get(nxt.type)
                if handler:
                    try:
                        handler(nxt)
                    except Exception:
                        pass
                break

        dx = event.root_x - self.drag["start_x"]
        dy = event.root_y - self.drag["start_y"]
        win, geom = self.drag["window"], self.drag["geom"]

        self.make_floating(win)

        try:
            if self.drag["button"] == 1:
                win.configure(x=geom.x + dx, y=geom.y + dy)
            else:
                win.configure(width=max(50, geom.width + dx), height=max(50, geom.height + dy))
            self.display.sync()
        except Exception:
            self.drag = None

    def on_button_release(self, event):
        self.drag = None

    def on_enter_notify(self, event):
        if not getattr(self.config, "FOCUS_FOLLOWS_MOUSE", True) or self.drag:
            return
        win = event.window
        if win.id in self.managed:
            self.focus_window(win)

    def on_client_message(self, event):
        if event.message_type == self.atom("_NET_WM_STATE"):
            fmt, values = event.data
            prop1, prop2 = values[1], values[2]
            if self.atom("_NET_WM_STATE_FULLSCREEN") in (prop1, prop2):
                self.toggle_fullscreen(window=event.window)

    # ------------------------------------------------------------------
    # ANA DONGU
    # ------------------------------------------------------------------
    def run(self):
        self.running = True
        print("[QWM] Pencere yoneticisi calisiyor. Cikis: Super+Shift+Q")
        while self.running:
            try:
                event = self.display.next_event()
            except Exception as exc:
                print(f"[QWM] Olay okuma hatasi: {exc}")
                continue
            handler = self.handlers.get(event.type)
            if not handler:
                continue
            try:
                handler(event)
            except Exception as exc:
                print(f"[QWM] Olay islenirken hata: {exc}")
        self.display.close()