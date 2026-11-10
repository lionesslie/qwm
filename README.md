# qwm

**Rust ile yazılmış, X11 üzerinde çalışan, [bspwm](https://github.com/baskerville/bspwm)
tarzı dinamik binary-space-partitioning (BSP) tiling pencere yöneticisi.**

![license](https://img.shields.io/badge/license-MIT-blue.svg)
![rust](https://img.shields.io/badge/rust-stable-orange.svg)
![status](https://img.shields.io/badge/status-work--in--progress-yellow.svg)

Mekanizma WM'de, politika config'de ve CLI'da: `qwm` arka planda çalışan ince
bir tiling motorudur, tüm kontrol `qwmctl` adlı ayrı bir CLI ile (bspwm'deki
`bspc` gibi) Unix socket üzerinden yapılır. Klavye kısayolları da bspwm'in
kendi felsefesine uyarak `sxhkd`'ye bırakılmıştır — qwm `[[keybind]]`
listesinden otomatik bir `sxhkdrc` üretir, tuşları kendisi gripli-emez.

> ⚠️ **Durum:** Aktif geliştirme aşamasında. Çekirdek tiling,
> multi-monitor, config/hot-reload, IPC/`qwmctl`, floating rules,
> scratchpad, temel EWMH/ICCCM uyumluluğu, sinyal yönetimi, mouse
> move/resize ve dahili bar çalışır durumda; asıl eksik preselect ve
> monitör hot-plug. Ayrıntılı durum için aşağıdaki
> [Yol haritası](#yol-haritası) bölümüne bakın. **Bu kod bu ortamda
> derlenip çalıştırılarak doğrulanamadı** — ilk derlemede küçük API
> uyumsuzlukları olasıdır, bkz. [Bilinen riskler](#bilinen-riskler).

## İçindekiler

- [Özellikler](#özellikler)
- [Mimari](#mimari)
- [Kurulum](#kurulum)
- [Hızlı başlangıç](#hızlı-başlangıç)
- [Yapılandırma](#yapılandırma)
- [Keybinding'ler: sxhkd](#keybindingler-sxhkd)
- [qwmctl](#qwmctl)
- [Display manager entegrasyonu](#display-manager-entegrasyonu)
- [Geliştirme](#geliştirme)
- [Bilinen riskler](#bilinen-riskler)
- [Yol haritası](#yol-haritası)
- [Katkıda bulunma](#katkıda-bulunma)
- [Lisans](#lisans)

## Özellikler

- **Dinamik BSP tiling** — split/swap/resize/close, bspwm'e benzer bir
  ikili ağaç modeli
- **Multi-monitor** — RandR ile monitör algılama, her monitörde bağımsız
  workspace seti
- **Dinamik workspace yönetimi** — boş workspace'ler otomatik silinir,
  gerektiğinde otomatik oluşturulur
- **TOML config + hot-reload** — `~/.config/qwm/qwm.toml`, `reload_config`
  komutuyla anında uygulanır
- **IPC / `qwmctl`** — tüm WM işlevlerine Unix socket üzerinden erişim,
  `query --windows` ile scriptlenebilir çıktı
- **Keybinding'ler `sxhkd` ile** — qwm kendisi `XGrabKey` yapmaz (bspwm'in
  felsefesine uyarak: mekanizma WM'de, tuş dinleme ayrı bir daemon'da);
  `qwm --export-sxhkd` komutu `qwm.toml`'daki `[[keybind]]` listesinden
  doğrudan bir `sxhkdrc` üretir, böylece tek bir config dosyası yeterli olur
- **Floating window rules** — class/instance/title regex eşleştirme,
  boyut/konum/merkezleme, workspace atama
- **Scratchpad** — adlandırılmış, toggle edilebilir gizli pencereler
- **Monocle & fullscreen** modları
- **Mouse move/resize** — `[[mousebind]]` ile floating pencereleri
  sürükleyerek taşıma/boyutlandırma; tiled bir pencere sürüklenirse
  (Move) otomatik floating'e çıkar, Resize ise en yakın split oranını
  değiştirir
- **Dahili bar** (opsiyonel, `[bar] enabled = true`) — workspace
  göstergesi + odaklı pencere başlığı; cairo/pango bağımlılığı
  eklemeden çekirdek X11 metin çizimiyle (bkz. [Bilinen riskler](#bilinen-riskler))
- **EWMH/ICCCM temelleri** — `_NET_WM_STRUT_PARTIAL` ile polybar/waybar
  için alan ayırma, `_NET_WM_STATE` okuma/yazma, `WM_DELETE_WINDOW`,
  `WM_TRANSIENT_FOR`/dialog otomatik floating, `WM_NORMAL_HINTS` min boyut

Henüz yok: preselect, monitör hot-plug, dahili barda sağ taraf modülleri
(saat/pil), tiled mouse-resize'de split yönünün (yatay/dikey) ayırt
edilmesi. Ayrıntılar için [Yol haritası](#yol-haritası).

## Mimari

```
qwm/
├── qwm-core/   # WM mantığı (kütüphane): x11, layout, config, ipc, rules, ...
├── qwm/        # WM binary'si (qwm-core'u kullanır, main.rs sadece init+run)
├── qwmctl/     # IPC CLI istemcisi (X11'den tamamen bağımsız)
├── docs/       # örnek config, .desktop dosyası
├── build.sh    # derleme + sisteme kurulum (SDDM/LightDM/GDM) scripti
└── .github/    # CI workflow'u (cargo build/test/fmt/clippy)
```

`qwm-core` içindeki `wm::Wm`, X11 event loop'unu ve `qwmctl`'den (ya da
`sxhkd`'nin çağırdığı `qwmctl`'den) gelen tüm komutları temsil eden
`Action` enum'unu işleyen tek state makinesidir. qwm kendisi klavye
tuşlarını dinlemez — bkz. [Keybinding'ler: sxhkd](#keybindingler-sxhkd).

## Kurulum

### Gereksinimler

- Rust (stable, 2021 edition)
- X11 çalışan bir Linux sistemi
- **[`sxhkd`](https://github.com/baskerville/sxhkd)** — klavye
  kısayolları için (bspwm'in de kullandığı araç). Çoğu dağıtımın paket
  deposunda var: `pacman -S sxhkd`, `apt install sxhkd`, vb. Zorunlu
  değildir (qwm `qwmctl` ile hâlâ tam kontrol edilebilir) ama pratikte
  klavyeden kullanmak için gereklidir.

Derleme için ek sistem bağımlılığı yoktur; `x11rb` XCB protokolünü
doğrudan soket üzerinden konuşur, bir C X11 kütüphanesine bağlanmaz.

### Kaynaktan derleme

```sh
git clone <bu-repo> qwm
cd qwm
cargo build --release
```

Binary'ler `target/release/qwm` ve `target/release/qwmctl` altında oluşur.

### `build.sh` ile derleme + sisteme kurulum

Projeyle birlikte gelen [`build.sh`](build.sh), hem derlemeyi hem de
`qwm`'i bir display manager'ın (SDDM, LightDM, GDM, ...) oturum
listesinde görünür hâle getirmeyi tek komutla yapar:

```sh
./build.sh                  # derle + sisteme kur (gerekirse sudo ister)
./build.sh --build-only     # yalnızca derle, kurma
./build.sh --install-only   # derleme yapma, önceden derlenmiş binary'leri kur
./build.sh --no-desktop     # .desktop dosyasını kurma (yalnızca binary'ler)
./build.sh --no-config      # ~/.config/qwm/qwm.toml'u kopyalama
./build.sh --prefix /usr/bin
./build.sh --uninstall      # kurulan dosyaları kaldır (config KORUNUR)
```

Script şunları yapar:
1. `cargo build --release --workspace` — **her zaman mevcut kullanıcı
   olarak** çalışır (root olarak `cargo build` çalıştırmak `~/.cargo` ve
   `target/` sahipliğini bozar ve sonraki derlemeleri kırar).
2. `qwm` ve `qwmctl`'i `$PREFIX`'e (varsayılan `/usr/local/bin`) kopyalar.
   Hedef dizine yazma izni yoksa yalnızca bu adım için `sudo` ister.
3. `docs/qwm.desktop`'ı (gerçek kurulum yoluna göre `Exec=` satırı
   güncellenmiş hâliyle) `/usr/share/xsessions/qwm.desktop`'a kopyalar —
   böylece **qwm, SDDM/LightDM/GDM'nin oturum seçim ekranında**
   doğrudan görünür.
4. `docs/default-config.toml`'u, dosya henüz yoksa, gerçek kullanıcının
   (`sudo` altında çalıştırılsa bile `$SUDO_USER` tespit edilir)
   `~/.config/qwm/qwm.toml` yoluna kopyalar.

`--uninstall` yalnızca kurulan binary'leri ve `.desktop` dosyasını
kaldırır; `~/.config/qwm/` dokunulmadan kalır.

## Hızlı başlangıç

Gerçek oturumunuzu riske atmadan denemek için `Xephyr` önerilir:

```sh
Xephyr -ac -screen 1280x800 :1 &
DISPLAY=:1 ./target/release/qwm &
DISPLAY=:1 alacritty &
DISPLAY=:1 ./target/release/qwmctl query --windows
```

Gerçek bir X oturumunda `.xinitrc` içine şunu ekleyin:

```sh
exec qwm
```

## Yapılandırma

Config dosyası: `~/.config/qwm/qwm.toml` (ya da
`$XDG_CONFIG_HOME/qwm/qwm.toml`). Tam örnek için
[`docs/default-config.toml`](docs/default-config.toml) dosyasına bakın.
Kapsadığı bölümler: `general`, `gaps`, `border`, `workspaces`, `monitors`,
`input`, `[[keybind]]`, `[[rule]]`, `[[scratchpad]]`, `autostart`, `bar`,
`external_bar`, `ipc`, `log`.

Kısa bir örnek:

```toml
[general]
split_ratio = 0.5
focus_follows_mouse = false

[gaps]
inner = 8
outer_top = 12

[[keybind]]
keys = "Mod+Return"
action = "spawn"
command = "alacritty"

[[rule]]
class = "^Pavucontrol$"
floating = true
center = true
```

Config değiştiğinde `qwmctl config reload` (ya da `Mod+Shift+r`) ile
anında uygulanır; bozuk bir config dosyası WM'i çökertmez, eski ayarlar
korunur ve hata loglanır.

### Mouse move/resize

`[[mousebind]]` girdileri `"Mod+Button1"` gibi bir tuş/buton
kombinasyonunu `move`/`resize`/`focus` aksiyonlarından birine bağlar
(buton numaraları: 1=sol, 2=orta, 3=sağ):

```toml
[[mousebind]]
button = "Mod+Button1"
action = "move"

[[mousebind]]
button = "Mod+Button3"
action = "resize"
```

- **Floating** bir pencerede `move`/`resize` pencereyi doğrudan fareyle
  sürükler/boyutlandırır.
- **Tiled** bir pencerede `move`, pencereyi önce floating'e çıkarıp
  sürüklemeye başlar (çoğu WM'de alışılan davranış); `resize` ise
  pencereyi tiled bırakıp en yakın split düğümünün oranını fare
  hareketine göre değiştirir (yalnızca yatay sürükleme dikkate alınır,
  split'in yatay/dikey olduğu ayırt edilmez — kaba ama kullanılabilir
  bir yaklaşım).

### Dahili bar

`[bar] enabled = true` yapıldığında, birincil monitörün üstünde
(ya da `position = "bottom"` ile altında) workspace göstergeleri ve
odaklı pencerenin başlığını gösteren ince bir pencere oluşturulur. Bu
bar, polybar/waybar gibi harici barlarla aynı mekanizmayı
(`_NET_WM_STRUT_PARTIAL` benzeri bir iç rezervasyon) kullanarak kendi
alanını tiling'den düşer — yani dahili bar ile dış bar'ı aynı anda
makul şekilde kullanabilirsiniz (önerilmez ama çakışmaz).

Bağımlılık yükünü düşük tutmak için cairo/pango yerine çekirdek X11
metin çizimi (`ImageText8` + "fixed" cekirdek fontu) kullanılır; bu
yüzden `[bar] font` ayarı şu an **göz ardı edilir**. `modules_right`
(saat/pil vb.) henüz implemente edilmedi.

## Keybinding'ler: sxhkd

qwm, bspwm gibi klavye dinlemeyi kendi üzerine almaz: `XGrabKey` ve
keysym/keycode eşleme gibi en kırılgan X11 detaylarını büsbütün devre
dışı bırakıp bu işi olgun ve test edilmiş bir araca (`sxhkd`) bırakır.
`qwm.toml`'daki `[[keybind]]` listesi **tek kaynak** olarak kalır —
`sxhkdrc`'yi elle yazıp iki config'i senkron tutmanıza gerek yok:

```sh
mkdir -p ~/.config/sxhkd
qwm --export-sxhkd ~/.config/sxhkd/sxhkdrc
```

Bunu `[autostart]` listesine ekleyin ki qwm her başladığında sxhkd de
çalışsın:

```toml
[autostart]
commands = [
    "sxhkd -c ~/.config/sxhkd/sxhkdrc",
]
```

Config'i değiştirdiğinizde `qwm --export-sxhkd ...` komutunu tekrar
çalıştırıp `pkill -USR1 -x sxhkd` ile sxhkd'yi yeniden yükletin (sxhkd'nin
kendi hot-reload sinyali budur).

`docs/default-config.toml`'daki varsayılan `[[keybind]]` listesi
şunları üretir:

| Tuş | Aksiyon |
|---|---|
| `Mod+Return` | terminal aç |
| `Mod+d` | rofi launcher |
| `Mod+q` | odaklı pencereyi kapat |
| `Mod+h/j/k/l` | odağı yönlendir (batı/güney/kuzey/doğu) |
| `Mod+Shift+h` | odaklı pencereyi batıdaki ile değiştir |
| `Mod+1..9` | workspace'e geç |
| `Mod+Shift+1..9` | pencereyi workspace'e taşı |
| `Mod+f` | floating aç/kapa |
| `Mod+m` | monocle aç/kapa |
| `` Mod+` `` | scratchpad "terminal" aç/kapa |
| `Mod+Shift+r` | config'i yeniden yükle |
| `Mod+Shift+q` | qwm'den çık |

Üretilen `sxhkdrc`'nin bir örneği:

```
super + Return
    alacritty

super + h
    qwmctl node -f west

super + shift + q
    qwmctl quit
```

## qwmctl

bspwm'deki `bspc`'ye paralel tasarlanmış CLI:

```sh
qwmctl node -f west              # odağı batıya kaydır
qwmctl node -s west              # odaklı pencereyi batıdaki ile değiştir
qwmctl node -t floating          # tiled <-> floating
qwmctl node -t monocle           # monocle aç/kapa
qwmctl node -t fullscreen        # fullscreen aç/kapa
qwmctl node -d 3                 # odaklı pencereyi workspace 3'e taşı
qwmctl node --resize west:10     # split oranını batıya doğru %10 kaydır
qwmctl desktop -f 3              # workspace 3'e geç
qwmctl config reload
qwmctl query --windows           # mevcut pencere listesini JSON olarak döker
qwmctl scratchpad toggle terminal
qwmctl spawn -- alacritty
qwmctl quit
```

## Display manager entegrasyonu

En kolay yol [`build.sh`](build.sh) ile kurulumdur (bkz. yukarı); manuel
yapmak isterseniz [`docs/qwm.desktop`](docs/qwm.desktop) dosyasını
`/usr/share/xsessions/qwm.desktop` olarak kopyalayın ve `qwm` binary'sinin
`$PATH` içinde (ya da dosyadaki `Exec=` satırında mutlak yolla) olduğundan
emin olun. SDDM/LightDM/GDM oturum listesinde görünecektir.

`qwm`, `SIGHUP` aldığında config'i yeniden yükler (`qwmctl config reload`
ile aynı), `SIGTERM`/`SIGINT` aldığında ise ana döngüyü temiz şekilde
sonlandırıp IPC socket dosyasını siler — bu sayede bir display manager'ın
oturumu sonlandırma/yeniden başlatma sinyalleri düzgün karşılanır.

## Geliştirme

```sh
cargo build --workspace
cargo test --workspace
cargo fmt --all
cargo clippy --workspace --all-targets
```

`.github/workflows/ci.yml` bu dört adımı her push/PR'da otomatik çalıştırır.

Birim testleri şimdilik `qwm-core/src/layout/bsp_tree.rs` (ağaç
insert/remove) ve `qwm-core/src/keybind.rs` (tuş string parse'ı) içinde;
X11 bağlantısı gerektiren kodun testleri `Xephyr` tabanlı entegrasyon
testleri olarak eklenmeyi bekliyor.

## Bilinen riskler

Bu kod, ağ erişimi olmayan bir ortamda yazıldığı için `cargo build` ile
hiç denenemedi. İlk derlemede karşılaşabileceğiniz muhtemel noktalar:

- `x11rb` 0.13 API'si (`ConnectionExt`, `atom_manager!` makrosu) sürüm
  güncellemeleriyle değişmiş olabilir.
- `wm.rs` ve `bar/mod.rs` içindeki `create_window` çağrılarının depth
  parametresi (`0`) bazı sürümlerde `x11rb::COPY_DEPTH_FROM_PARENT`
  sabitiyle ifade edilmesi gerekebilir.
- `close_window` içindeki `ClientMessageEvent::new(...)` /
  `send_event(..., EventMask::NO_EVENT, ...)` imzaları sürüme göre
  hafifçe farklılaşabilir.
- `grab_buttons` içindeki `ModMask::from(u16)` / `u16::from(ModMask)`
  dönüşümleri (yalnızca mouse bind'lar için kullanılır, bkz. aşağı)
  desteklenmiyorsa, doğrudan tuple-struct erişimine (`ModMask(combined)`)
  çevrilmesi gerekebilir.
- `signal-hook` 0.3 API'si (`Signals::new`, `.forever()`) sürüm
  güncellemeleriyle değişmiş olabilir; `qwm/src/main.rs::install_signal_handlers`
  bu yüzden ilk derlemede küçük bir düzeltme isteyebilir.
- `grab_buttons` içindeki `ButtonIndex::ANY` sabiti bazı x11rb
  sürümlerinde farklı adlandırılmış ya da hiç bulunmuyor olabilir;
  derleyici hata verirse `ungrab_button` çağrısını `0u8` (AnyButton)
  ile değiştirin.
- `bar/mod.rs::alloc_color`, X sunucusunun `roots[0]` (tek X "screen")
  varsayımını yapar; birden fazla X screen'i olan (RandR değil, gerçek
  çoklu-screen) kurulumlarda doğru çalışmayabilir — günümüzde bu
  son derece nadirdir.

Bunların hiçbiri mimariyi etkilemez; birkaç satırlık yerel düzeltmeler
olması beklenir. Bir PR'da bu listeyi güncelleyip kaldırmaktan çekinmeyin.

## Yol haritası

Orijinal spesifikasyonun fazlarına göre durum:

| Faz | Kapsam | Durum |
|---|---|---|
| 0 | X11 bağlantısı, `SubstructureRedirect`, temel event loop | ✅ |
| 1 | BSP tiling (split/swap/resize/close) | ✅ temel; preselect ve mouse resize yok |
| 2 | Multi-monitor + dinamik workspace | ✅ temel; hot-plug ve monitörler arası focus/swap yok |
| 3 | TOML config + hot-reload | ✅ |
| 4 | IPC/`qwmctl` + keybinding | ✅ — `XGrabKey` yerine `sxhkd` (bkz. `qwm --export-sxhkd`); mouse bind'lar hâlâ dahili `XGrabButton` ile |
| 5 | Tam EWMH/ICCCM | ✅ temel (strut, `_NET_WM_STATE`, `WM_NORMAL_HINTS` min boyut, transient-for); max boyut/aspect/increment, tam viewport semantiği yok |
| 6 | Floating rules, scratchpad, monocle, preselect | ✅ preselect hariç |
| 7 | Dahili bar, autostart, sinyal yönetimi, mouse move/resize, cilalama | ✅ temel; autostart, sinyal yönetimi (SIGHUP/SIGTERM/SIGINT), dahili bar (çekirdek X11 çizim) ve mouse move/resize çalışıyor. Eksik: barda sağ modüller (saat/pil), monitör hot-plug, genel cilalama/performans geçişi |

Detaylı not ve bilinen eksikler için her fazın commit geçmişine ve ilgili
kaynak dosyalarındaki yorum satırlarına bakılabilir.

## Katkıda bulunma

Issue ve PR'lara açık. Büyük bir değişiklik öncesi (örn. yeni bir faz)
kısa bir issue açıp yaklaşımı tartışmak işbirliğini kolaylaştırır. Kod
tarzı: `cargo fmt` + `cargo clippy -- -D warnings` temiz geçmeli; yeni
davranış ekleyen fonksiyonlara kısa Türkçe yorum satırı eklemek
(mevcut dosyalardaki gibi) tercih edilir.

## Lisans

[MIT](LICENSE)
