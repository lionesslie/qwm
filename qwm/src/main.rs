use anyhow::Result;
use qwm_core::config::{self, Config};
use qwm_core::ipc::{self, protocol::Response};
use qwm_core::keybind::{self, Action};
use qwm_core::wm::Wm;
use qwm_core::x11::connection::XConn;
use signal_hook::consts::{SIGHUP, SIGINT, SIGTERM};
use signal_hook::iterator::Signals;
use std::sync::mpsc::{self, Sender};
use tracing_subscriber::EnvFilter;

fn main() -> Result<()> {
    // `qwm` bir WM baslatmadan, sadece `qwm.toml`'daki `[[keybind]]`
    // listesinden bir sxhkd config'i uretip cikar. qwm artik tuslari
    // kendisi gripli-emez (XGrabKey yerine sxhkd kullanilir, bkz. README);
    // bu komut iki ayri config dosyasi elle senkron tutmak zorunda
    // kalmamak icin tek kaynaktan (qwm.toml) uretim yapar.
    let args: Vec<String> = std::env::args().collect();
    if let Some(flag_pos) = args.iter().position(|a| a == "--export-sxhkd") {
        let config_path = config::default_config_path();
        let config = config::load(&config_path)
            .map_err(|err| anyhow::anyhow!("config okunamadi ({}): {err:#}", config_path.display()))?;
        let sxhkdrc = export_sxhkd(&config);
        match args.get(flag_pos + 1) {
            Some(out_path) => {
                std::fs::write(out_path, sxhkdrc)?;
                eprintln!("sxhkdrc yazildi: {out_path}");
            }
            None => print!("{sxhkdrc}"),
        }
        return Ok(());
    }

    install_panic_hook();

    let config_path = config::default_config_path();
    let config: Config = config::load(&config_path).unwrap_or_else(|err| {
        eprintln!(
            "config yuklenemedi ({err:#}), varsayilan ayarlar kullaniliyor: {}",
            config_path.display()
        );
        Config::default()
    });

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::new(config.log.level.clone()))
        .init();

    tracing::info!("qwm baslatiliyor (config: {})", config_path.display());

    let xc = XConn::connect()?;
    xc.become_wm()?;

    let mut wm = Wm::new(xc, config.clone(), config_path.clone())?;
    wm.init_ewmh()?;

    run_autostart(&config);

    let (tx, rx) = mpsc::channel::<(Action, Sender<Response>)>();
    let socket_path = config.ipc.socket_path.clone();
    {
        let socket_path = socket_path.clone();
        let tx = tx.clone();
        std::thread::spawn(move || {
            if let Err(err) = ipc::server::start(&socket_path, tx) {
                tracing::error!("IPC sunucusu baslatilamadi: {err:#}");
            }
        });
    }

    // SIGHUP -> config'i yeniden yukle (hot-reload ile ayni mekanizma),
    // SIGTERM/SIGINT -> running=false ile ana dongunun temiz cikmasini
    // tetikle. Her iki durumda da sinyal, IPC kanaliyla ayni Action'a
    // cevrilip ana WM dongusune gonderilir; boylece X11 state'ine
    // (self.clients, self.monitors vb.) yalnizca tek bir thread dokunur.
    if let Err(err) = install_signal_handlers(tx) {
        tracing::warn!("sinyal yakalayicilari kurulamadi: {err:#}");
    }

    wm.run(rx)?;

    // Socket dosyasini temizle ki bir sonraki baslatmada "adres zaten
    // kullaniliyor" hatasi alinmasin (bkz. spesifikasyon bolum 14).
    let _ = std::fs::remove_file(&socket_path);

    tracing::info!("qwm kapatiliyor");
    Ok(())
}

fn install_signal_handlers(tx: Sender<(Action, Sender<Response>)>) -> Result<()> {
    let mut signals = Signals::new([SIGHUP, SIGTERM, SIGINT])?;
    std::thread::spawn(move || {
        for sig in signals.forever() {
            let action = match sig {
                SIGHUP => {
                    tracing::info!("SIGHUP alindi, config yeniden yukleniyor");
                    Action::ReloadConfig
                }
                SIGTERM | SIGINT => {
                    tracing::info!("SIGTERM/SIGINT alindi, kapatiliyor");
                    Action::Quit
                }
                _ => continue,
            };
            // Bu kanaldaki yanit kimse tarafindan okunmuyor (fire-and-forget);
            // `ipc::server` ile ayni protokolu kullanmak, Wm::handle_action'i
            // degistirmeden sinyalleri de normal bir komut gibi islememizi saglar.
            let (resp_tx, _resp_rx) = mpsc::channel();
            if tx.send((action, resp_tx)).is_err() {
                break; // Wm ana dongusu zaten kapanmis.
            }
        }
    });
    Ok(())
}

fn run_autostart(config: &Config) {
    for cmd in &config.autostart.commands {
        let parts: Vec<&str> = cmd.split_whitespace().collect();
        if let Some((bin, args)) = parts.split_first() {
            if let Err(err) = std::process::Command::new(bin).args(args).spawn() {
                tracing::warn!("autostart komutu baslatilamadi '{cmd}': {err}");
            }
        }
    }
}

/// `config.keybinds`'ten bir `sxhkdrc` icerigi uretir. `qwm.toml`'daki
/// `"Mod"` token'i sxhkd'nin `super` anahtar kelimesine, diger token'lar
/// (harfler, `Return`, `grave` vb.) oldugu gibi gecer; sxhkd bu isimleri
/// zaten X11 keysym adlariyla ayni sekilde cozumler.
fn export_sxhkd(config: &Config) -> String {
    let mut out = String::new();
    out.push_str("# qwm.toml'daki [[keybind]] listesinden uretildi, elle duzenlemeyin.\n");
    out.push_str("# Yeniden uretmek icin: qwm --export-sxhkd ~/.config/sxhkd/sxhkdrc\n\n");

    for kb in &config.keybinds {
        let Some(action) = keybind::action_from_keybind(kb) else {
            eprintln!("# atlanildi (taninmayan aksiyon): {} -> {}", kb.keys, kb.action);
            continue;
        };
        let Some(command) = keybind::action_to_qwmctl_command(&action) else {
            continue; // orn. Query: sxhkd icin anlamli degil
        };
        out.push_str(&sxhkd_chain(&kb.keys));
        out.push('\n');
        out.push_str("    ");
        out.push_str(&command);
        out.push_str("\n\n");
    }
    out
}

fn sxhkd_chain(spec: &str) -> String {
    spec.split('+')
        .map(|part| match part {
            "Mod" | "Super" => "super",
            "Shift" => "shift",
            "Ctrl" | "Control" => "ctrl",
            "Alt" => "alt",
            other => other,
        })
        .collect::<Vec<_>>()
        .join(" + ")
}

fn install_panic_hook() {
    // Cokus aninda en azindan hatayi logla ve stderr'e yazdir; X sunucusu
    // zaten baglanti kapaninca SubstructureRedirect'i geri alacaktir, bu
    // sayede ekran tamamen kilitli kalmaz (bkz. spesifikasyon bolum 14).
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        tracing::error!("qwm panic oldu: {info}");
        default_hook(info);
    }));
}
