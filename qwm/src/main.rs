use anyhow::Result;
use qwm_core::config::{self, Config};
use qwm_core::ipc;
use qwm_core::wm::Wm;
use qwm_core::x11::connection::XConn;
use std::sync::mpsc;
use tracing_subscriber::EnvFilter;

fn main() -> Result<()> {
    install_panic_hook();

    let config_path = config::default_config_path();
    let config: Config = config::load(&config_path).unwrap_or_else(|err| {
        eprintln!(
            "config yüklenemedi ({err:#}), varsayılan ayarlar kullanılıyor: {}",
            config_path.display()
        );
        Config::default()
    });

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::new(config.log.level.clone()))
        .init();

    tracing::info!("qwm başlatılıyor (config: {})", config_path.display());

    let xc = XConn::connect()?;
    xc.become_wm()?;

    let mut wm = Wm::new(xc, config.clone())?;
    wm.init_ewmh()?;

    run_autostart(&config);

    let (tx, rx) = mpsc::channel();
    {
        let socket_path = config.ipc.socket_path.clone();
        std::thread::spawn(move || {
            if let Err(err) = ipc::server::start(&socket_path, tx) {
                tracing::error!("IPC sunucusu başlatılamadı: {err:#}");
            }
        });
    }

    // TODO (Faz 7): SIGHUP -> config::load_or_fallback + relayout,
    // SIGTERM/SIGINT -> graceful shutdown (pencereleri floating'e çevirip
    // bırak, socket dosyasını temizle). `signal-hook` crate'i ile eklenecek.

    wm.run(rx)?;
    tracing::info!("qwm kapatılıyor");
    Ok(())
}

fn run_autostart(config: &Config) {
    for cmd in &config.autostart.commands {
        let parts: Vec<&str> = cmd.split_whitespace().collect();
        if let Some((bin, args)) = parts.split_first() {
            if let Err(err) = std::process::Command::new(bin).args(args).spawn() {
                tracing::warn!("autostart komutu başlatılamadı '{cmd}': {err}");
            }
        }
    }
}

fn install_panic_hook() {
    // Çöküş anında en azından hatayı logla ve stderr'e yazdır; X sunucusu
    // zaten bağlantı kapanınca SubstructureRedirect'i geri alacaktır, bu
    // sayede ekran tamamen kilitli kalmaz (bkz. spesifikasyon bölüm 14).
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        tracing::error!("qwm panic oldu: {info}");
        default_hook(info);
    }));
}
