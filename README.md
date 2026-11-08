# qwm

Rust ile yazılmış, X11 üzerinde çalışan, bspwm tarzı dinamik
binary-space-partitioning (BSP) tiling pencere yöneticisi.

> **Durum:** Bu repo, orijinal spesifikasyonun **Faz 0 (İskelet)** ve
> **Faz 1/3/4**'ten temel parçalarını içeren bir başlangıç noktasıdır:
> X11 bağlantısı + event loop, basit tek-ağaçlı BSP tiling, TOML config
> parse'ı, Unix socket IPC sunucusu ve `qwmctl` CLI'si çalışır durumda.
> Multi-monitor/dinamik workspace yönetimi, floating rules'un fiilen
> uygulanması, scratchpad'in WM tarafı, mouse move/resize, tam EWMH
> state senkronizasyonu ve dahili bar henüz **iskelet/stub**
> seviyesindedir — `qwm-core/src/wm.rs` içindeki `handle_action` ve
> `handle_event` fonksiyonları, kalan fazların ekleneceği yerdir.

## Mimari

```
qwm/
├── qwm-core/   # WM mantığı (kütüphane): x11, layout, config, ipc, ...
├── qwm/        # WM binary'si (qwm-core'u kullanır)
├── qwmctl/     # IPC CLI istemcisi (X11'den bağımsız)
└── docs/       # örnek config, .desktop dosyası
```

## Derleme

Bu ortamda ağ erişimi kapalı olduğu için bağımlılıklar indirilip derleme
doğrulanamadı. Kendi makinenizde:

```sh
cd qwm
cargo build --release
```

Gerekli sistem bağımlılığı yoktur (saf Rust + `x11rb`), ancak X11
geliştirme başlıklarının (`libx11-dev` vb.) kurulu olması genelde
sorun çıkarmaz çünkü `x11rb` XCB protokolünü soketten konuşur, C
kütüphanesine bağlanmaz.

Derleme sırasında dikkat edilmesi muhtemel noktalar:
- `x11rb` 0.13 API'si (örn. `ConnectionExt`, `atom_manager!` makrosu)
  sürüm güncellemeleriyle değişebilir; `Cargo.lock` oluşunca sabitlenir.
- `qwm-core/src/wm.rs` içindeki `create_window` çağrısındaki depth
  parametresi (`0` = `COPY_DEPTH_FROM_PARENT`) bazı x11rb sürümlerinde
  farklı bir sabitle ifade edilebilir; derleyici hata verirse
  `x11rb::COPY_DEPTH_FROM_PARENT` sabitini kullanın.

## Çalıştırma (geliştirme)

Gerçek oturumunuzu riske atmadan test etmek için `Xephyr` önerilir:

```sh
Xephyr -ac -screen 1280x800 :1 &
DISPLAY=:1 ./target/release/qwm &
DISPLAY=:1 alacritty &
DISPLAY=:1 ./target/release/qwmctl query --windows
```

## `.xinitrc` ile başlatma

```sh
exec qwm
```

## Display manager entegrasyonu

`docs/qwm.desktop` dosyasını `/usr/share/xsessions/qwm.desktop` olarak
kopyalayın; `qwm` binary'si `$PATH` içinde olmalı.

## Varsayılan keybinding'ler

Bkz. `docs/default-config.toml`. Özet:

| Tuş | Aksiyon |
|---|---|
| `Mod+Return` | terminal aç |
| `Mod+d` | rofi launcher |
| `Mod+q` | odaklı pencereyi kapat |
| `Mod+h/j/k/l` | odağı yönlendir |
| `Mod+Shift+h` | odaklı pencereyi batıdaki ile değiştir |
| `Mod+1..9` | workspace'e geç |
| `Mod+Shift+1..9` | pencereyi workspace'e taşı |
| `Mod+f` | floating aç/kapa |
| `Mod+m` | monocle aç/kapa |
| `` Mod+` `` | scratchpad "terminal" aç/kapa |
| `Mod+Shift+r` | config'i yeniden yükle |
| `Mod+Shift+q` | qwm'den çık |

## qwmctl örnekleri

```sh
qwmctl node -f west
qwmctl node -s west
qwmctl node -t floating
qwmctl desktop -f 3
qwmctl node -d 3
qwmctl config reload
qwmctl query --windows
qwmctl scratchpad toggle terminal
qwmctl quit
```

## Yol haritası

Spesifikasyonun 11. bölümündeki fazlara göre kalan işler:

- [x] Faz 0 — X11 bağlantısı, `SubstructureRedirect`, temel event loop
- [ ] Faz 1 — tam BSP tiling (preselect, manuel resize UI'si, auto-split yön algısı)
- [ ] Faz 2 — multi-monitor (RandR hot-plug) + gerçek dinamik workspace yönetimi
- [x] Faz 3 — TOML config + keybinding (temel), hot-reload altyapısı var, WM'e bağlanmadı
- [x] Faz 4 — IPC/qwmctl (temel komut seti)
- [ ] Faz 5 — tam EWMH/ICCCM (`_NET_WM_STRUT_PARTIAL` okuma, `WM_DELETE_WINDOW`, vb.)
- [ ] Faz 6 — floating rules'un fiilen uygulanması, scratchpad (WM tarafı), monocle, preselect
- [ ] Faz 7 — dahili bar, autostart (temel hali var), sinyal yönetimi, cilalama
