use crate::layout::bsp_tree::BspTree;

/// Tek bir monitordeki tek bir workspace. `mode = "dynamic"` oldugunda WM,
/// `is_empty()` true donen workspace'leri otomatik siler ve gerektiginde
/// yenisini olusturur (bkz. `wm.rs::prune_empty_workspaces`).
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
