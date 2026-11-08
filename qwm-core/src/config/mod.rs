pub mod schema;
pub mod watcher;

use anyhow::{Context, Result};
pub use schema::Config;
use std::path::{Path, PathBuf};

/// `~/.config/qwm/qwm.toml` (ya da `$XDG_CONFIG_HOME/qwm/qwm.toml`) yolunu
/// hesaplar. Dosyanın var olup olmadığını kontrol etmez.
pub fn default_config_path() -> PathBuf {
    let base = std::env::var("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
            PathBuf::from(home).join(".config")
        });
    base.join("qwm").join("qwm.toml")
}

pub fn load(path: &Path) -> Result<Config> {
    let text = std::fs::read_to_string(path)
        .with_context(|| format!("config okunamadı: {}", path.display()))?;
    let cfg: Config = toml::from_str(&text)
        .with_context(|| format!("config parse edilemedi: {}", path.display()))?;
    Ok(cfg)
}

/// Config'i yüklemeyi dener; başarısız olursa hatayı loglayıp önceki
/// config'e (hot-reload senaryosu) ya da varsayılana düşer. Bu fonksiyon
/// WM'i ASLA panikletmemeli — bozuk bir config dosyası WM'in çökmesine
/// değil, sadece eski ayarların korunmasına yol açmalı (bkz. spesifikasyon
/// bölüm 6 "Hot-Reload").
pub fn load_or_fallback(path: &Path, previous: Option<&Config>) -> Config {
    match load(path) {
        Ok(cfg) => cfg,
        Err(err) => {
            tracing::error!("config yüklenemedi, eski ayarlar korunuyor: {err:#}");
            previous.cloned().unwrap_or_default()
        }
    }
}
