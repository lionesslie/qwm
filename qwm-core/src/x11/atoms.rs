//! EWMH/ICCCM atom tanımları.
//!
//! `x11rb::atom_manager!` makrosu, X sunucusuna tek seferde `InternAtom`
//! istekleri gönderip yanıtları toplu halde alan bir `Atoms` struct'ı
//! üretir. Spesifikasyonun 10. bölümünde listelenen atomların tamamı
//! burada tanımlanır; yeni bir EWMH/ICCCM özelliği eklenecekse önce
//! buraya atomu eklemek gerekir.

use x11rb::atom_manager;

atom_manager! {
    pub Atoms: AtomsCookie {
        // --- Root window properties (WM -> dış dünya) ---
        _NET_SUPPORTED,
        _NET_CLIENT_LIST,
        _NET_CLIENT_LIST_STACKING,
        _NET_NUMBER_OF_DESKTOPS,
        _NET_DESKTOP_NAMES,
        _NET_CURRENT_DESKTOP,
        _NET_ACTIVE_WINDOW,
        _NET_WORKAREA,
        _NET_SUPPORTING_WM_CHECK,
        _NET_DESKTOP_GEOMETRY,
        _NET_DESKTOP_VIEWPORT,

        // --- Window properties (WM <-> client) ---
        _NET_WM_NAME,
        _NET_WM_DESKTOP,
        _NET_WM_STATE,
        _NET_WM_STATE_FULLSCREEN,
        _NET_WM_STATE_MAXIMIZED_VERT,
        _NET_WM_STATE_MAXIMIZED_HORZ,
        _NET_WM_STATE_STICKY,
        _NET_WM_STATE_DEMANDS_ATTENTION,
        _NET_WM_WINDOW_TYPE,
        _NET_WM_WINDOW_TYPE_DIALOG,
        _NET_WM_WINDOW_TYPE_DOCK,
        _NET_WM_WINDOW_TYPE_UTILITY,
        _NET_WM_WINDOW_TYPE_SPLASH,
        _NET_WM_WINDOW_TYPE_NORMAL,
        _NET_WM_STRUT,
        _NET_WM_STRUT_PARTIAL,

        // --- ICCCM ---
        WM_PROTOCOLS,
        WM_DELETE_WINDOW,
        WM_STATE,
        WM_CLASS,
        WM_TRANSIENT_FOR,

        UTF8_STRING,
    }
}
