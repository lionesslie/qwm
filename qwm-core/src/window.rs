use x11rb::protocol::xproto::Window;

/// qwm tarafından yönetilen tek bir pencerenin durumu.
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
    pub workspace: usize,
    pub class: String,
    pub instance: String,
    pub title: String,
}

impl Client {
    pub fn new(window: Window, workspace: usize) -> Self {
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
            workspace,
            class: String::new(),
            instance: String::new(),
            title: String::new(),
        }
    }
}
