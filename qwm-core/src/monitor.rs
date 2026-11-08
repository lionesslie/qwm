use anyhow::Result;
use x11rb::connection::Connection;
use x11rb::protocol::randr::ConnectionExt as _;
use x11rb::protocol::xproto::{ConnectionExt as _, Window};

#[derive(Debug, Clone)]
pub struct Monitor {
    pub name: String,
    pub x: i16,
    pub y: i16,
    pub width: u16,
    pub height: u16,
}

/// RandR üzerinden bağlı monitörleri (aktif CRTC'leri) sorgular.
/// RandR extension mevcut değilse veya hiçbir CRTC bulunamazsa, tüm
/// ekranı kaplayan tek bir "sanal" monitör döner — böylece WM, RandR'siz
/// ortamlarda da (örn. Xephy testleri) çalışabilir.
pub fn query_monitors<C: Connection>(conn: &C, root: Window) -> Result<Vec<Monitor>> {
    if let Ok(resources) = conn.randr_get_screen_resources_current(root)?.reply() {
        let mut monitors = Vec::new();
        for crtc in resources.crtcs {
            if let Ok(info) = conn
                .randr_get_crtc_info(crtc, resources.config_timestamp)?
                .reply()
            {
                if info.width == 0 || info.height == 0 {
                    continue;
                }
                monitors.push(Monitor {
                    name: format!("crtc-{crtc}"),
                    x: info.x,
                    y: info.y,
                    width: info.width,
                    height: info.height,
                });
            }
        }
        if !monitors.is_empty() {
            return Ok(monitors);
        }
    }
    Ok(vec![default_monitor(conn, root)?])
}

fn default_monitor<C: Connection>(conn: &C, root: Window) -> Result<Monitor> {
    let geom = conn.get_geometry(root)?.reply()?;
    Ok(Monitor {
        name: "default".into(),
        x: 0,
        y: 0,
        width: geom.width,
        height: geom.height,
    })
}
