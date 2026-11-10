//! `qwmctl`: qwm'in Unix socket IPC'si üzerinden konuşan CLI istemcisi.
//! Bu binary bilerek `qwm-core`'a bağımlı DEĞİLDİR (X11 gerektirmez),
//! yalnızca JSON mesajları gönderip alır — bkz. `qwm_core::ipc::protocol`.

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use serde_json::json;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;

#[derive(Parser)]
#[command(name = "qwmctl", about = "qwm window manager için komut satırı istemcisi")]
struct Cli {
    /// qwm'in dinlediği IPC socket yolu (config'deki `[ipc] socket_path` ile eşleşmeli)
    #[arg(long, default_value = "/tmp/qwm.sock")]
    socket: String,

    #[command(subcommand)]
    command: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Pencere odağı / durumu ile ilgili komutlar (bspwm'deki `bspc node` karşılığı)
    Node {
        /// Odağı belirtilen yöne kaydır: west|east|north|south
        #[arg(short = 'f', long)]
        focus: Option<String>,
        /// Odaklı pencereyi belirtilen yöndeki ile yer değiştir
        #[arg(short = 's', long)]
        swap: Option<String>,
        /// Durum değiştir: floating|monocle|fullscreen
        #[arg(short = 't', long)]
        toggle: Option<String>,
        /// Odaklı pencereyi başka bir workspace'e taşı
        #[arg(short = 'd', long)]
        to_workspace: Option<String>,
        /// Split oranını değiştir: "<yön>:<yüzde>" (ör. "west:10")
        #[arg(long)]
        resize: Option<String>,
        /// Odaklı pencereyi kapat (hiçbir bayrak verilmezse varsayılan davranış)
        #[arg(short = 'c', long)]
        close: bool,
    },
    /// Workspace/desktop komutları
    Desktop {
        /// Belirtilen workspace'e geç (id veya isim)
        #[arg(short = 'f', long)]
        focus: Option<String>,
    },
    /// Scratchpad kontrolü
    Scratchpad {
        /// show | hide | toggle
        action: String,
        name: String,
    },
    /// Config'i yeniden yükle
    Config {
        /// şimdilik yalnızca "reload" destekleniyor
        action: String,
    },
    /// WM state'ini sorgula (scripting için)
    Query {
        #[arg(long)]
        windows: bool,
    },
    /// Rastgele bir komut başlat (örn. terminal, launcher)
    Spawn { command: Vec<String> },
    /// qwm'i kapat
    Quit,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let payload = match cli.command {
        Cmd::Node {
            focus,
            swap,
            toggle,
            to_workspace,
            resize,
            close,
        } => {
            if let Some(dir) = focus {
                json!({"cmd": "focus", "args": {"direction": dir}})
            } else if let Some(dir) = swap {
                json!({"cmd": "node_swap", "args": {"direction": dir}})
            } else if let Some(state) = toggle {
                match state.as_str() {
                    "monocle" => json!({"cmd": "toggle_monocle", "args": {}}),
                    "fullscreen" => json!({"cmd": "toggle_fullscreen", "args": {}}),
                    _ => json!({"cmd": "toggle_floating", "args": {}}),
                }
            } else if let Some(target) = to_workspace {
                json!({"cmd": "node_to_workspace", "args": {"target": target}})
            } else if let Some(spec) = resize {
                let (dir, amount) = spec
                    .split_once(':')
                    .context("--resize \"<yön>:<yüzde>\" biçiminde olmalı (ör. \"west:10\")")?;
                let amount: i32 = amount
                    .parse()
                    .context("--resize'daki yüzde bir tam sayı olmalı")?;
                json!({"cmd": "node_resize", "args": {"direction": dir, "amount": amount}})
            } else if close {
                json!({"cmd": "node_close", "args": {}})
            } else {
                anyhow::bail!("node için en az bir bayrak gerekli: -f/-s/-t/-d/-c/--resize");
            }
        }
        Cmd::Desktop { focus } => json!({
            "cmd": "workspace_switch",
            "args": {"target": focus.context("desktop için -f/--focus gerekli")?}
        }),
        Cmd::Scratchpad { name, .. } => json!({
            "cmd": "scratchpad_toggle",
            "args": {"name": name}
        }),
        Cmd::Config { .. } => json!({"cmd": "reload_config", "args": {}}),
        Cmd::Query { windows } => json!({"cmd": "query", "args": {"windows": windows}}),
        Cmd::Spawn { command } => json!({
            "cmd": "spawn",
            "args": {"command": command.join(" ")}
        }),
        Cmd::Quit => json!({"cmd": "quit", "args": {}}),
    };

    let response = send(&cli.socket, &payload)
        .with_context(|| format!("qwm'e bağlanılamadı ({}); WM çalışıyor mu?", cli.socket))?;
    println!("{}", serde_json::to_string_pretty(&response)?);
    Ok(())
}

fn send(socket: &str, payload: &serde_json::Value) -> Result<serde_json::Value> {
    let mut stream = UnixStream::connect(socket)?;
    let mut line = payload.to_string();
    line.push('\n');
    stream.write_all(line.as_bytes())?;

    let mut reader = BufReader::new(stream);
    let mut response_line = String::new();
    reader.read_line(&mut response_line)?;
    Ok(serde_json::from_str(&response_line)?)
}
