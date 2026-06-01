import logging
import signal
import sys
from typing import Any, Dict

import Xlib.X
import Xlib.error
import Xlib.protocol.event as xevent

from .state import QWMState, WindowState
from ..x11.display import XDisplay

logger = logging.getLogger("qwm.wm")


class WindowManager:
    """Central WM engine and event dispatcher."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = QWMState()
        self.display = XDisplay()  # $DISPLAY yoksa burada RuntimeError fırlatır

    # ------------------------------------------------------------------ #
    # Başlangıç                                                              #
    # ------------------------------------------------------------------ #

    def setup(self):
        """Perform initial setup before entering the event loop."""
        logger.info("XDisplay ayarlanıyor")
        self.display.setup()

        # Temiz kapatılma için sinyal yakalıyıcı
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Halihazırda açık olan pencereleri yönetim altına al
        self._adopt_existing_windows()

    def _handle_signal(self, signum, frame):
        """SIGINT / SIGTERM — döngüden çık."""
        logger.info(f"Sinyal alındı: {signum} — çıkılıyor")
        self.state.running = False

    def _adopt_existing_windows(self):
        """WM başlatıldığında zaten açık olan pencereleri al."""
        try:
            children = self.display.root.query_tree().children
            for child in children:
                try:
                    attrs = child.get_attributes()
                    # Mapped ve override_redirect olmayan pencereleri al
                    if attrs and attrs.map_state == Xlib.X.IsViewable and not attrs.override_redirect:
                        self._manage_window(child.id)
                except Exception:
                    pass  # Tek bir pencere hatası tümünü durdurmasın
        except Exception as e:
            logger.warning(f"Mevcut pencereler alınırken hata: {e}")

    # ------------------------------------------------------------------ #
    # Ana olay döngüsü                                                    #
    # ------------------------------------------------------------------ #

    def run(self):
        """Main event loop."""
        self.setup()
        logger.info("X11 olay döngüsü başlıyor")
        try:
            while self.state.running:
                event = self.display.next_event()
                if event is not None:
                    self.handle_event(event)
        except Xlib.error.ConnectionClosedError:
            logger.error("X sunucu bağlantısı kesildi")
        finally:
            self.cleanup()

    # ------------------------------------------------------------------ #
    # Olay yönlendirme                                                     #
    # ------------------------------------------------------------------ #

    def handle_event(self, event):
        """Dispatch X11 events to appropriate handlers."""
        etype = event.type
        handlers = {
            Xlib.X.MapRequest:       self._on_map_request,
            Xlib.X.DestroyNotify:    self._on_destroy_notify,
            Xlib.X.UnmapNotify:      self._on_unmap_notify,
            Xlib.X.ConfigureRequest: self._on_configure_request,
            Xlib.X.EnterNotify:      self._on_enter_notify,
        }
        handler = handlers.get(etype)
        if handler:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Olay işleme hatası (type={etype}): {e}")
        else:
            logger.debug(f"Bilinmeyen/işlenmemiş olay: type={etype}")

    # ------------------------------------------------------------------ #
    # Olay işleyicileri                                                   #
    # ------------------------------------------------------------------ #

    def _on_map_request(self, event):
        """Yeni pencere gösterilmek istiyor."""
        xid = event.window.id
        logger.info(f"MapRequest: xid=0x{xid:x}")
        self._manage_window(xid)
        event.window.map()
        self.display.flush()

    def _on_destroy_notify(self, event):
        """Pencere kapatıldı."""
        xid = event.window.id
        if xid in self.state.windows:
            del self.state.windows[xid]
            if self.state.active_window == xid:
                self.state.active_window = None
            logger.info(f"Pencere kaldırıldı: 0x{xid:x}")

    def _on_unmap_notify(self, event):
        """Pencere görünümden kaldırıldı."""
        xid = event.window.id
        logger.debug(f"UnmapNotify: xid=0x{xid:x}")

    def _on_configure_request(self, event):
        """Pencere konfigürasyon isteği — kabul et."""
        xid = event.window.id
        # Pencereyi istediği boyut/konumla yapılandır
        kwargs = {}
        if event.value_mask & Xlib.X.CWX:           kwargs["x"] = event.x
        if event.value_mask & Xlib.X.CWY:           kwargs["y"] = event.y
        if event.value_mask & Xlib.X.CWWidth:       kwargs["width"] = event.width
        if event.value_mask & Xlib.X.CWHeight:      kwargs["height"] = event.height
        if event.value_mask & Xlib.X.CWBorderWidth: kwargs["border_width"] = event.border_width
        if event.value_mask & Xlib.X.CWStackMode:   kwargs["stack_mode"] = event.stack_mode
        if kwargs:
            try:
                event.window.configure(**kwargs)
                self.display.flush()
            except Exception as e:
                logger.warning(f"ConfigureRequest başarısız (0x{xid:x}): {e}")

    def _on_enter_notify(self, event):
        """Fare pencereye girdi — focus-follows-mouse."""
        focus_model = self.config.get("general", {}).get("focus_model", "click")
        if focus_model == "sloppy":
            xid = event.window.id
            if xid in self.state.windows:
                try:
                    event.window.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
                    self.state.active_window = xid
                    self.display.flush()
                except Exception as e:
                    logger.warning(f"Focus ayarlanamadı (0x{xid:x}): {e}")

    # ------------------------------------------------------------------ #
    # Yardımcı metodlar                                                   #
    # ------------------------------------------------------------------ #

    def _manage_window(self, xid: int):
        """Pencereyi state'e kaydet."""
        if xid not in self.state.windows:
            self.state.windows[xid] = WindowState(
                xid=xid,
                workspace=self.state.active_workspace
            )
            logger.debug(f"Pencere yönetim altına alındı: 0x{xid:x}")

    def cleanup(self):
        """Clean up resources before exit."""
        logger.info("QWM kaynakları temizleniyor")
        self.display.cleanup()

