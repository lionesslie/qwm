//! `qwmctl` <-> `qwm` arasındaki satır-bazlı (newline-delimited) JSON
//! protokolü. Her istek `{"cmd": "...", "args": {...}}` biçimindedir ve
//! doğrudan `keybind::Action`'a karşılık gelir; her yanıt
//! `{"status": "ok"|"error", "data": ...}` biçimindedir.

use crate::keybind::Action;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct Request {
    #[serde(flatten)]
    pub action: Action,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Response {
    pub status: String,
    pub data: Option<serde_json::Value>,
}

impl Response {
    pub fn ok(data: Option<serde_json::Value>) -> Self {
        Self {
            status: "ok".into(),
            data,
        }
    }

    pub fn err(message: impl Into<String>) -> Self {
        Self {
            status: "error".into(),
            data: Some(serde_json::json!({ "message": message.into() })),
        }
    }
}
