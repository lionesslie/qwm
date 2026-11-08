//! Ana WM state makinesi ve olay döngüsü.
//!
//! Faz 0/1 kapsamında: X11 bağlantısını kurma, tek bir (monitör/workspace
//! ayrımı henüz yapılmamış) BSP ağacı üzerinde temel tiling, ve IPC'den
//! gelen birkaç temel aksiyonun (`spawn`, `quit`, `query`) işlenmesi.
//! Multi-monitor/workspace entegrasyonu, floating/scratchpad, tam EWMH
//! state senkronizasyonu ve mouse move/resize sonraki fazlarda bu
//! struct'a eklenecek (bkz. proje spesifikasyonu bölüm 11).

use crate::config::Config;
use crate::ipc::protocol::Response;
use crate::keybind::Action;
use crate::layout::bsp_tree::{BspTree, SplitDir};
use crate::layout::geometry::{layout, Rect};
use crate::window::Client;
use crate::x11::atoms::Atoms;
use crate::x11::connection::XConn;
use anyhow::Result;
use std::collections::HashMap;
use std::sync::mpsc::{Receiver, Sender};
use std::time::Duration;
use x11rb::connection::Connection;
use x11rb::protocol::xproto::*;
use x11rb::protocol::Event;

pub struct Wm {
    pub xc: XConn,
    pub atoms: Atoms,
    pub config: Config,
    pub clients: HashMap<Window, Client>,
    pub tree: BspTree,
    pub focused: Option<Window>,
    pub running: bool,
}

impl Wm {
    pub fn new(xc: XConn, config: Config) -> Result<Self> {
        let atoms = Atoms::new(&xc.conn)?.reply()?;
        let split_ratio = config.general.split_ratio;
        Ok(Self {
            xc,
            atoms,
            config,
            clients: HashMap::new(),
            tree: BspTree::new(split_ratio),
            focused: None,
            running: true,
        })
    }

    /// EWMH için gerekli temel kök pencere özelliklerini ilan eder:
    /// `_NET_SUPPORTED`, `_NET_SUPPORTING_WM_CHECK` ve başlangıçta boş bir
    /// `_NET_CLIENT_LIST`. `_NET_WM_STRUT_PARTIAL` desteği (polybar/waybar
    /// için kritik) client tarafı property okumasıyla Faz 5'te tamamlanır.
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
        Ok(())
    }

    /// Ana olay döngüsü: X11 event'lerini ve IPC'den gelen komutları
    /// non-blocking şekilde, tek thread'de sırayla işler. Tüm X11
    /// çağrıları yalnızca bu thread'den yapılır (x11rb bağlantısı thread
    /// güvenli değildir varsayılarak).
    pub fn run(&mut self, ipc_rx: Receiver<(Action, Sender<Response>)>) -> Result<()> {
        self.xc.conn.flush()?;
        while self.running {
            while let Some(event) = self.xc.conn.poll_for_event()? {
                self.handle_event(event)?;
            }
            if let Ok((action, resp_tx)) = ipc_rx.try_recv() {
                let resp = self.handle_action(action);
                let _ = resp_tx.send(resp);
            }
            self.xc.conn.flush()?;
            // Basit polling aralığı; CPU kullanımını düşük tutarken IPC/X11
            // olaylarına makul bir tepki süresi (≈10ms) sağlar. Faz
            // sonrasında `poll(2)` ile iki fd'yi (X11 socket + IPC'den
            // haber veren bir self-pipe) birlikte beklemek daha verimli
            // olur.
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
            Event::EnterNotify(ev) => {
                if self.config.general.focus_follows_mouse {
                    self.focus(ev.event)?;
                }
            }
            _ => {}
        }
        Ok(())
    }

    fn on_map_request(&mut self, ev: MapRequestEvent) -> Result<()> {
        let win = ev.window;
        self.xc.conn.map_window(win)?;

        let dir = match self.config.general.auto_split_direction.as_str() {
            "horizontal" => SplitDir::Horizontal,
            "vertical" => SplitDir::Vertical,
            _ => SplitDir::Vertical, // "auto": Faz 1'de pencere en-boy oranına göre seçilecek
        };
        self.tree.insert(win, self.focused, dir);
        self.clients.insert(win, Client::new(win, 0));

        if self.config.general.new_window_takes_focus {
            self.focused = Some(win);
        }
        self.relayout()?;
        self.update_client_list()?;
        Ok(())
    }

    fn on_unmap(&mut self, win: Window) -> Result<()> {
        if self.clients.remove(&win).is_some() {
            self.tree.remove(win);
            if self.focused == Some(win) {
                self.focused = self.tree.windows().first().copied();
            }
            self.relayout()?;
            self.update_client_list()?;
        }
        Ok(())
    }

    fn on_configure_request(&mut self, ev: ConfigureRequestEvent) -> Result<()> {
        // Henüz tiling'e dahil edilmemiş (örn. map edilmeden önce boyut
        // isteyen) pencereler için istenen geometriyi olduğu gibi onayla;
        // tiled pencerelerin asıl konumu `relayout`da zaten ayarlanıyor.
        let aux = ConfigureWindowAux::from_configure_request(&ev);
        self.xc.conn.configure_window(ev.window, &aux)?;
        Ok(())
    }

    fn relayout(&mut self) -> Result<()> {
        let Some(root_node) = &self.tree.root else {
            return Ok(());
        };
        let geom = self.xc.conn.get_geometry(self.xc.root())?.reply()?;
        let gaps = &self.config.gaps;
        let single = self.tree.windows().len() == 1;
        let inner_gap = if single && gaps.smart_gaps {
            0
        } else {
            gaps.inner
        };
        let region = Rect {
            x: gaps.outer_left,
            y: gaps.outer_top,
            w: (geom.width as i32 - gaps.outer_left - gaps.outer_right).max(1) as u32,
            h: (geom.height as i32 - gaps.outer_top - gaps.outer_bottom).max(1) as u32,
        };
        for (win, rect) in layout(root_node, region, inner_gap) {
            let aux = ConfigureWindowAux::default()
                .x(rect.x)
                .y(rect.y)
                .width(rect.w)
                .height(rect.h)
                .border_width(self.config.border.width as u32);
            self.xc.conn.configure_window(win, &aux)?;
        }
        Ok(())
    }

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
        Ok(())
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

    /// IPC'den (veya WM-içi keybinding'den) gelen bir `Action`'ı işler.
    /// Henüz implemente edilmemiş aksiyonlar `error` yanıtı döner ama
    /// WM'i etkilemez (bkz. spesifikasyon bölüm 11 — fazlar ilerledikçe
    /// buradaki `match` kolları doldurulacak).
    fn handle_action(&mut self, action: Action) -> Response {
        match action {
            Action::Spawn { command } => {
                spawn_command(&command);
                Response::ok(None)
            }
            Action::Quit => {
                self.running = false;
                Response::ok(None)
            }
            Action::Query { windows } => {
                if windows {
                    let list: Vec<u32> = self.clients.keys().copied().collect();
                    Response::ok(Some(serde_json::json!({ "windows": list })))
                } else {
                    Response::ok(None)
                }
            }
            other => {
                tracing::debug!("henüz implemente edilmemiş aksiyon: {other:?}");
                Response::err("henüz implemente edilmedi")
            }
        }
    }
}

fn spawn_command(command: &str) {
    let parts: Vec<&str> = command.split_whitespace().collect();
    if let Some((bin, args)) = parts.split_first() {
        if let Err(err) = std::process::Command::new(bin).args(args).spawn() {
            tracing::warn!("komut başlatılamadı '{command}': {err}");
        }
    }
}
