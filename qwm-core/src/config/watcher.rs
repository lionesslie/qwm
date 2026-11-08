use anyhow::Result;
use notify::{RecursiveMode, Watcher};
use std::path::Path;
use std::sync::mpsc::{channel, Receiver};

/// Config dosyasını `inotify` (Linux) üzerinden izler; her değişiklikte
/// kanaldan bir sinyal gönderir. Ana döngü bu kanalı `try_recv` ile
/// polling yaparak okur (bkz. `wm::Wm::run`).
///
/// Dönen `notify::RecommendedWatcher` canlı tutulmalıdır — drop edilirse
/// işletim sistemi seviyesindeki izleme de durur.
pub fn watch(path: &Path) -> Result<(notify::RecommendedWatcher, Receiver<()>)> {
    let (tx, rx) = channel();
    let mut watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
        if res.is_ok() {
            // Hatalı/ilgisiz event'lerde bile basitçe "bir şey değişti"
            // sinyali gönderiyoruz; asıl doğrulama `config::load` içinde
            // (TOML parse + serde) yapılır.
            let _ = tx.send(());
        }
    })?;
    watcher.watch(path, RecursiveMode::NonRecursive)?;
    Ok((watcher, rx))
}
