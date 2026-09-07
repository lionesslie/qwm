# QWM (Quick Window Manager)

Python 3.11+ ile yazılmış, python-xlib üzerine kurulu, NVIDIA ekran kartlarına
özel optimizasyonlar içeren bir X11 tiling window manager.

## Özellikler

- Layout modları: `master_stack`, `grid`, `spiral`, `monocle`, `floating`
- EWMH/ICCCM desteği (rofi, taskbar gibi araçlarla uyumlu)
- `config.qc` (TOML sözdizimi) ile canlı (hot-reload) yapılandırma
- picom entegrasyonu: rounded corners, blur, shadow, animasyonlar
- WM taraflı ease-out-cubic animasyonlu pencere taşıma/boyutlandırma
- NVIDIA GPU tespiti ve optimizasyon (force composition pipeline, PRIME offload)
- Game mode: fullscreen tespitinde compositor bypass, animasyon kapatma, CPU governor
- Çoklu monitör desteği (Xrandr)
- Unix socket üzerinden `qwmctl` CLI kontrolü
- Opsiyonel minimal status bar
- Crash recovery (otomatik yeniden başlatma)

## Kurulum

```bash
git clone <bu-repo> qwm
cd qwm
sudo python3 installer/install.py
```

Kurulum betiği:

1. Dağıtımınızı tespit eder (Arch/Debian/Ubuntu/Fedora/openSUSE)
2. Gerekli sistem paketlerini kurar (`python-xlib`, `picom`, `git`, derleyici araçları)
3. `alacritty`, `rofi`, `feh` paketlerini kurar; depoda yoksa kaynak koddan derler
4. NVIDIA sürücüsünü tespit eder (kurulu değilse sadece bilgilendirir, otomatik kurmaz)
5. `qwm` paketini `/opt/qwm` altına kopyalar
6. `~/.config/qwm/config.qc` varsayılan yapılandırmasını oluşturur
7. `/usr/share/xsessions/qwm.desktop` dosyasını oluşturarak GDM/SDDM/LightDM'de
   "QWM" oturumunu seçilebilir hale getirir
8. `/usr/bin/qwm-start` başlatma betiğini ve `/usr/local/bin/qwmctl` CLI aracını kurar
9. rofi teması ve alacritty renk paletini qwm ile senkronize eder

Root gerektirmeyen sadece kullanıcı dizinine yapılan adımlar (config kopyalama vb.)
sudo olmadan da çalışır; sistem paketleri ve `/opt`, `/usr` altındaki dosyalar için
root gerekir.

Kurulumu geri almak için:

```bash
sudo python3 installer/install.py --uninstall
```

`~/.config/qwm` dizini kullanıcı verisi olduğu için uninstall sırasında silinmez.

### Geliştirme / test kurulumu

Sistem genelinde kurulum yapmadan sadece Python bağımlılıklarını kurup
depodan çalıştırmak için:

```bash
pip install -r requirements.txt --break-system-packages
python3 -m qwm.main --config ./config.qc
```

Bu şekilde çalıştırmak için `DISPLAY` ortam değişkeninin tanımlı olduğu bir
X oturumu (gerçek oturum, iç içe Xephyr, veya Xvfb) gereklidir.

## Kullanım

### Varsayılan kısayollar

| Kısayol | Eylem |
|---|---|
| `Super+Return` | Terminal aç |
| `Super+D` | Uygulama başlatıcı (rofi) |
| `Super+Q` | Odaklı pencereyi kapat |
| `Super+F` | Tam ekran aç/kapat |
| `Super+Shift+Space` | Floating aç/kapat |
| `Super+Space` | Layout değiştir (master_stack → grid → spiral → monocle) |
| `Super+H/J/K/L` | Odak değiştir |
| `Super+Shift+H/J/K/L` | Pencereyi taşı |
| `Super+Equal` / `Super+Minus` | Master oranını büyült/küçült |
| `Super+1..9` | Workspace'e geç |
| `Super+Shift+1..9` | Pencereyi workspace'e taşı |
| `Super+Shift+R` | Config'i yeniden yükle |
| `Super+Shift+Q` | qwm'i kapat |
| `Super+\`` | Scratchpad terminal aç/gizle |
| `Super+Shift+S` | Ekran görüntüsü |
| `Super+L` | Ekranı kilitle |

Tüm kısayollar `~/.config/qwm/config.qc` içindeki `[keybinds]` tablosundan
özelleştirilebilir.

Fare: `Super+SolTık` pencere taşır, `Super+SağTık` boyutlandırır, orta tık
floating durumunu değiştirir.

### Yapılandırma

`~/.config/qwm/config.qc` saf TOML sözdizimi kullanır (uzantı `.qc`).
Dosya değiştirildiğinde 300ms sonra otomatik olarak, pencereler kapatılmadan
yeniden yüklenir: renkler, gap, border, kısayollar ve animasyon ayarları
canlı olarak güncellenir.

Örnek bölümler için depo kökündeki `config.qc` dosyasına bakın.

Pencere kuralları `[[rules]]` tablo dizisiyle tanımlanır:

```toml
[[rules]]
class = "Rofi"
floating = true

[[rules]]
class = "mpv"
workspace = 3
```

### qwmctl

```bash
qwmctl reload            # config.qc'yi yeniden yükle
qwmctl restart           # qwm sürecini yeniden başlat
qwmctl kill-focused      # odaklı pencereyi kapat
qwmctl workspace 3       # 3. workspace'e geç
qwmctl layout grid       # aktif workspace'in layout'unu değiştir
```

### NVIDIA optimizasyonu

`[nvidia]` bölümü `auto_optimize = true` olduğunda qwm başlangıçta
`nvidia-smi` ile GPU'yu tespit eder, picom'u `backend = "glx"`,
`vsync = true`, `glx-no-stencil = true` ayarlarıyla başlatır ve mevcut
metamode'da `ForceFullCompositionPipeline` eksikse öneri loglar (otomatik
uygulamak `nvidia-settings --assign` çağrısı yapar ve sudo gerektirebilir).

PRIME/Optimus sistemlerde game mode etkinken oyun prosesleri
`__NV_PRIME_RENDER_OFFLOAD=1` ve `__GLX_VENDOR_LIBRARY_NAME=nvidia`
ortam değişkenleriyle başlatılabilir (`qwm.gpu.nvidia.env_for_prime_offload`).

### Game mode

Bir pencere `_NET_WM_STATE_FULLSCREEN` durumuna geçtiğinde:

- picom compositor bypass edilir (unredirect-fullscreen)
- Animasyonlar otomatik kapanır
- CPU governor `performance` moduna alınır (izin varsa, `cpupower` gerekir)
- Sistem `gamemoded` kuruluysa D-Bus üzerinden entegre olunur

Fullscreen kapandığında her şey eski haline döner.

## Proje yapısı

```
qwm/
├── qwm/
│   ├── core/       ana event loop, layout, window, workspace, ewmh
│   ├── config/     config.qc parse/validate/watch
│   ├── render/      animasyon, compositor, decoration
│   ├── input/       keybind ve mouse yönetimi
│   ├── gpu/         nvidia optimizasyonu
│   ├── gamemode/    oyun modu
│   ├── bar/         status bar
│   ├── ipc/         unix socket sunucusu
│   └── main.py      giriş noktası
├── installer/       kurulum betikleri
├── config.qc        varsayılan yapılandırma
├── qwmctl           CLI aracı
└── requirements.txt
```

## Bilinen sınırlamalar

- picom'un `backend = "glx"` ayarı gerçek bir GLX/GPU ortamı gerektirir;
  sanal/headless ortamlarda (Xvfb gibi) compositor GPU hızlandırması
  bulamadığından başlatılamayabilir.
- `nvidia-settings --assign` ile otomatik metamode değişikliği çoğu
  sistemde root/sudo gerektirir; qwm bunu varsayılan olarak sadece önerir,
  otomatik uygulamaz (`dry_run=True`).
- Ekran kilitleme `i3lock` veya `xlock` varlığına bağlıdır; hiçbiri kurulu
  değilse `Super+L` bir şey yapmaz.
