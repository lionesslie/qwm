use anyhow::{Context, Result};
use x11rb::connection::Connection;
use x11rb::protocol::xproto::{ChangeWindowAttributesAux, ConnectionExt, EventMask, Window};
use x11rb::rust_connection::RustConnection;

/// X sunucusuna açılan bağlantı ve ilgili ekran bilgisi.
pub struct XConn {
    pub conn: RustConnection,
    pub screen_num: usize,
}

impl XConn {
    /// `$DISPLAY` ortam değişkenine göre X sunucusuna bağlanır.
    pub fn connect() -> Result<Self> {
        let (conn, screen_num) =
            x11rb::connect(None).context("X sunucusuna bağlanılamadı (DISPLAY ayarlı mı?)")?;
        Ok(Self { conn, screen_num })
    }

    pub fn root(&self) -> Window {
        self.conn.setup().roots[self.screen_num].root
    }

    /// Root pencere üzerinde `SubstructureRedirect` alarak bu sürecin tek
    /// window manager olduğunu X sunucusuna bildirir.
    ///
    /// X11'de aynı anda yalnızca bir istemci `SubstructureRedirect` event
    /// mask'ini alabilir; zaten bir WM çalışıyorsa bu çağrı `BadAccess`
    /// hatasıyla başarısız olur ve bu durum açıkça hataya çevrilir, ki
    /// kullanıcı "zaten bir WM çalışıyor" mesajını net görsün.
    pub fn become_wm(&self) -> Result<()> {
        let root = self.root();
        let aux = ChangeWindowAttributesAux::default().event_mask(
            EventMask::SUBSTRUCTURE_REDIRECT
                | EventMask::SUBSTRUCTURE_NOTIFY
                | EventMask::STRUCTURE_NOTIFY
                | EventMask::PROPERTY_CHANGE,
        );
        self.conn
            .change_window_attributes(root, &aux)?
            .check()
            .context("root pencerede event mask alınamadı — başka bir window manager zaten çalışıyor olabilir")?;
        self.conn.flush()?;
        Ok(())
    }
}
