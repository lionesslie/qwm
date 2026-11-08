use crate::layout::bsp_tree::BspTree;

/// Tek bir monitördeki tek bir workspace. `mode = "dynamic"` olduğunda
/// WM, `is_empty()` true dönen workspace'leri otomatik siler ve gerektiğinde
/// yenisini oluşturur (bkz. `wm.rs`).
pub struct Workspace {
    pub id: usize,
    pub name: Option<String>,
    pub tree: BspTree,
    pub layout: Layout,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Layout {
    Bsp,
    Monocle,
}

impl Workspace {
    pub fn new(id: usize, name: Option<String>, split_ratio: f32) -> Self {
        Self {
            id,
            name,
            tree: BspTree::new(split_ratio),
            layout: Layout::Bsp,
        }
    }

    pub fn is_empty(&self) -> bool {
        self.tree.root.is_none()
    }
}
