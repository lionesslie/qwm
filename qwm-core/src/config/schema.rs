//! `qwm.toml` şemasının serde karşılığı. Spesifikasyonun 7. bölümündeki
//! örnek dosyayla birebir eşleşir. Her alt-struct kendi makul
//! varsayılanlarını tanımlar ki config dosyasında yalnızca değiştirmek
//! istenen alanlar yazılabilsin (`#[serde(default)]`).

use serde::Deserialize;

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Config {
    pub general: General,
    pub gaps: Gaps,
    pub border: Border,
    pub workspaces: Workspaces,
    pub monitors: Monitors,
    pub input: Input,
    #[serde(rename = "keybind")]
    pub keybinds: Vec<Keybind>,
    #[serde(rename = "mousebind")]
    pub mousebinds: Vec<MouseBind>,
    #[serde(rename = "rule")]
    pub rules: Vec<Rule>,
    #[serde(rename = "scratchpad")]
    pub scratchpads: Vec<Scratchpad>,
    #[serde(rename = "workspace_override")]
    pub workspace_overrides: Vec<WorkspaceOverride>,
    pub autostart: Autostart,
    pub bar: Bar,
    pub external_bar: ExternalBar,
    pub ipc: Ipc,
    pub log: Log,
}

impl Default for Config {
    fn default() -> Self {
        // Boş bir TOML belgesi her zaman geçerlidir ve her alt-struct'ın
        // kendi `Default` implementasyonunu tetikler; tüm varsayılanları
        // tek bir yerde (burada) tutmaktansa, "boş config = varsayılan
        // config" eşdeğerliğini garanti eder.
        toml::from_str("").expect("boş config her zaman geçerli olmalı")
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct General {
    pub split_ratio: f32,
    pub auto_split_direction: String,
    pub focus_follows_mouse: bool,
    pub click_to_focus: bool,
    pub new_window_takes_focus: bool,
    pub default_layout: String,
}

impl Default for General {
    fn default() -> Self {
        Self {
            split_ratio: 0.5,
            auto_split_direction: "auto".into(),
            focus_follows_mouse: false,
            click_to_focus: true,
            new_window_takes_focus: true,
            default_layout: "bsp".into(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Gaps {
    pub inner: i32,
    pub outer_top: i32,
    pub outer_bottom: i32,
    pub outer_left: i32,
    pub outer_right: i32,
    pub smart_gaps: bool,
}

impl Default for Gaps {
    fn default() -> Self {
        Self {
            inner: 8,
            outer_top: 12,
            outer_bottom: 12,
            outer_left: 12,
            outer_right: 12,
            smart_gaps: true,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Border {
    pub width: u16,
    pub focused_color: String,
    pub unfocused_color: String,
    pub urgent_color: String,
    pub radius: u16,
}

impl Default for Border {
    fn default() -> Self {
        Self {
            width: 2,
            focused_color: "#89b4fa".into(),
            unfocused_color: "#45475a".into(),
            urgent_color: "#f38ba8".into(),
            radius: 0,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Workspaces {
    pub mode: String,
    pub static_count: u32,
    pub names: Vec<String>,
}

impl Default for Workspaces {
    fn default() -> Self {
        Self {
            mode: "dynamic".into(),
            static_count: 10,
            names: Vec::new(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Monitors {
    pub on_connect: String,
    pub on_disconnect: String,
}

impl Default for Monitors {
    fn default() -> Self {
        Self {
            on_connect: "assign_new_workspace".into(),
            on_disconnect: "merge".into(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Input {
    pub mod_key: String,
    pub keybinding_style: String,
}

impl Default for Input {
    fn default() -> Self {
        Self {
            mod_key: "Super".into(),
            keybinding_style: "custom".into(),
        }
    }
}

/// `target` hem workspace numarası (`1`) hem de ismi (`"web"`) olabildiği
/// için ham `toml::Value` olarak tutulup kullanım anında çözümlenir.
#[derive(Debug, Deserialize, Clone)]
pub struct Keybind {
    pub keys: String,
    pub action: String,
    #[serde(default)]
    pub command: Option<String>,
    #[serde(default)]
    pub direction: Option<String>,
    #[serde(default)]
    pub target: Option<toml::Value>,
    #[serde(default)]
    pub name: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct MouseBind {
    pub button: String,
    pub action: String,
}

#[derive(Debug, Deserialize, Clone, Default)]
pub struct Rule {
    #[serde(default)]
    pub class: Option<String>,
    #[serde(default)]
    pub instance: Option<String>,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub floating: bool,
    #[serde(default)]
    pub sticky: bool,
    #[serde(default)]
    pub always_on_top: bool,
    #[serde(default)]
    pub center: bool,
    #[serde(default)]
    pub width: Option<u32>,
    #[serde(default)]
    pub height: Option<u32>,
    #[serde(default)]
    pub workspace: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Scratchpad {
    pub name: String,
    pub command: String,
    pub match_class: String,
    #[serde(default = "default_scratchpad_ratio")]
    pub width: f32,
    #[serde(default = "default_scratchpad_ratio")]
    pub height: f32,
    #[serde(default)]
    pub center: bool,
}

fn default_scratchpad_ratio() -> f32 {
    0.6
}

#[derive(Debug, Deserialize, Clone)]
pub struct WorkspaceOverride {
    pub name: String,
    #[serde(default)]
    pub layout: Option<String>,
    #[serde(default)]
    pub inner_gap: Option<i32>,
}

#[derive(Debug, Deserialize, Clone, Default)]
#[serde(default)]
pub struct Autostart {
    pub commands: Vec<String>,
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Bar {
    pub enabled: bool,
    pub position: String,
    pub height: u16,
    pub font: String,
    pub background: String,
    pub foreground: String,
    pub show_workspaces: bool,
    pub show_window_title: bool,
    pub modules_right: Vec<String>,
}

impl Default for Bar {
    fn default() -> Self {
        Self {
            enabled: false,
            position: "top".into(),
            height: 24,
            font: "monospace 10".into(),
            background: "#1e1e2e".into(),
            foreground: "#cdd6f4".into(),
            show_workspaces: true,
            show_window_title: true,
            modules_right: vec!["clock".into()],
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct ExternalBar {
    pub enabled: bool,
}

impl Default for ExternalBar {
    fn default() -> Self {
        Self { enabled: true }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Ipc {
    pub socket_path: String,
}

impl Default for Ipc {
    fn default() -> Self {
        Self {
            socket_path: "/tmp/qwm.sock".into(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Log {
    pub level: String,
    pub file: String,
}

impl Default for Log {
    fn default() -> Self {
        Self {
            level: "info".into(),
            file: "~/.local/share/qwm/qwm.log".into(),
        }
    }
}
