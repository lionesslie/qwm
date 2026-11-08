use crate::config::schema::Rule;
use regex::Regex;

/// Derlenmiş (regex'leri önceden compile edilmiş) kural. Config her
/// hot-reload'da yeniden derlenir.
pub struct CompiledRule {
    pub class: Option<Regex>,
    pub instance: Option<Regex>,
    pub title: Option<Regex>,
    pub raw: Rule,
}

pub fn compile_rules(rules: &[Rule]) -> Vec<CompiledRule> {
    rules
        .iter()
        .map(|r| CompiledRule {
            class: r.class.as_deref().and_then(|p| Regex::new(p).ok()),
            instance: r.instance.as_deref().and_then(|p| Regex::new(p).ok()),
            title: r.title.as_deref().and_then(|p| Regex::new(p).ok()),
            raw: r.clone(),
        })
        .collect()
}

/// Verilen WM_CLASS (class, instance) ve pencere başlığı için eşleşen ilk
/// kuralı döner. Bir kuralda tanımlı olmayan alan (örn. `title` yoksa)
/// her zaman eşleşmiş sayılır; en az bir alanın tanımlı olması gerekir.
pub fn find_match<'a>(
    rules: &'a [CompiledRule],
    class: &str,
    instance: &str,
    title: &str,
) -> Option<&'a CompiledRule> {
    rules.iter().find(|r| {
        let has_any = r.class.is_some() || r.instance.is_some() || r.title.is_some();
        let class_ok = r.class.as_ref().map_or(true, |re| re.is_match(class));
        let instance_ok = r
            .instance
            .as_ref()
            .map_or(true, |re| re.is_match(instance));
        let title_ok = r.title.as_ref().map_or(true, |re| re.is_match(title));
        has_any && class_ok && instance_ok && title_ok
    })
}
