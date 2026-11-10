//! Keybinding string parse'ı ve `Action` enum'u.
//!
//! `Action`, hem WM içi keybinding'lerin hem de `qwmctl`'den gelen IPC
//! komutlarının ortak temsilidir (spesifikasyon bölüm 8: "keybinding'ler
//! aslında dahili olarak qwmctl ile aynı IPC komutlarını tetikler").

use crate::config::schema::Keybind;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Modifiers {
    /// Config'deki `input.mod_key` (genelde Super/Win tuşu).
    pub mod_mask: bool,
    pub shift: bool,
    pub ctrl: bool,
    pub alt: bool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ParsedKeybind {
    pub mods: Modifiers,
    pub keysym: u32,
}

/// `"Mod+Shift+h"` gibi bir string'i modifier'lara ve X11 keysym değerine
/// ayırır. Şimdilik yalnızca ASCII harf/rakamlar ve birkaç yaygın özel
/// tuş (`Return`, `grave`, `space`, `Tab`, `Escape`) destekleniyor; daha
/// eksiksiz bir tablo için ileride `xkbcommon` entegrasyonu düşünülebilir.
pub fn parse_keys(spec: &str) -> Option<ParsedKeybind> {
    let parts: Vec<&str> = spec.split('+').collect();
    if parts.is_empty() {
        return None;
    }
    let (modifiers, key) = parts.split_at(parts.len() - 1);
    let key = key.first()?;

    let mut mods = Modifiers::default();
    for m in modifiers {
        match *m {
            "Mod" | "Super" => mods.mod_mask = true,
            "Shift" => mods.shift = true,
            "Ctrl" | "Control" => mods.ctrl = true,
            "Alt" => mods.alt = true,
            _ => {}
        }
    }

    keysym_for(key).map(|keysym| ParsedKeybind { mods, keysym })
}

fn keysym_for(name: &str) -> Option<u32> {
    if name.chars().count() == 1 {
        let c = name.chars().next().unwrap();
        if c.is_ascii_alphanumeric() {
            // ASCII harf/rakam keysym'leri karakter koduyla birebir aynıdır.
            return Some(c.to_ascii_lowercase() as u32);
        }
    }
    let sym = match name {
        "Return" => 0xff0d,
        "grave" => 0x0060,
        "space" => 0x0020,
        "Tab" => 0xff09,
        "Escape" => 0xff1b,
        _ => return None,
    };
    Some(sym)
}

/// WM'in anladığı tüm aksiyonlar. `qwmctl` bu enum'u JSON olarak
/// serileştirip IPC socket'ine gönderir (bkz. `ipc::protocol`).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "cmd", content = "args", rename_all = "snake_case")]
pub enum Action {
    Spawn { command: String },
    NodeClose,
    Focus { direction: String },
    NodeSwap { direction: String },
    NodeResize { direction: String, amount: i32 },
    WorkspaceSwitch { target: String },
    NodeToWorkspace { target: String },
    ToggleFloating,
    ToggleMonocle,
    ToggleFullscreen,
    ScratchpadToggle { name: String },
    ReloadConfig,
    Quit,
    Query { windows: bool },
}

/// Config'deki `[[keybind]]` girdisini, WM'in çalışma zamanı `Action`
/// enum'una çevirir. `qwmctl`'den gelen JSON komutlarla aynı hedefe
/// (`wm::Wm::handle_action`) gider; yani bir WM-içi keybinding ile aynı
/// işi yapan bir `qwmctl` çağrısı davranışsal olarak birebir aynıdır.
pub fn action_from_keybind(kb: &Keybind) -> Option<Action> {
    match kb.action.as_str() {
        "spawn" => Some(Action::Spawn {
            command: kb.command.clone()?,
        }),
        "node_close" => Some(Action::NodeClose),
        "focus" => Some(Action::Focus {
            direction: kb.direction.clone()?,
        }),
        "node_swap" => Some(Action::NodeSwap {
            direction: kb.direction.clone()?,
        }),
        "workspace_switch" => Some(Action::WorkspaceSwitch {
            target: toml_value_to_string(kb.target.as_ref()?),
        }),
        "node_to_workspace" => Some(Action::NodeToWorkspace {
            target: toml_value_to_string(kb.target.as_ref()?),
        }),
        "toggle_floating" => Some(Action::ToggleFloating),
        "toggle_monocle" => Some(Action::ToggleMonocle),
        "toggle_fullscreen" => Some(Action::ToggleFullscreen),
        "scratchpad_toggle" => Some(Action::ScratchpadToggle {
            name: kb.name.clone()?,
        }),
        "reload_config" => Some(Action::ReloadConfig),
        "quit" => Some(Action::Quit),
        _ => None,
    }
}

/// Bir `Action`'i, `qwmctl` CLI'sinin kabul edecegi tam komut satirina
/// cevirir. `sxhkd` gibi harici bir hotkey daemon'u icin komut uretmekte
/// kullanilir (bkz. `qwm --export-sxhkd`); boylece `[[keybind]]` listesi,
/// WM-ici grab olmasa da tek kaynak (single source of truth) olmaya devam
/// eder. `Query` gibi sxhkd icin anlamsiz aksiyonlar icin `None` doner.
pub fn action_to_qwmctl_command(action: &Action) -> Option<String> {
    Some(match action {
        Action::Spawn { command } => return Some(command.clone()),
        Action::NodeClose => "qwmctl node -c".to_string(),
        Action::Focus { direction } => format!("qwmctl node -f {direction}"),
        Action::NodeSwap { direction } => format!("qwmctl node -s {direction}"),
        Action::NodeResize { direction, amount } => {
            format!("qwmctl node --resize {direction}:{amount}")
        }
        Action::WorkspaceSwitch { target } => format!("qwmctl desktop -f {target}"),
        Action::NodeToWorkspace { target } => format!("qwmctl node -d {target}"),
        Action::ToggleFloating => "qwmctl node -t floating".to_string(),
        Action::ToggleMonocle => "qwmctl node -t monocle".to_string(),
        Action::ToggleFullscreen => "qwmctl node -t fullscreen".to_string(),
        Action::ScratchpadToggle { name } => format!("qwmctl scratchpad toggle {name}"),
        Action::ReloadConfig => "qwmctl config reload".to_string(),
        Action::Quit => "qwmctl quit".to_string(),
        Action::Query { .. } => return None,
    })
}

/// `[[mousebind]]` config girdilerinin aksiyonu: `move`/`resize` floating
/// pencereyi surukler (tiled ise once floating'e cikarir), `focus` ise
/// yalnizca tiklanan pencereye odaklanir.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MouseAction {
    Move,
    Resize,
    Focus,
}

pub fn mouse_action_from_str(s: &str) -> Option<MouseAction> {
    match s {
        "move" => Some(MouseAction::Move),
        "resize" => Some(MouseAction::Resize),
        "focus" => Some(MouseAction::Focus),
        _ => None,
    }
}

/// `"Mod+Button1"` gibi bir string'i modifier'lara ve buton numarasina
/// (1=sol, 2=orta, 3=sag) ayirir.
pub fn parse_mouse_keys(spec: &str) -> Option<(Modifiers, u8)> {
    let parts: Vec<&str> = spec.split('+').collect();
    if parts.is_empty() {
        return None;
    }
    let (modifiers, button) = parts.split_at(parts.len() - 1);
    let button = button.first()?;

    let mut mods = Modifiers::default();
    for m in modifiers {
        match *m {
            "Mod" | "Super" => mods.mod_mask = true,
            "Shift" => mods.shift = true,
            "Ctrl" | "Control" => mods.ctrl = true,
            "Alt" => mods.alt = true,
            _ => {}
        }
    }

    let n: u8 = button.strip_prefix("Button")?.parse().ok()?;
    Some((mods, n))
}

fn toml_value_to_string(v: &toml::Value) -> String {
    match v {
        toml::Value::Integer(n) => n.to_string(),
        toml::Value::String(s) => s.clone(),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_modifiers_and_key() {
        let parsed = parse_keys("Mod+Shift+h").unwrap();
        assert!(parsed.mods.mod_mask);
        assert!(parsed.mods.shift);
        assert!(!parsed.mods.ctrl);
        assert_eq!(parsed.keysym, 'h' as u32);
    }

    #[test]
    fn parses_named_key() {
        let parsed = parse_keys("Mod+Return").unwrap();
        assert_eq!(parsed.keysym, 0xff0d);
    }
}
