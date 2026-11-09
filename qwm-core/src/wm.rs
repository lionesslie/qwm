//! Ana WM state makinesi ve olay dongusu.
//!
//! Bu surumde: multi-monitor (RandR) + monitor basina dinamik workspace
//! yonetimi, floating window rules (class/instance/title regex), basit
//! scratchpad, monocle/fullscreen, yon bazli focus/swap (pencere
//! merkezlerine gore) ve gercek `XGrabKey` tabanli keybinding sistemi
//! calisir durumda. Kalan bosluklar: preselect, mouse move/resize, tam
//! multi-monitor EWMH viewport semantigi (bkz. README yol haritasi).

use crate::bar::BarState;
use crate::config::{self, schema::Rule, Config};
use crate::ipc::protocol::Response;
use crate::keybind::{self, Action, MouseAction};
use crate::layout::bsp_tree::SplitDir;
use crate::layout::geometry::{layout, Rect};
use crate::monitor::{self, Monitor};
use crate::rules::{self, CompiledRule};
use crate::scratchpad::ScratchpadState;
use crate::window::Client;
use crate::workspace::{Layout, Workspace};
use crate::x11::atoms::Atoms;
use crate::x11::connection::XConn;
use anyhow::Result;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::mpsc::{Receiver, Sender};
use std::time::Duration;
use x11rb::connection::Connection;
use x11rb::protocol::xproto::*;
use x11rb::protocol::Event;

/// Tek bir fiziksel monitor: geometrisi + kendi workspace seti + o anki
/// aktif workspace index'i.
pub struct MonitorState {
    pub monitor: Monitor,
    pub workspaces: Vec<Workspace>,
    pub active: usize,
}

pub struct Wm {
    pub xc: XConn,
    pub atoms: Atoms,
    pub config: Config,
    pub config_path: PathBuf,
    pub clients: HashMap<Window, Client>,
    pub monitors: Vec<MonitorState>,
    pub active_monitor: usize,
    pub focused: Option<Window>,
    pub running: bool,
    pub rules: Vec<CompiledRule>,
    pub scratchpad: ScratchpadState,
    /// match_class -> scratchpad adi. Scratchpad komutu calistirildiktan
    /// sonra, ilgili class'la map olan ilk pencere bu isimdeki slota baglanir.
    pub pending_scratchpad: HashMap<String, String>,
    /// (keycode, modifier_bits) -> Action. `grab_keys()` tarafindan doldurulur.
    pub key_bindings: HashMap<(u8, u16), Action>,
    /// `_NET_WM_WINDOW_TYPE_DOCK` olarak map edilen pencereler (polybar,
    /// waybar vb.). Tiling'e dahil edilmez, yalnizca strut hesabinda kullanilir.
    pub docks: HashSet<Window>,
    /// Her dock penceresinin `_NET_WM_STRUT_PARTIAL`/`_NET_WM_STRUT`'tan
    /// okunan alan rezervasyonu. Dahili bar aktifse kendi penceresi de
    /// (ayni mekanizmayi kullanarak) burada bir girdi tutar.
    pub struts: HashMap<Window, Strut>,
    /// (button, modifier_bits) -> MouseAction. `grab_buttons()` tarafindan doldurulur.
    pub mouse_bindings: HashMap<(u8, u16), MouseAction>,
    /// Devam eden bir mouse move/resize suruklemesi, varsa.
    pub drag: Option<DragState>,
    pub bar: Option<BarState>,
}

#[derive(Debug, Clone, Copy)]
pub struct DragState {
    window: Window,
    mode: MouseAction,
    start_root_x: i16,
    start_root_y: i16,
    start_x: i32,
    start_y: i32,
    start_w: u32,
    start_h: u32,
    /// Surukleme basladiginda pencere tiled miydi (true ise `Move` aninda
    /// floating'e cikarilir, `Resize` ise split oranini degistirir).
    tiled: bool,
}

/// `_NET_WM_STRUT_PARTIAL`'in basitlestirilmis (yalnizca dort kenar)
/// karsiligi. Tam spesifikasyondaki start/end araliklari (ör. bir barin
/// yalnizca ekranin bir kismini kaplamasi) su an icin dikkate alinmiyor.
#[derive(Debug, Clone, Copy, Default)]
pub struct Strut {
    pub left: i32,
    pub right: i32,
    pub top: i32,
    pub bottom: i32,
}

#[derive(Debug, Clone, Copy, Default)]
struct SizeHints {
    min_w: Option<u32>,
    min_h: Option<u32>,
}

impl Wm {
    pub fn new(xc: XConn, config: Config, config_path: PathBuf) -> Result<Self> {
        let atoms = Atoms::new(&xc.conn)?.reply()?;
        let root = xc.root();
        let split_ratio = config.general.split_ratio;

        let detected = monitor::query_monitors(&xc.conn, root)?;
        let monitors = detected
            .into_iter()
            .map(|m| {
                let workspaces = if config.workspaces.mode == "static" {
                    (0..config.workspaces.static_count.max(1))
                        .map(|i| {
                            let name = config.workspaces.names.get(i as usize).cloned();
                            Workspace::new(i as usize + 1, name, split_ratio)
                        })
                        .collect()
                } else {
                    vec![Workspace::new(
                        1,
                        config.workspaces.names.first().cloned(),
                        split_ratio,
                    )]
                };
                MonitorState {
                    monitor: m,
                    workspaces,
                    active: 0,
                }
            })
            .collect();

        let rules = rules::compile_rules(&config.rules);

        Ok(Self {
            xc,
            atoms,
            config,
            config_path,
            clients: HashMap::new(),
            monitors,
            active_monitor: 0,
            focused: None,
            running: true,
            rules,
            scratchpad: ScratchpadState::default(),
            pending_scratchpad: HashMap::new(),
            key_bindings: HashMap::new(),
            docks: HashSet::new(),
            struts: HashMap::new(),
            mouse_bindings: HashMap::new(),
            drag: None,
            bar: None,
        })
    }

    /// EWMH icin gerekli kok pencere ozelliklerini ilan eder ve config'deki
    /// keybinding'leri `XGrabKey` ile baglar.
    pub fn init_ewmh(&mut self) -> Result<()> {
        let root = self.xc.root();
        let conn = &self.xc.conn;

        let check_win = conn.generate_id()?;
        conn.create_window(
            x11rb::COPY_DEPTH_FROM_PARENT,
            check_win,
            root,
            -1,
            -1,
            1,
            1,
            0,
            WindowClass::INPUT_ONLY,
            0,
            &CreateWindowAux::default(),
        )?;

        let supported = [
            self.atoms._NET_SUPPORTED,
            self.atoms._NET_CLIENT_LIST,
            self.atoms._NET_CLIENT_LIST_STACKING,
            self.atoms._NET_NUMBER_OF_DESKTOPS,
            self.atoms._NET_DESKTOP_NAMES,
            self.atoms._NET_CURRENT_DESKTOP,
            self.atoms._NET_ACTIVE_WINDOW,
            self.atoms._NET_WORKAREA,
            self.atoms._NET_SUPPORTING_WM_CHECK,
            self.atoms._NET_WM_STATE,
            self.atoms._NET_WM_STATE_FULLSCREEN,
            self.atoms._NET_WM_WINDOW_TYPE,
            self.atoms._NET_WM_STRUT,
            self.atoms._NET_WM_STRUT_PARTIAL,
        ];
        conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_SUPPORTED,
            AtomEnum::ATOM,
            &supported,
        )?;
        conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_SUPPORTING_WM_CHECK,
            AtomEnum::WINDOW,
            &[check_win],
        )?;
        conn.change_property32(
            PropMode::REPLACE,
            check_win,
            self.atoms._NET_SUPPORTING_WM_CHECK,
            AtomEnum::WINDOW,
            &[check_win],
        )?;
        conn.change_property8(
            PropMode::REPLACE,
            check_win,
            self.atoms._NET_WM_NAME,
            self.atoms.UTF8_STRING,
            b"qwm",
        )?;
        conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_CLIENT_LIST,
            AtomEnum::WINDOW,
            &[] as &[u32],
        )?;
        conn.flush()?;

        self.grab_keys()?;
        self.grab_buttons()?;

        if self.config.bar.enabled && !self.monitors.is_empty() {
            let m = self.monitors[0].monitor.clone();
            match BarState::create(&self.xc.conn, root, 0, &m, &self.config.bar) {
                Ok(bar) => {
                    self.struts.insert(bar.window, Self::bar_strut(&bar));
                    self.bar = Some(bar);
                }
                Err(err) => tracing::warn!("dahili bar olusturulamadi: {err:#}"),
            }
        }

        self.sync_ewmh()?;
        self.relayout_all()?;
        Ok(())
    }

    fn bar_strut(bar: &BarState) -> Strut {
        Strut {
            left: 0,
            right: 0,
            top: if bar.position_top { bar.height as i32 } else { 0 },
            bottom: if bar.position_top { 0 } else { bar.height as i32 },
        }
    }

    /// Ana olay dongusu.
    pub fn run(&mut self, ipc_rx: Receiver<(Action, Sender<Response>)>) -> Result<()> {
        self.xc.conn.flush()?;
        while self.running {
            while let Some(event) = self.xc.conn.poll_for_event()? {
                if let Err(err) = self.handle_event(event) {
                    tracing::warn!("event isleme hatasi: {err:#}");
                }
            }
            if let Ok((action, resp_tx)) = ipc_rx.try_recv() {
                let resp = self.handle_action(action);
                let _ = resp_tx.send(resp);
            }
            self.xc.conn.flush()?;
            std::thread::sleep(Duration::from_millis(10));
        }
        Ok(())
    }

    fn handle_event(&mut self, event: Event) -> Result<()> {
        match event {
            Event::MapRequest(ev) => self.on_map_request(ev)?,
            Event::UnmapNotify(ev) => self.on_unmap(ev.window)?,
            Event::DestroyNotify(ev) => self.on_unmap(ev.window)?,
            Event::ConfigureRequest(ev) => self.on_configure_request(ev)?,
            Event::KeyPress(ev) => self.on_key_press(ev)?,
            Event::ClientMessage(ev) => self.on_client_message(ev)?,
            Event::PropertyNotify(ev) => self.on_property_notify(ev)?,
            Event::ButtonPress(ev) => self.on_button_press(ev)?,
            Event::ButtonRelease(_ev) => self.on_button_release()?,
            Event::MotionNotify(ev) => self.on_motion_notify(ev)?,
            Event::Expose(ev) => {
                if self.bar.as_ref().map(|b| b.window) == Some(ev.window) {
                    self.redraw_bar()?;
                }
            }
            Event::EnterNotify(ev) => {
                if self.config.general.focus_follows_mouse {
                    self.focus(ev.event)?;
                }
            }
            _ => {}
        }
        Ok(())
    }

    // --- Pencere map/unmap ---

    fn on_map_request(&mut self, ev: MapRequestEvent) -> Result<()> {
        let win = ev.window;

        // Dock pencereleri (polybar/waybar vb.) tiling disinda tutulur;
        // yalnizca strut'lari okunup workarea'ya yansitilir.
        if self.is_dock(win) {
            self.docks.insert(win);
            let aux = ChangeWindowAttributesAux::default().event_mask(EventMask::PROPERTY_CHANGE);
            self.xc.conn.change_window_attributes(win, &aux)?;
            if let Some(s) = self.read_strut(win) {
                self.struts.insert(win, s);
            }
            self.xc.conn.map_window(win)?;
            self.sync_ewmh()?;
            self.relayout_all()?;
            return Ok(());
        }

        let (class, instance) = self.read_wm_class(win).unwrap_or_default();
        let title = self.read_wm_title(win).unwrap_or_default();
        let hints = self.read_size_hints(win);

        if let Some(name) = self
            .pending_scratchpad
            .remove(&class)
            .or_else(|| self.pending_scratchpad.remove(&instance))
        {
            return self.setup_scratchpad_window(win, &name, class, instance, title);
        }

        let mon_idx = self.active_monitor;
        let rule: Option<Rule> = rules::find_match(&self.rules, &class, &instance, &title)
            .map(|r| r.raw.clone());

        let mut target_ws = self.monitors[mon_idx].active;
        if let Some(r) = &rule {
            if let Some(ws_name) = &r.workspace {
                if let Some(idx) = self.resolve_or_create_workspace(mon_idx, ws_name) {
                    target_ws = idx;
                }
            }
        }

        let mut client = Client::new(win, mon_idx, target_ws);
        client.class = class;
        client.instance = instance;
        client.title = title;
        client.min_width = hints.min_w;
        client.min_height = hints.min_h;

        // Rule'da floating=true verilmemis olsa bile WM_TRANSIENT_FOR
        // sahibi olan (dialog) ya da DIALOG/UTILITY/SPLASH tipindeki
        // pencereler ICCCM/EWMH geleneklerine uyarak otomatik floating acilir.
        let is_floating =
            rule.as_ref().map(|r| r.floating).unwrap_or(false) || self.should_float(win);
        if is_floating {
            client.floating = true;
            client.sticky = rule.as_ref().map(|r| r.sticky).unwrap_or(false);
            let m = self.monitors[mon_idx].monitor.clone();
            let w = rule
                .as_ref()
                .and_then(|r| r.width)
                .unwrap_or(m.width as u32 / 2)
                .max(hints.min_w.unwrap_or(0));
            let h = rule
                .as_ref()
                .and_then(|r| r.height)
                .unwrap_or(m.height as u32 / 2)
                .max(hints.min_h.unwrap_or(0));
            let center = rule.as_ref().map(|r| r.center).unwrap_or(true);
            let (x, y) = if center {
                (
                    m.x as i32 + (m.width as i32 - w as i32) / 2,
                    m.y as i32 + (m.height as i32 - h as i32) / 2,
                )
            } else {
                (m.x as i32, m.y as i32)
            };
            client.x = x;
            client.y = y;
            client.width = w;
            client.height = h;
            let aux = ConfigureWindowAux::default()
                .x(x)
                .y(y)
                .width(w)
                .height(h)
                .border_width(self.config.border.width as u32);
            self.xc.conn.configure_window(win, &aux)?;
        } else {
            let focus_target = if target_ws == self.monitors[mon_idx].active {
                self.focused
            } else {
                None
            };
            self.monitors[mon_idx].workspaces[target_ws]
                .tree
                .insert(win, focus_target, SplitDir::Vertical);
        }

        self.clients.insert(win, client);
        self.write_wm_state(win)?;

        if target_ws == self.monitors[mon_idx].active {
            self.xc.conn.map_window(win)?;
            if self.config.general.new_window_takes_focus {
                self.focused = Some(win);
            }
            self.relayout_monitor(mon_idx)?;
        }
        self.update_client_list()?;
        Ok(())
    }

    fn setup_scratchpad_window(
        &mut self,
        win: Window,
        name: &str,
        class: String,
        instance: String,
        title: String,
    ) -> Result<()> {
        let mon_idx = self.active_monitor;
        let m = self.monitors[mon_idx].monitor.clone();
        let cfg = self
            .config
            .scratchpads
            .iter()
            .find(|s| s.name == name)
            .cloned();
        let (wr, hr, center) = cfg.map(|c| (c.width, c.height, c.center)).unwrap_or((0.6, 0.5, true));
        let w = (m.width as f32 * wr) as u32;
        let h = (m.height as f32 * hr) as u32;
        let (x, y) = if center {
            (
                m.x as i32 + (m.width as i32 - w as i32) / 2,
                m.y as i32 + (m.height as i32 - h as i32) / 2,
            )
        } else {
            (m.x as i32, m.y as i32)
        };

        let mut client = Client::new(win, mon_idx, self.monitors[mon_idx].active);
        client.floating = true;
        client.scratchpad = Some(name.to_string());
        client.class = class;
        client.instance = instance;
        client.title = title;
        client.x = x;
        client.y = y;
        client.width = w;
        client.height = h;
        self.clients.insert(win, client);

        self.scratchpad.register(name, win);
        self.scratchpad.toggle(name); // kayittan hemen sonra gorunur yap

        let aux = ConfigureWindowAux::default()
            .x(x)
            .y(y)
            .width(w)
            .height(h)
            .border_width(self.config.border.width as u32)
            .stack_mode(StackMode::ABOVE);
        self.xc.conn.configure_window(win, &aux)?;
        self.xc.conn.map_window(win)?;
        self.focused = Some(win);
        self.update_client_list()?;
        Ok(())
    }

    fn on_unmap(&mut self, win: Window) -> Result<()> {
        if self.docks.remove(&win) {
            self.struts.remove(&win);
            self.sync_ewmh()?;
            self.relayout_all()?;
            return Ok(());
        }

        let Some(client) = self.clients.remove(&win) else {
            return Ok(());
        };
        if !client.floating {
            self.monitors[client.monitor].workspaces[client.workspace]
                .tree
                .remove(win);
        }
        if self.focused == Some(win) {
            self.focused = self.monitors[client.monitor].workspaces[client.workspace]
                .tree
                .windows()
                .first()
                .copied();
        }
        if client.monitor == self.active_monitor
            && client.workspace == self.monitors[client.monitor].active
        {
            self.relayout_monitor(client.monitor)?;
        }
        self.prune_empty_workspaces(client.monitor);
        self.update_client_list()?;
        Ok(())
    }

    fn on_configure_request(&mut self, ev: ConfigureRequestEvent) -> Result<()> {
        let aux = ConfigureWindowAux::from_configure_request(&ev);
        self.xc.conn.configure_window(ev.window, &aux)?;
        Ok(())
    }

    fn on_key_press(&mut self, ev: KeyPressEvent) -> Result<()> {
        // CapsLock durumunu yok sayan basit bir maskeleme; NumLock henuz
        // ele alinmiyor (bkz. README).
        let masked = ev.state & !(u16::from(ModMask::LOCK));
        if let Some(action) = self.key_bindings.get(&(ev.detail, masked)).cloned() {
            let _ = self.handle_action(action);
        }
        Ok(())
    }

    // --- Mouse move/resize ---

    fn on_button_press(&mut self, ev: ButtonPressEvent) -> Result<()> {
        let masked = ev.state & !(u16::from(ModMask::LOCK));
        let Some(&action) = self.mouse_bindings.get(&(ev.detail, masked)) else {
            return Ok(());
        };
        let win = ev.child;
        if win == x11rb::NONE || !self.clients.contains_key(&win) {
            return Ok(());
        }

        self.focus(win)?;

        if action == MouseAction::Focus {
            return Ok(());
        }

        // Tiled bir pencere Move ile surukleniyorsa once floating'e
        // cikarilir (yaygin WM davranisi); Resize ise tiled kalir ve
        // split oranini degistirir (bkz. on_motion_notify).
        let is_floating = self.clients.get(&win).map(|c| c.floating).unwrap_or(false);
        if action == MouseAction::Move && !is_floating {
            let mon_idx = self.clients.get(&win).map(|c| c.monitor).unwrap_or(self.active_monitor);
            let active = self.monitors[mon_idx].active;
            self.monitors[mon_idx].workspaces[active].tree.remove(win);
            if let Some(c) = self.clients.get_mut(&win) {
                c.floating = true;
            }
            self.relayout_monitor(mon_idx)?;
        }

        let Some(c) = self.clients.get(&win) else {
            return Ok(());
        };
        self.drag = Some(DragState {
            window: win,
            mode: action,
            start_root_x: ev.root_x,
            start_root_y: ev.root_y,
            start_x: c.x,
            start_y: c.y,
            start_w: c.width,
            start_h: c.height,
            tiled: !c.floating,
        });

        self.xc.conn.grab_pointer(
            false,
            self.xc.root(),
            EventMask::BUTTON_RELEASE | EventMask::POINTER_MOTION,
            GrabMode::ASYNC,
            GrabMode::ASYNC,
            x11rb::NONE,
            x11rb::NONE,
            x11rb::CURRENT_TIME,
        )?;
        self.xc.conn.flush()?;
        Ok(())
    }

    fn on_button_release(&mut self) -> Result<()> {
        if self.drag.take().is_some() {
            self.xc.conn.ungrab_pointer(x11rb::CURRENT_TIME)?;
            self.xc.conn.flush()?;
        }
        Ok(())
    }

    fn on_motion_notify(&mut self, ev: MotionNotifyEvent) -> Result<()> {
        let Some(drag) = self.drag else {
            return Ok(());
        };
        let dx = (ev.root_x - drag.start_root_x) as i32;
        let dy = (ev.root_y - drag.start_root_y) as i32;

        if drag.tiled {
            // Basit yaklasim: yatay surukleme, surukledigimiz pencereyi
            // tutan en yakin split dugumunun oranini degistirir. Split'in
            // yatay mi dikey mi oldugunu ayirt etmez (bkz. README).
            if dx != 0 {
                let mon_idx = self
                    .clients
                    .get(&drag.window)
                    .map(|c| c.monitor)
                    .unwrap_or(self.active_monitor);
                let mw = self.monitors[mon_idx].monitor.width.max(1) as f32;
                let delta = dx as f32 / mw;
                let active = self.monitors[mon_idx].active;
                self.monitors[mon_idx].workspaces[active].tree.resize(drag.window, delta);
                self.relayout_monitor(mon_idx)?;
                self.drag = Some(DragState {
                    start_root_x: ev.root_x,
                    ..drag
                });
            }
            return Ok(());
        }

        match drag.mode {
            MouseAction::Move => {
                let x = drag.start_x + dx;
                let y = drag.start_y + dy;
                let aux = ConfigureWindowAux::default().x(x).y(y);
                self.xc.conn.configure_window(drag.window, &aux)?;
                if let Some(c) = self.clients.get_mut(&drag.window) {
                    c.x = x;
                    c.y = y;
                }
            }
            MouseAction::Resize => {
                let w = (drag.start_w as i32 + dx).max(50) as u32;
                let h = (drag.start_h as i32 + dy).max(50) as u32;
                let aux = ConfigureWindowAux::default().width(w).height(h);
                self.xc.conn.configure_window(drag.window, &aux)?;
                if let Some(c) = self.clients.get_mut(&drag.window) {
                    c.width = w;
                    c.height = h;
                }
            }
            MouseAction::Focus => {}
        }
        self.xc.conn.flush()?;
        Ok(())
    }

    fn grab_buttons(&mut self) -> Result<()> {
        let root = self.xc.root();
        self.xc.conn.ungrab_button(ButtonIndex::ANY, root, ModMask::ANY)?;
        self.mouse_bindings.clear();

        for mb in self.config.mousebinds.clone() {
            let Some((mods, button)) = keybind::parse_mouse_keys(&mb.button) else {
                tracing::warn!("mousebind parse edilemedi: {}", mb.button);
                continue;
            };
            let Some(action) = keybind::mouse_action_from_str(&mb.action) else {
                tracing::warn!("mousebind aksiyonu taninmiyor: {} ({})", mb.button, mb.action);
                continue;
            };
            let Some(bidx) = button_index(button) else {
                tracing::warn!("desteklenmeyen buton: {}", mb.button);
                continue;
            };

            let mut bits: u16 = 0;
            if mods.mod_mask {
                bits |= u16::from(ModMask::M4);
            }
            if mods.shift {
                bits |= u16::from(ModMask::SHIFT);
            }
            if mods.ctrl {
                bits |= u16::from(ModMask::CONTROL);
            }
            if mods.alt {
                bits |= u16::from(ModMask::M1);
            }

            for extra in [0u16, u16::from(ModMask::LOCK)] {
                let combined = bits | extra;
                self.xc.conn.grab_button(
                    true,
                    root,
                    EventMask::BUTTON_PRESS,
                    GrabMode::ASYNC,
                    GrabMode::ASYNC,
                    x11rb::NONE,
                    x11rb::NONE,
                    bidx,
                    ModMask::from(combined),
                )?;
                self.mouse_bindings.insert((button, combined), action);
            }
        }
        self.xc.conn.flush()?;
        Ok(())
    }

    fn redraw_bar(&self) -> Result<()> {
        let Some(bar) = &self.bar else {
            return Ok(());
        };
        let mon = &self.monitors[bar.monitor_idx];
        let labels: Vec<(String, bool)> = mon
            .workspaces
            .iter()
            .enumerate()
            .map(|(i, ws)| (ws.name.clone().unwrap_or_else(|| (i + 1).to_string()), i == mon.active))
            .collect();
        let title = self
            .focused
            .and_then(|w| self.clients.get(&w))
            .map(|c| c.title.clone())
            .unwrap_or_default();
        bar.redraw(&self.xc.conn, &labels, &title)?;
        Ok(())
    }

    // --- Keybinding grab ---

    fn grab_keys(&mut self) -> Result<()> {
        let root = self.xc.root();
        self.xc.conn.ungrab_key(0u8, root, ModMask::ANY)?;
        self.key_bindings.clear();

        for kb in self.config.keybinds.clone() {
            let Some(parsed) = keybind::parse_keys(&kb.keys) else {
                tracing::warn!("keybinding parse edilemedi: {}", kb.keys);
                continue;
            };
            let Some(action) = keybind::action_from_keybind(&kb) else {
                tracing::warn!("keybinding aksiyonu taninmiyor: {} ({})", kb.keys, kb.action);
                continue;
            };
            let Some(keycode) = self.keysym_to_keycode(parsed.keysym) else {
                tracing::warn!("keysym icin keycode bulunamadi: {}", kb.keys);
                continue;
            };

            let mut bits: u16 = 0;
            if parsed.mods.mod_mask {
                bits |= u16::from(ModMask::M4); // Super genelde Mod4
            }
            if parsed.mods.shift {
                bits |= u16::from(ModMask::SHIFT);
            }
            if parsed.mods.ctrl {
                bits |= u16::from(ModMask::CONTROL);
            }
            if parsed.mods.alt {
                bits |= u16::from(ModMask::M1);
            }

            // CapsLock acik/kapaliyken de calissin diye iki kombinasyonu
            // da griple; NumLock varyanti eklenmedi (bkz. README).
            for extra in [0u16, u16::from(ModMask::LOCK)] {
                let combined = bits | extra;
                self.xc
                    .conn
                    .grab_key(true, root, ModMask::from(combined), keycode, GrabMode::ASYNC, GrabMode::ASYNC)?;
                self.key_bindings.insert((keycode, combined), action.clone());
            }
        }
        self.xc.conn.flush()?;
        Ok(())
    }

    fn keysym_to_keycode(&self, keysym: u32) -> Option<u8> {
        let setup = self.xc.conn.setup();
        let min_kc = setup.min_keycode;
        let max_kc = setup.max_keycode;
        let count = max_kc - min_kc + 1;
        let mapping = self
            .xc
            .conn
            .get_keyboard_mapping(min_kc, count)
            .ok()?
            .reply()
            .ok()?;
        let per = mapping.keysyms_per_keycode as usize;
        if per == 0 {
            return None;
        }
        for (i, chunk) in mapping.keysyms.chunks(per).enumerate() {
            if chunk.iter().any(|&ks| ks == keysym) {
                return Some(min_kc + i as u8);
            }
        }
        None
    }

    // --- ICCCM property okuma ---

    fn read_wm_class(&self, win: Window) -> Option<(String, String)> {
        let reply = self
            .xc
            .conn
            .get_property(false, win, AtomEnum::WM_CLASS, AtomEnum::STRING, 0, 1024)
            .ok()?
            .reply()
            .ok()?;
        let mut parts = reply.value.split(|&b| b == 0).filter(|s| !s.is_empty());
        let instance = parts
            .next()
            .map(|s| String::from_utf8_lossy(s).to_string())
            .unwrap_or_default();
        let class = parts
            .next()
            .map(|s| String::from_utf8_lossy(s).to_string())
            .unwrap_or_default();
        Some((class, instance))
    }

    fn read_wm_title(&self, win: Window) -> Option<String> {
        if let Ok(cookie) =
            self.xc
                .conn
                .get_property(false, win, self.atoms._NET_WM_NAME, self.atoms.UTF8_STRING, 0, 1024)
        {
            if let Ok(reply) = cookie.reply() {
                if !reply.value.is_empty() {
                    return Some(String::from_utf8_lossy(&reply.value).to_string());
                }
            }
        }
        let reply = self
            .xc
            .conn
            .get_property(false, win, AtomEnum::WM_NAME, AtomEnum::STRING, 0, 1024)
            .ok()?
            .reply()
            .ok()?;
        Some(String::from_utf8_lossy(&reply.value).to_string())
    }

    fn read_window_type(&self, win: Window) -> Vec<u32> {
        self.xc
            .conn
            .get_property(false, win, self.atoms._NET_WM_WINDOW_TYPE, AtomEnum::ATOM, 0, 12)
            .ok()
            .and_then(|c| c.reply().ok())
            .and_then(|r| r.value32().map(|it| it.collect()))
            .unwrap_or_default()
    }

    fn is_dock(&self, win: Window) -> bool {
        self.read_window_type(win)
            .contains(&self.atoms._NET_WM_WINDOW_TYPE_DOCK)
    }

    fn read_transient_for(&self, win: Window) -> Option<Window> {
        let reply = self
            .xc
            .conn
            .get_property(false, win, AtomEnum::WM_TRANSIENT_FOR, AtomEnum::WINDOW, 0, 1)
            .ok()?
            .reply()
            .ok()?;
        reply.value32()?.next()
    }

    /// `WM_TRANSIENT_FOR` sahibi olan (dialog) ya da `_NET_WM_WINDOW_TYPE`
    /// DIALOG/UTILITY/SPLASH olan pencereler ICCCM/EWMH geleneklerine
    /// uyarak otomatik floating acilmali.
    fn should_float(&self, win: Window) -> bool {
        if self.read_transient_for(win).is_some() {
            return true;
        }
        let wtype = self.read_window_type(win);
        [
            self.atoms._NET_WM_WINDOW_TYPE_DIALOG,
            self.atoms._NET_WM_WINDOW_TYPE_UTILITY,
            self.atoms._NET_WM_WINDOW_TYPE_SPLASH,
        ]
        .iter()
        .any(|t| wtype.contains(t))
    }

    /// `_NET_WM_STRUT_PARTIAL`'i tercih eder, yoksa eski `_NET_WM_STRUT`'a
    /// duser (bkz. EWMH spesifikasyonu: ikisi de ayni 4 temel rezervasyonu
    /// tasir, `_PARTIAL` ayrica start/end araliklari ekler).
    fn read_strut(&self, win: Window) -> Option<Strut> {
        if let Ok(cookie) =
            self.xc
                .conn
                .get_property(false, win, self.atoms._NET_WM_STRUT_PARTIAL, AtomEnum::CARDINAL, 0, 12)
        {
            if let Ok(reply) = cookie.reply() {
                if let Some(vals) = reply.value32() {
                    let vals: Vec<u32> = vals.collect();
                    if vals.len() >= 4 {
                        return Some(Strut {
                            left: vals[0] as i32,
                            right: vals[1] as i32,
                            top: vals[2] as i32,
                            bottom: vals[3] as i32,
                        });
                    }
                }
            }
        }
        let reply = self
            .xc
            .conn
            .get_property(false, win, self.atoms._NET_WM_STRUT, AtomEnum::CARDINAL, 0, 4)
            .ok()?
            .reply()
            .ok()?;
        let vals: Vec<u32> = reply.value32()?.collect();
        if vals.len() >= 4 {
            Some(Strut {
                left: vals[0] as i32,
                right: vals[1] as i32,
                top: vals[2] as i32,
                bottom: vals[3] as i32,
            })
        } else {
            None
        }
    }

    /// `WM_NORMAL_HINTS`'ten yalnizca minimum boyutu (ICCCM `PMinSize`
    /// bayragi, flags & 0x10) okur; max boyut/aspect/increment su an icin
    /// kullanilmiyor.
    fn read_size_hints(&self, win: Window) -> SizeHints {
        let mut hints = SizeHints::default();
        if let Ok(cookie) =
            self.xc
                .conn
                .get_property(false, win, AtomEnum::WM_NORMAL_HINTS, AtomEnum::WM_SIZE_HINTS, 0, 18)
        {
            if let Ok(reply) = cookie.reply() {
                if let Some(it) = reply.value32() {
                    let vals: Vec<u32> = it.collect();
                    if vals.len() >= 7 && (vals[0] & 0x10) != 0 {
                        hints.min_w = Some(vals[5]);
                        hints.min_h = Some(vals[6]);
                    }
                }
            }
        }
        hints
    }

    fn total_struts(&self) -> Strut {
        let mut total = Strut::default();
        for s in self.struts.values() {
            total.left += s.left;
            total.right += s.right;
            total.top += s.top;
            total.bottom += s.bottom;
        }
        total
    }

    fn write_wm_state(&self, win: Window) -> Result<()> {
        let mut states = Vec::new();
        if let Some(c) = self.clients.get(&win) {
            if c.fullscreen {
                states.push(self.atoms._NET_WM_STATE_FULLSCREEN);
            }
            if c.sticky {
                states.push(self.atoms._NET_WM_STATE_STICKY);
            }
            if c.urgent {
                states.push(self.atoms._NET_WM_STATE_DEMANDS_ATTENTION);
            }
        }
        self.xc
            .conn
            .change_property32(PropMode::REPLACE, win, self.atoms._NET_WM_STATE, AtomEnum::ATOM, &states)?;
        Ok(())
    }

    /// Bir istemcinin kendi `_NET_WM_STATE` isteklerini (ör. bir video
    /// oynaticinin kendi kendini fullscreen yapmasi) EWMH client-message
    /// protokolune gore isler: `data[0]` 0=kaldir, 1=ekle, 2=toggle.
    fn on_client_message(&mut self, ev: ClientMessageEvent) -> Result<()> {
        if ev.type_ != self.atoms._NET_WM_STATE {
            return Ok(());
        }
        let data = ev.data.as_data32();
        let action = data[0];
        let win = ev.window;
        let mut changed = false;
        for atom in [data[1], data[2]] {
            if atom == self.atoms._NET_WM_STATE_FULLSCREEN {
                if let Some(c) = self.clients.get_mut(&win) {
                    c.fullscreen = match action {
                        0 => false,
                        1 => true,
                        _ => !c.fullscreen,
                    };
                    changed = true;
                }
            }
        }
        if changed {
            self.write_wm_state(win)?;
            if let Some(mon_idx) = self.clients.get(&win).map(|c| c.monitor) {
                self.relayout_monitor(mon_idx)?;
            }
        }
        Ok(())
    }

    /// Dock pencerelerinin strut'u degistiginde (ör. polybar yeniden
    /// boyutlanir) workarea'yi ve tum monitorlerin yerlesimini gunceller.
    fn on_property_notify(&mut self, ev: PropertyNotifyEvent) -> Result<()> {
        if !self.docks.contains(&ev.window) {
            return Ok(());
        }
        if ev.atom == self.atoms._NET_WM_STRUT_PARTIAL || ev.atom == self.atoms._NET_WM_STRUT {
            match self.read_strut(ev.window) {
                Some(s) => {
                    self.struts.insert(ev.window, s);
                }
                None => {
                    self.struts.remove(&ev.window);
                }
            }
            self.sync_ewmh()?;
            self.relayout_all()?;
        }
        Ok(())
    }

    fn relayout_all(&mut self) -> Result<()> {
        for i in 0..self.monitors.len() {
            self.relayout_monitor(i)?;
        }
        Ok(())
    }

    /// `_NET_CURRENT_DESKTOP`/`_NET_DESKTOP_NAMES`/`_NET_NUMBER_OF_DESKTOPS`
    /// ve `_NET_WORKAREA`'yi birlikte gunceller. Workspace sayisi ya da
    /// dock/strut durumu degisen her yerde cagrilmasi beklenir.
    fn sync_ewmh(&self) -> Result<()> {
        self.update_desktop_properties()?;
        self.update_workarea()?;
        Ok(())
    }

    /// `_NET_WORKAREA`: basitlik icin tum sanal masaustleri icin aktif
    /// monitorun (strut dusulmus) alanini yayinlar; tam dogru multi-monitor
    /// semantigi (her monitorun kendi workarea'si) EWMH'nin viewport
    /// mekanizmasini gerektirir ve bu surumde kapsam disidir.
    fn update_workarea(&self) -> Result<()> {
        let root = self.xc.root();
        let total_desktops: usize = self.monitors.iter().map(|m| m.workspaces.len()).sum::<usize>().max(1);
        let m = &self.monitors[self.active_monitor].monitor;
        let s = self.total_struts();
        let x = (m.x as i32 + s.left).max(0) as u32;
        let y = (m.y as i32 + s.top).max(0) as u32;
        let w = (m.width as i32 - s.left - s.right).max(1) as u32;
        let h = (m.height as i32 - s.top - s.bottom).max(1) as u32;
        let mut vals = Vec::with_capacity(total_desktops * 4);
        for _ in 0..total_desktops {
            vals.extend_from_slice(&[x, y, w, h]);
        }
        self.xc
            .conn
            .change_property32(PropMode::REPLACE, root, self.atoms._NET_WORKAREA, AtomEnum::CARDINAL, &vals)?;
        Ok(())
    }

    fn supports_wm_delete(&self, win: Window) -> Result<bool> {
        let reply = self
            .xc
            .conn
            .get_property(false, win, self.atoms.WM_PROTOCOLS, AtomEnum::ATOM, 0, 1024)?
            .reply()?;
        let protocols: Vec<u32> = reply.value32().map(|it| it.collect()).unwrap_or_default();
        Ok(protocols.contains(&self.atoms.WM_DELETE_WINDOW))
    }

    fn close_window(&self, win: Window) -> Result<()> {
        if self.supports_wm_delete(win).unwrap_or(false) {
            let event = ClientMessageEvent::new(
                32,
                win,
                self.atoms.WM_PROTOCOLS,
                [self.atoms.WM_DELETE_WINDOW, x11rb::CURRENT_TIME, 0, 0, 0],
            );
            self.xc.conn.send_event(false, win, EventMask::NO_EVENT, event)?;
        } else {
            self.xc.conn.kill_client(win)?;
        }
        self.xc.conn.flush()?;
        Ok(())
    }

    // --- Workspace cozumleme / gecis ---

    fn find_workspace_index(mon: &MonitorState, target: &str) -> Option<usize> {
        if let Ok(n) = target.parse::<usize>() {
            if n >= 1 && n <= mon.workspaces.len() {
                return Some(n - 1);
            }
        }
        mon.workspaces.iter().position(|w| w.name.as_deref() == Some(target))
    }

    /// Hedef workspace'i (sayi veya isim) bulur; dinamik modda yoksa
    /// olusturur. Statik modda yalnizca var olan workspace'ler donebilir.
    fn resolve_or_create_workspace(&mut self, mon_idx: usize, target: &str) -> Option<usize> {
        if let Some(idx) = Self::find_workspace_index(&self.monitors[mon_idx], target) {
            return Some(idx);
        }
        if self.config.workspaces.mode != "dynamic" {
            return None;
        }
        if let Ok(n) = target.parse::<usize>() {
            if n >= 1 {
                while self.monitors[mon_idx].workspaces.len() < n {
                    let id = self.monitors[mon_idx].workspaces.len() + 1;
                    let name = self.config.workspaces.names.get(id - 1).cloned();
                    self.monitors[mon_idx]
                        .workspaces
                        .push(Workspace::new(id, name, self.config.general.split_ratio));
                }
                return Some(n - 1);
            }
            return None;
        }
        let id = self.monitors[mon_idx].workspaces.len() + 1;
        self.monitors[mon_idx].workspaces.push(Workspace::new(
            id,
            Some(target.to_string()),
            self.config.general.split_ratio,
        ));
        Some(self.monitors[mon_idx].workspaces.len() - 1)
    }

    fn switch_workspace(&mut self, mon_idx: usize, target_idx: usize) -> Result<()> {
        let old_idx = self.monitors[mon_idx].active;
        if old_idx == target_idx {
            return Ok(());
        }

        let old_tiled = self.monitors[mon_idx].workspaces[old_idx].tree.windows();
        for w in &old_tiled {
            self.xc.conn.unmap_window(*w)?;
        }
        let old_floating: Vec<Window> = self
            .clients
            .values()
            .filter(|c| c.monitor == mon_idx && c.workspace == old_idx && c.floating)
            .map(|c| c.window)
            .collect();
        for w in &old_floating {
            self.xc.conn.unmap_window(*w)?;
        }

        self.monitors[mon_idx].active = target_idx;

        let new_tiled = self.monitors[mon_idx].workspaces[target_idx].tree.windows();
        for w in &new_tiled {
            self.xc.conn.map_window(*w)?;
        }
        let new_floating: Vec<Window> = self
            .clients
            .values()
            .filter(|c| c.monitor == mon_idx && c.workspace == target_idx && c.floating)
            .map(|c| c.window)
            .collect();
        for w in &new_floating {
            self.xc.conn.map_window(*w)?;
        }

        self.focused = new_tiled.first().copied().or_else(|| new_floating.first().copied());
        self.prune_empty_workspaces(mon_idx);
        self.relayout_monitor(mon_idx)?;
        self.sync_ewmh()?;
        if let Some(f) = self.focused {
            self.focus(f)?;
        }
        Ok(())
    }

    /// Dinamik modda, aktif olmayan ve bos olan workspace'leri siler;
    /// kalan en az bir workspace'i garanti eder. Silme, vektoru
    /// sikistirdigi icin bu monitordeki tum client'larin `workspace`
    /// index'lerini de yeniden esler.
    fn prune_empty_workspaces(&mut self, mon_idx: usize) {
        if self.config.workspaces.mode != "dynamic" {
            return;
        }
        let active_before = self.monitors[mon_idx].active;
        let len = self.monitors[mon_idx].workspaces.len();
        let mut mapping: Vec<Option<usize>> = vec![None; len];
        let mut kept_indices = Vec::new();
        for i in 0..len {
            let empty = self.monitors[mon_idx].workspaces[i].is_empty();
            if empty && i != active_before {
                continue;
            }
            mapping[i] = Some(kept_indices.len());
            kept_indices.push(i);
        }

        if kept_indices.is_empty() {
            self.monitors[mon_idx].workspaces =
                vec![Workspace::new(1, None, self.config.general.split_ratio)];
            self.monitors[mon_idx].active = 0;
        } else if kept_indices.len() != len {
            let mut new_workspaces = Vec::with_capacity(kept_indices.len());
            for &i in &kept_indices {
                let placeholder = Workspace::new(0, None, self.config.general.split_ratio);
                let ws = std::mem::replace(&mut self.monitors[mon_idx].workspaces[i], placeholder);
                new_workspaces.push(ws);
            }
            self.monitors[mon_idx].workspaces = new_workspaces;
            self.monitors[mon_idx].active = mapping[active_before].unwrap_or(0);

            for c in self.clients.values_mut() {
                if c.monitor == mon_idx {
                    if let Some(Some(new_i)) = mapping.get(c.workspace) {
                        c.workspace = *new_i;
                    }
                }
            }
        }
    }

    fn update_desktop_properties(&self) -> Result<()> {
        let root = self.xc.root();
        let mut names: Vec<String> = Vec::new();
        let mut current = 0u32;
        let mut flat = 0u32;
        for (mi, m) in self.monitors.iter().enumerate() {
            for (wi, ws) in m.workspaces.iter().enumerate() {
                let label = ws.name.clone().unwrap_or_else(|| (wi + 1).to_string());
                if mi == self.active_monitor && wi == m.active {
                    current = flat;
                }
                names.push(label);
                flat += 1;
            }
        }
        self.xc.conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_NUMBER_OF_DESKTOPS,
            AtomEnum::CARDINAL,
            &[names.len() as u32],
        )?;
        self.xc.conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_CURRENT_DESKTOP,
            AtomEnum::CARDINAL,
            &[current],
        )?;
        let mut buf = Vec::new();
        for n in &names {
            buf.extend_from_slice(n.as_bytes());
            buf.push(0);
        }
        self.xc.conn.change_property8(
            PropMode::REPLACE,
            root,
            self.atoms._NET_DESKTOP_NAMES,
            self.atoms.UTF8_STRING,
            &buf,
        )?;
        self.xc.conn.flush()?;
        Ok(())
    }

    // --- Yerlesim (layout) ---

    fn relayout_monitor(&mut self, mon_idx: usize) -> Result<()> {
        let active = self.monitors[mon_idx].active;
        let windows = self.monitors[mon_idx].workspaces[active].tree.windows();

        // Fullscreen bir pencere varsa onu tam ekran yap, geri kalanini
        // (basitlik icin) oldugu gibi birak.
        if let Some(fs_win) = windows
            .iter()
            .copied()
            .find(|w| self.clients.get(w).map(|c| c.fullscreen).unwrap_or(false))
        {
            let m = self.monitors[mon_idx].monitor.clone();
            let aux = ConfigureWindowAux::default()
                .x(m.x as i32)
                .y(m.y as i32)
                .width(m.width as u32)
                .height(m.height as u32)
                .border_width(0)
                .stack_mode(StackMode::ABOVE);
            self.xc.conn.configure_window(fs_win, &aux)?;
            if let Some(c) = self.clients.get_mut(&fs_win) {
                c.x = m.x as i32;
                c.y = m.y as i32;
                c.width = m.width as u32;
                c.height = m.height as u32;
            }
            return Ok(());
        }

        let gaps = self.config.gaps.clone();
        let m = self.monitors[mon_idx].monitor.clone();
        // Dock pencerelerinin (bar) rezerve ettigi alan, dis bosluklarin
        // ustune eklenir ki polybar/waybar ile tiling cakismasin.
        let s = self.total_struts();
        let region = Rect {
            x: m.x as i32 + gaps.outer_left + s.left,
            y: m.y as i32 + gaps.outer_top + s.top,
            w: (m.width as i32 - gaps.outer_left - gaps.outer_right - s.left - s.right).max(1) as u32,
            h: (m.height as i32 - gaps.outer_top - gaps.outer_bottom - s.top - s.bottom).max(1) as u32,
        };

        let ws_layout = self.monitors[mon_idx].workspaces[active].layout;
        match ws_layout {
            Layout::Monocle => {
                for w in &windows {
                    let aux = ConfigureWindowAux::default()
                        .x(region.x)
                        .y(region.y)
                        .width(region.w)
                        .height(region.h)
                        .border_width(0);
                    self.xc.conn.configure_window(*w, &aux)?;
                    if let Some(c) = self.clients.get_mut(w) {
                        c.x = region.x;
                        c.y = region.y;
                        c.width = region.w;
                        c.height = region.h;
                    }
                }
                if let Some(focused) = self.focused {
                    let aux = ConfigureWindowAux::default().stack_mode(StackMode::ABOVE);
                    self.xc.conn.configure_window(focused, &aux)?;
                }
            }
            Layout::Bsp => {
                let Some(root) = self.monitors[mon_idx].workspaces[active].tree.root.clone() else {
                    return Ok(());
                };
                let single = windows.len() == 1;
                let inner_gap = if single && gaps.smart_gaps { 0 } else { gaps.inner };
                for (win, mut rect) in layout(&root, region, inner_gap) {
                    if let Some(c) = self.clients.get(&win) {
                        if let Some(mw) = c.min_width {
                            rect.w = rect.w.max(mw);
                        }
                        if let Some(mh) = c.min_height {
                            rect.h = rect.h.max(mh);
                        }
                    }
                    let aux = ConfigureWindowAux::default()
                        .x(rect.x)
                        .y(rect.y)
                        .width(rect.w)
                        .height(rect.h)
                        .border_width(self.config.border.width as u32);
                    self.xc.conn.configure_window(win, &aux)?;
                    if let Some(c) = self.clients.get_mut(&win) {
                        c.x = rect.x;
                        c.y = rect.y;
                        c.width = rect.w;
                        c.height = rect.h;
                    }
                }
            }
        }
        if self.bar.as_ref().map(|b| b.monitor_idx) == Some(mon_idx) {
            let _ = self.redraw_bar();
        }
        Ok(())
    }

    // --- Odak / yonlendirme ---

    fn focus(&mut self, win: Window) -> Result<()> {
        if !self.clients.contains_key(&win) {
            return Ok(());
        }
        self.xc
            .conn
            .set_input_focus(InputFocus::POINTER_ROOT, win, x11rb::CURRENT_TIME)?;
        self.focused = Some(win);
        let root = self.xc.root();
        self.xc.conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_ACTIVE_WINDOW,
            AtomEnum::WINDOW,
            &[win],
        )?;
        self.xc.conn.flush()?;
        let _ = self.redraw_bar();
        Ok(())
    }

    fn direction_delta(dir: &str) -> (i32, i32) {
        match dir {
            "west" => (-1, 0),
            "east" => (1, 0),
            "north" => (0, -1),
            "south" => (0, 1),
            _ => (0, 0),
        }
    }

    /// Odaklı pencerenin merkezinden verilen yonde en yakin komsuyu,
    /// o anki workspace'teki (yalniz tiled) pencereler arasindan bulur.
    fn find_neighbor(&self, mon_idx: usize, from: Window, dir: &str) -> Option<Window> {
        let (dx, dy) = Self::direction_delta(dir);
        let active = self.monitors[mon_idx].active;
        let from_client = self.clients.get(&from)?;
        let fx = from_client.x + from_client.width as i32 / 2;
        let fy = from_client.y + from_client.height as i32 / 2;

        let mut best: Option<(Window, i32)> = None;
        for w in self.monitors[mon_idx].workspaces[active].tree.windows() {
            if w == from {
                continue;
            }
            let Some(c) = self.clients.get(&w) else { continue };
            let cx = c.x + c.width as i32 / 2;
            let cy = c.y + c.height as i32 / 2;
            let vx = cx - fx;
            let vy = cy - fy;
            let dot = vx * dx + vy * dy;
            if dot <= 0 {
                continue;
            }
            let score = vx * vx + vy * vy;
            if best.map_or(true, |(_, s)| score < s) {
                best = Some((w, score));
            }
        }
        best.map(|(w, _)| w)
    }

    // --- IPC/keybinding aksiyon isleme ---

    fn handle_action(&mut self, action: Action) -> Response {
        match self.try_handle_action(action) {
            Ok(resp) => resp,
            Err(err) => {
                tracing::warn!("aksiyon islenirken hata: {err:#}");
                Response::err(err.to_string())
            }
        }
    }

    fn try_handle_action(&mut self, action: Action) -> Result<Response> {
        match action {
            Action::Spawn { command } => {
                spawn_command(&command);
                Ok(Response::ok(None))
            }
            Action::NodeClose => {
                if let Some(win) = self.focused {
                    self.close_window(win)?;
                }
                Ok(Response::ok(None))
            }
            Action::Focus { direction } => {
                if let Some(cur) = self.focused {
                    if let Some(target) = self.find_neighbor(self.active_monitor, cur, &direction) {
                        self.focus(target)?;
                    }
                }
                Ok(Response::ok(None))
            }
            Action::NodeSwap { direction } => {
                if let Some(cur) = self.focused {
                    if let Some(target) = self.find_neighbor(self.active_monitor, cur, &direction) {
                        let mon_idx = self.active_monitor;
                        let active = self.monitors[mon_idx].active;
                        self.monitors[mon_idx].workspaces[active]
                            .tree
                            .swap_windows(cur, target);
                        self.relayout_monitor(mon_idx)?;
                    }
                }
                Ok(Response::ok(None))
            }
            Action::NodeResize { direction, amount } => {
                if let Some(win) = self.focused {
                    let delta = amount as f32 / 100.0;
                    let signed = match direction.as_str() {
                        "west" | "north" => -delta,
                        _ => delta,
                    };
                    let mon_idx = self.active_monitor;
                    let active = self.monitors[mon_idx].active;
                    self.monitors[mon_idx].workspaces[active].tree.resize(win, signed);
                    self.relayout_monitor(mon_idx)?;
                }
                Ok(Response::ok(None))
            }
            Action::WorkspaceSwitch { target } => {
                let mon_idx = self.active_monitor;
                if let Some(idx) = self.resolve_or_create_workspace(mon_idx, &target) {
                    self.switch_workspace(mon_idx, idx)?;
                    Ok(Response::ok(None))
                } else {
                    Ok(Response::err(format!("workspace bulunamadi: {target}")))
                }
            }
            Action::NodeToWorkspace { target } => {
                let mon_idx = self.active_monitor;
                let Some(win) = self.focused else {
                    return Ok(Response::ok(None));
                };
                let Some(target_idx) = self.resolve_or_create_workspace(mon_idx, &target) else {
                    return Ok(Response::err(format!("workspace bulunamadi: {target}")));
                };
                let cur_idx = self.monitors[mon_idx].active;
                if target_idx != cur_idx {
                    let is_floating = self.clients.get(&win).map(|c| c.floating).unwrap_or(false);
                    if !is_floating {
                        self.monitors[mon_idx].workspaces[cur_idx].tree.remove(win);
                        self.monitors[mon_idx].workspaces[target_idx]
                            .tree
                            .insert(win, None, SplitDir::Vertical);
                    }
                    if let Some(c) = self.clients.get_mut(&win) {
                        c.workspace = target_idx;
                    }
                    self.xc.conn.unmap_window(win)?;
                    self.focused = self.monitors[mon_idx].workspaces[cur_idx]
                        .tree
                        .windows()
                        .first()
                        .copied();
                    self.relayout_monitor(mon_idx)?;
                    self.prune_empty_workspaces(mon_idx);
                    self.update_client_list()?;
                }
                Ok(Response::ok(None))
            }
            Action::ToggleFloating => {
                if let Some(win) = self.focused {
                    let mon_idx = self.active_monitor;
                    let active = self.monitors[mon_idx].active;
                    let is_floating = self.clients.get(&win).map(|c| c.floating).unwrap_or(false);
                    if is_floating {
                        self.monitors[mon_idx].workspaces[active]
                            .tree
                            .insert(win, None, SplitDir::Vertical);
                        if let Some(c) = self.clients.get_mut(&win) {
                            c.floating = false;
                        }
                    } else {
                        self.monitors[mon_idx].workspaces[active].tree.remove(win);
                        if let Some(c) = self.clients.get_mut(&win) {
                            c.floating = true;
                        }
                    }
                    self.relayout_monitor(mon_idx)?;
                }
                Ok(Response::ok(None))
            }
            Action::ToggleMonocle => {
                let mon_idx = self.active_monitor;
                let active = self.monitors[mon_idx].active;
                let ws = &mut self.monitors[mon_idx].workspaces[active];
                ws.layout = if ws.layout == Layout::Monocle {
                    Layout::Bsp
                } else {
                    Layout::Monocle
                };
                self.relayout_monitor(mon_idx)?;
                Ok(Response::ok(None))
            }
            Action::ToggleFullscreen => {
                if let Some(win) = self.focused {
                    if let Some(c) = self.clients.get_mut(&win) {
                        c.fullscreen = !c.fullscreen;
                    }
                    self.write_wm_state(win)?;
                    self.relayout_monitor(self.active_monitor)?;
                }
                Ok(Response::ok(None))
            }
            Action::ScratchpadToggle { name } => self.action_scratchpad_toggle(&name),
            Action::ReloadConfig => {
                let new_cfg = config::load_or_fallback(&self.config_path, Some(&self.config));
                let bar_was_enabled = self.config.bar.enabled;
                self.config = new_cfg;
                self.rules = rules::compile_rules(&self.config.rules);
                self.grab_keys()?;
                self.grab_buttons()?;

                if self.config.bar.enabled && !bar_was_enabled && !self.monitors.is_empty() {
                    let root = self.xc.root();
                    let m = self.monitors[0].monitor.clone();
                    match BarState::create(&self.xc.conn, root, 0, &m, &self.config.bar) {
                        Ok(bar) => {
                            self.struts.insert(bar.window, Self::bar_strut(&bar));
                            self.bar = Some(bar);
                        }
                        Err(err) => tracing::warn!("dahili bar olusturulamadi: {err:#}"),
                    }
                } else if !self.config.bar.enabled && bar_was_enabled {
                    if let Some(bar) = self.bar.take() {
                        self.struts.remove(&bar.window);
                        let _ = bar.destroy(&self.xc.conn);
                    }
                }

                self.relayout_all()?;
                self.sync_ewmh()?;
                tracing::info!("config yeniden yuklendi");
                Ok(Response::ok(None))
            }
            Action::Quit => {
                self.running = false;
                Ok(Response::ok(None))
            }
            Action::Query { windows } => {
                if windows {
                    let list: Vec<u32> = self.clients.keys().copied().collect();
                    Ok(Response::ok(Some(serde_json::json!({ "windows": list }))))
                } else {
                    Ok(Response::ok(None))
                }
            }
        }
    }

    fn action_scratchpad_toggle(&mut self, name: &str) -> Result<Response> {
        match self.scratchpad.toggle(name) {
            Some((win, visible)) => {
                if visible {
                    self.xc.conn.map_window(win)?;
                    let aux = ConfigureWindowAux::default().stack_mode(StackMode::ABOVE);
                    self.xc.conn.configure_window(win, &aux)?;
                    self.focus(win)?;
                } else {
                    self.xc.conn.unmap_window(win)?;
                    if self.focused == Some(win) {
                        self.focused = None;
                    }
                }
                Ok(Response::ok(None))
            }
            None => {
                if let Some(sp) = self.config.scratchpads.iter().find(|s| s.name == name).cloned() {
                    self.pending_scratchpad.insert(sp.match_class.clone(), sp.name.clone());
                    spawn_command(&sp.command);
                    Ok(Response::ok(None))
                } else {
                    Ok(Response::err(format!("tanimsiz scratchpad: {name}")))
                }
            }
        }
    }

    fn update_client_list(&mut self) -> Result<()> {
        let root = self.xc.root();
        let list: Vec<Window> = self.clients.keys().copied().collect();
        self.xc.conn.change_property32(
            PropMode::REPLACE,
            root,
            self.atoms._NET_CLIENT_LIST,
            AtomEnum::WINDOW,
            &list,
        )?;
        Ok(())
    }
}

fn button_index(n: u8) -> Option<ButtonIndex> {
    match n {
        1 => Some(ButtonIndex::M1),
        2 => Some(ButtonIndex::M2),
        3 => Some(ButtonIndex::M3),
        4 => Some(ButtonIndex::M4),
        5 => Some(ButtonIndex::M5),
        _ => None,
    }
}

fn spawn_command(command: &str) {
    let parts: Vec<&str> = command.split_whitespace().collect();
    if let Some((bin, args)) = parts.split_first() {
        if let Err(err) = std::process::Command::new(bin).args(args).spawn() {
            tracing::warn!("komut baslatilamadi '{command}': {err}");
        }
    }
}
