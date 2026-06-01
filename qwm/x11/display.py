import logging
import os
import Xlib.display
import Xlib.X
import Xlib.error
import Xlib.protocol.event

logger = logging.getLogger("qwm.x11.display")

class XDisplay:
    """Wrapper for the X server connection and root window."""

    def __init__(self):
        # python-xlib bağlantı hatalarını farklı exception'larla atar;
        # hepsini yakala.
        display_name = os.environ.get("DISPLAY", "")
        if not display_name:
            logger.critical("$DISPLAY değişkeni ayarlanmamış! X11 oturumu başlatılmış mı?")
            raise RuntimeError("$DISPLAY not set")
        try:
            self.display = Xlib.display.Display()
            self.screen = self.display.screen()
            self.root = self.screen.root
            self._closed = False
            logger.info(f"X Display'e bağlanıldı: {self.display.get_display_name()}")
        except Xlib.error.DisplayConnectionError as e:
            logger.critical(f"X display bağlantısı başarısız: {e}")
            raise
        except Exception as e:
            logger.critical(f"X display açılırken beklenmeyen hata: {e}")
            raise

    def setup(self):
        """Initialize root window properties and event masks."""
        try:
            self.root.change_attributes(
                event_mask=(
                    Xlib.X.SubstructureRedirectMask
                    | Xlib.X.SubstructureNotifyMask
                    | Xlib.X.EnterWindowMask
                    | Xlib.X.LeaveWindowMask
                    | Xlib.X.StructureNotifyMask
                    | Xlib.X.PropertyChangeMask
                )
            )
            # flush yerine sync: sunucunun eventi işlediğini garantile.
            # BadAccess hatası burada gelir; eğer başka WM çalışıyorsa.
            self.display.sync()
            logger.info("Root pencere olay maskesi ayarlandı")
        except Xlib.error.BadAccess:
            logger.critical(
                "SubstructureRedirectMask alınamadı! "
                "Başka bir window manager zaten çalışıyor."
            )
            raise RuntimeError("Başka bir WM zaten çalışıyor.")

    def next_event(self):
        """Fetch the next X11 event. Returns None on recoverable error."""
        try:
            return self.display.next_event()
        except Xlib.error.ConnectionClosedError:
            logger.error("X sunucu bağlantısı kapatıldı")
            raise  # fatal — üste ilet
        except Exception as e:
            logger.error(f"Event okuma hatası: {e}")
            return None

    def flush(self):
        """Flush the X11 command buffer."""
        if not self._closed:
            self.display.flush()

    def cleanup(self):
        """Close connection."""
        if not self._closed:
            self._closed = True
            try:
                self.display.close()
            except Exception:
                pass
