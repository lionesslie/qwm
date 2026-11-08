//! qwm-core: qwm pencere yöneticisinin ana mantığını barındıran kütüphane.
//!
//! Bu crate WM binary'si (`qwm`) tarafından kullanılır. `qwmctl` CLI'si bu
//! crate'e bağımlı DEĞİLDİR; yalnızca IPC protokolü (JSON) üzerinden
//! konuşur, böylece istemci tarafı X11'den tamamen bağımsız kalır.

pub mod bar;
pub mod config;
pub mod ipc;
pub mod keybind;
pub mod layout;
pub mod monitor;
pub mod rules;
pub mod scratchpad;
pub mod window;
pub mod wm;
pub mod workspace;
pub mod x11;
