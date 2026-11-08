//! Dahili opsiyonel status bar (`[bar] enabled = true`).
//!
//! v1 iskeletinde devre dışı bırakılmış bir stub'tır. Faz 7'de
//! `cairo-rs` + `pango` (ya da doğrudan x11rb `PutImage`/`PolyText8`)
//! kullanılarak workspace göstergesi, pencere başlığı ve sağdaki
//! modüllerin (saat, pil vb.) render edilmesi planlanıyor. `[external_bar]`
//! açıkken (varsayılan) qwm zaten EWMH atomlarını (bkz. `x11::atoms`)
//! yayınladığı için polybar/waybar bu modül olmadan da çalışır.

use crate::config::schema::Bar;

pub struct InternalBar {
    #[allow(dead_code)]
    config: Bar,
}

impl InternalBar {
    pub fn new(config: Bar) -> Option<Self> {
        if config.enabled {
            Some(Self { config })
        } else {
            None
        }
    }
}
