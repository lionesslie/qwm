/// `[gaps]` config bölümüne karşılık gelen çalışma zamanı değerleri.
/// `config::schema::Gaps` TOML'dan parse edilir; bu struct (gerekirse)
/// workspace başına override edilmiş etkin değerleri taşımak için
/// kullanılabilir.
#[derive(Debug, Clone, Copy, Default)]
pub struct Gaps {
    pub inner: i32,
    pub outer_top: i32,
    pub outer_bottom: i32,
    pub outer_left: i32,
    pub outer_right: i32,
    pub smart_gaps: bool,
}
