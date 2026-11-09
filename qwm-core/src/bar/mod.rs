//! Dahili, opsiyonel status bar (`[bar] enabled = true`).
//!
//! Bagimlilik yukunu dusuk tutmak icin cairo/pango yerine dogrudan
//! cekirdek X11 metin cizimi (`PolyFillRectangle` + `ImageText8`, "fixed"
//! cekirdek fontu) kullanilir; bu yuzden `[bar] font` ayari su an goz
//! ardi edilir. Yalnizca birincil monitorde (index 0) gosterilir; sag
//! taraf modulleri (`modules_right`, saat/pil vb.) henuz implemente
//! edilmedi. Barin kendi rezerve ettigi alan, dock pencerelerininkiyle
//! ayni mekanizmayi (`Wm::struts`) kullanarak tiling alanindan dusulur.

use crate::config::schema::Bar;
use crate::monitor::Monitor;
use anyhow::Result;
use x11rb::connection::Connection;
use x11rb::protocol::xproto::*;

pub struct BarState {
    pub window: Window,
    pub monitor_idx: usize,
    pub height: u16,
    pub position_top: bool,
    gc_bg: Gcontext,
    gc_fg: Gcontext,
    gc_accent: Gcontext,
    font: Font,
    width: u16,
}

impl BarState {
    pub fn create<C: Connection>(
        conn: &C,
        root: Window,
        monitor_idx: usize,
        monitor: &Monitor,
        config: &Bar,
    ) -> Result<Self> {
        let window = conn.generate_id()?;
        let position_top = config.position != "bottom";
        let y = if position_top {
            monitor.y
        } else {
            monitor.y + monitor.height as i16 - config.height as i16
        };

        let bg = alloc_color(conn, &config.background)?;
        let fg = alloc_color(conn, &config.foreground)?;
        let accent = alloc_color(conn, "#89b4fa").unwrap_or(fg);

        let aux = CreateWindowAux::default()
            .background_pixel(bg)
            .event_mask(EventMask::EXPOSURE);
        conn.create_window(
            x11rb::COPY_DEPTH_FROM_PARENT,
            window,
            root,
            monitor.x,
            y,
            monitor.width,
            config.height,
            0,
            WindowClass::INPUT_OUTPUT,
            0,
            &aux,
        )?;

        let font = conn.generate_id()?;
        conn.open_font(font, b"fixed")?;

        let gc_bg = conn.generate_id()?;
        conn.create_gc(gc_bg, window, &CreateGCAux::default().foreground(bg).background(bg))?;
        let gc_fg = conn.generate_id()?;
        conn.create_gc(
            gc_fg,
            window,
            &CreateGCAux::default().foreground(fg).background(bg).font(font),
        )?;
        let gc_accent = conn.generate_id()?;
        conn.create_gc(
            gc_accent,
            window,
            &CreateGCAux::default().foreground(accent).background(bg).font(font),
        )?;

        conn.map_window(window)?;
        conn.flush()?;

        Ok(Self {
            window,
            monitor_idx,
            height: config.height,
            position_top,
            gc_bg,
            gc_fg,
            gc_accent,
            font,
            width: monitor.width,
        })
    }

    pub fn destroy<C: Connection>(&self, conn: &C) -> Result<()> {
        conn.close_font(self.font)?;
        conn.free_gc(self.gc_bg)?;
        conn.free_gc(self.gc_fg)?;
        conn.free_gc(self.gc_accent)?;
        conn.destroy_window(self.window)?;
        conn.flush()?;
        Ok(())
    }

    /// `labels`: her workspace icin (etiket, aktif_mi); `title`: odakli
    /// pencerenin basligi (etiketlerin sagina yazilir).
    pub fn redraw<C: Connection>(&self, conn: &C, labels: &[(String, bool)], title: &str) -> Result<()> {
        conn.poly_fill_rectangle(
            self.window,
            self.gc_bg,
            &[Rectangle {
                x: 0,
                y: 0,
                width: self.width,
                height: self.height,
            }],
        )?;

        let mut x: i16 = 8;
        let baseline = (self.height as i16) / 2 + 5;
        for (label, active) in labels {
            let text_w = (label.chars().count() as i16) * 7 + 12;
            if *active {
                conn.poly_fill_rectangle(
                    self.window,
                    self.gc_accent,
                    &[Rectangle {
                        x,
                        y: 2,
                        width: text_w as u16,
                        height: self.height.saturating_sub(4),
                    }],
                )?;
            }
            conn.image_text8(self.window, self.gc_fg, x + 6, baseline, label.as_bytes())?;
            x += text_w + 4;
        }

        if !title.is_empty() {
            let truncated: String = title.chars().take(80).collect();
            conn.image_text8(self.window, self.gc_fg, x + 16, baseline, truncated.as_bytes())?;
        }

        conn.flush()?;
        Ok(())
    }
}

/// Hex rengi (`"#rrggbb"`) X sunucusunun varsayilan colormap'inden bir
/// piksel degerine cevirir. Not: tek X "screen" (ekran 0) varsayilir —
/// RandR tabanli multi-monitor kurulumlarinin neredeyse tamami icin
/// gecerlidir, birden fazla X screen'i (ayri colormap'ler) kapsam disidir.
fn alloc_color<C: Connection>(conn: &C, hex: &str) -> Result<u32> {
    let s = hex.trim_start_matches('#');
    let r = u8::from_str_radix(s.get(0..2).unwrap_or("00"), 16).unwrap_or(0);
    let g = u8::from_str_radix(s.get(2..4).unwrap_or("00"), 16).unwrap_or(0);
    let b = u8::from_str_radix(s.get(4..6).unwrap_or("00"), 16).unwrap_or(0);
    let colormap = conn.setup().roots[0].default_colormap;
    let reply = conn
        .alloc_color(colormap, (r as u16) * 257, (g as u16) * 257, (b as u16) * 257)?
        .reply()?;
    Ok(reply.pixel)
}
