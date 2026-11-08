use super::protocol::{Request, Response};
use crate::keybind::Action;
use anyhow::Result;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::sync::mpsc::Sender;

/// Unix domain socket üzerinde dinler. Her gelen bağlantı ayrı bir
/// thread'de ele alınır; satır satır okunan JSON komutları `Action`'a
/// çözümlenip `tx` kanalıyla ana WM event loop'una iletilir, yanıt da
/// aynı kanal üzerinden (her istek için oluşturulan tek seferlik bir
/// `Sender<Response>` ile) geri alınır. Böylece X11 ile ilgili tüm state
/// mutasyonu tek bir thread'de (WM ana döngüsü) kalır.
pub fn start(socket_path: &str, tx: Sender<(Action, Sender<Response>)>) -> Result<()> {
    let _ = std::fs::remove_file(socket_path);
    let listener = UnixListener::bind(socket_path)?;
    tracing::info!("IPC socket dinleniyor: {socket_path}");

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let tx = tx.clone();
                std::thread::spawn(move || {
                    if let Err(err) = handle_client(stream, tx) {
                        tracing::warn!("IPC istemci hatası: {err:#}");
                    }
                });
            }
            Err(err) => tracing::warn!("IPC bağlantı hatası: {err}"),
        }
    }
    Ok(())
}

fn handle_client(stream: UnixStream, tx: Sender<(Action, Sender<Response>)>) -> Result<()> {
    let mut writer = stream.try_clone()?;
    let reader = BufReader::new(stream);
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let response = match serde_json::from_str::<Request>(&line) {
            Ok(req) => {
                let (resp_tx, resp_rx) = std::sync::mpsc::channel();
                if tx.send((req.action, resp_tx)).is_err() {
                    Response::err("WM ana döngüsüne ulaşılamadı")
                } else {
                    resp_rx
                        .recv()
                        .unwrap_or_else(|_| Response::err("yanıt alınamadı"))
                }
            }
            Err(err) => Response::err(format!("geçersiz komut: {err}")),
        };
        let mut out = serde_json::to_string(&response)?;
        out.push('\n');
        writer.write_all(out.as_bytes())?;
    }
    Ok(())
}
