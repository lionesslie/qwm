use x11rb::protocol::xproto::Window;

/// qwm tarafindan yonetilen tek bir pencerenin durumu.
#[derive(Debug, Clone)]
pub struct Client {
    pub window: Window,
    pub floating: bool,
    pub fullscreen: bool,
    pub sticky: bool,
    pub urgent: bool,
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
    /// `Wm::monitors` icindeki index.
    pub monitor: usize,
    /// Ilgili monitordeki `MonitorState::workspaces` icindeki index.
    /// Dikkat: `prune_empty_workspaces` workspace listesini sikistirdiginda
    /// bu alan da WM tarafindan yeniden eslenir (bkz. `wm.rs`).
    pub workspace: usize,
    /// `Some(name)` ise bu pencere bir scratchpad slotuna baglidir ve BSP
    /// agacinin disinda tutulur.
    pub scratchpad: Option<String>,
    pub class: String,
    pub instance: String,
    pub title: String,
    /// `WM_NORMAL_HINTS`'ten (ICCCM) okunan minimum boyut; relayout
    /// sırasında hesaplanan dikdörtgen bu değerin altına düşürülmez.
    pub min_width: Option<u32>,
    pub min_height: Option<u32>,
}

impl Client {
    pub fn new(window: Window, monitor: usize, workspace: usize) -> Self {
        Self {
            window,
            floating: false,
            fullscreen: false,
            sticky: false,
            urgent: false,
            x: 0,
            y: 0,
            width: 0,
            height: 0,
            monitor,
            workspace,
            scratchpad: None,
            class: String::new(),
            instance: String::new(),
            title: String::new(),
            min_width: None,
            min_height: None,
        }
    }
}
