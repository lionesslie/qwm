use std::collections::HashMap;
use x11rb::protocol::xproto::Window;

/// Birden fazla adlandırılmış scratchpad slotunu (bkz. `[[scratchpad]]`
/// config bölümü) ve her birinin o anki görünürlük durumunu tutar.
#[derive(Debug, Default)]
pub struct ScratchpadState {
    slots: HashMap<String, Slot>,
}

#[derive(Debug, Clone, Copy)]
struct Slot {
    window: Window,
    visible: bool,
}

impl ScratchpadState {
    /// Scratchpad komutuyla başlatılan pencere map olduğunda (MapRequest)
    /// çağrılır; pencereyi ilgili isimli slota bağlar.
    pub fn register(&mut self, name: &str, window: Window) {
        self.slots.insert(
            name.to_string(),
            Slot {
                window,
                visible: false,
            },
        );
    }

    /// Slotun görünürlüğünü tersine çevirir ve (pencere, yeni_görünürlük)
    /// döner; slot henüz hiç başlatılmadıysa `None` döner (WM bu durumda
    /// config'deki `command`i çalıştırıp pencereyi ilk kez oluşturmalı).
    pub fn toggle(&mut self, name: &str) -> Option<(Window, bool)> {
        let slot = self.slots.get_mut(name)?;
        slot.visible = !slot.visible;
        Some((slot.window, slot.visible))
    }

    pub fn contains_window(&self, window: Window) -> bool {
        self.slots.values().any(|s| s.window == window)
    }
}
