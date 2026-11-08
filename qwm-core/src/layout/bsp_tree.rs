//! bspwm tarzı dinamik binary-space-partitioning ağacı.
//!
//! Her yaprak (`Leaf`) bir pencereyi tutar; her iç düğüm (`Split`) alanı
//! yatay ya da dikey olarak `ratio` oranında ikiye böler. Bu dosya saf
//! veri yapısını içerir; piksel koordinatlarına çevirme işi
//! `layout::geometry` modülünde yapılır (ayrım bilinçli: ağaç mantığı
//! X11'den tamamen bağımsız test edilebilir).

use x11rb::protocol::xproto::Window;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SplitDir {
    Horizontal,
    Vertical,
}

#[derive(Debug, Clone)]
pub enum Node {
    Split {
        dir: SplitDir,
        ratio: f32,
        first: Box<Node>,
        second: Box<Node>,
    },
    Leaf(Window),
}

pub struct BspTree {
    pub root: Option<Node>,
    pub default_ratio: f32,
}

impl BspTree {
    pub fn new(default_ratio: f32) -> Self {
        Self {
            root: None,
            default_ratio,
        }
    }

    /// Yeni pencereyi ağaca ekler. `target` verilmişse (genelde odaklı
    /// pencere) o yaprak `dir` yönünde ikiye bölünür ve yeni pencere
    /// ikinci çocuk olur. `target` `None`ise ya da ağaçta bulunamazsa
    /// ağacın mevcut kökü bölünür (tek pencerelik ağaçlarda doğal olarak
    /// kökle aynı şeydir).
    pub fn insert(&mut self, window: Window, target: Option<Window>, dir: SplitDir) {
        match self.root.take() {
            None => self.root = Some(Node::Leaf(window)),
            Some(root) => {
                self.root = Some(Self::insert_into(
                    root,
                    window,
                    target,
                    dir,
                    self.default_ratio,
                ));
            }
        }
    }

    fn insert_into(
        node: Node,
        window: Window,
        target: Option<Window>,
        dir: SplitDir,
        ratio: f32,
    ) -> Node {
        match node {
            Node::Leaf(w) if target.is_none() || target == Some(w) => Node::Split {
                dir,
                ratio,
                first: Box::new(Node::Leaf(w)),
                second: Box::new(Node::Leaf(window)),
            },
            Node::Leaf(w) => Node::Leaf(w),
            Node::Split {
                dir: d,
                ratio: r,
                first,
                second,
            } => Node::Split {
                dir: d,
                ratio: r,
                first: Box::new(Self::insert_into(*first, window, target, dir, ratio)),
                second: Box::new(Self::insert_into(*second, window, target, dir, ratio)),
            },
        }
    }

    /// Pencereyi ağaçtan kaldırır. Silinen yaprağın kardeşi, ebeveyninin
    /// (Split düğümünün) yerini alır — bspwm'deki "kapatınca komşu alan
    /// genişler" davranışı budur.
    pub fn remove(&mut self, window: Window) {
        if let Some(Node::Leaf(w)) = &self.root {
            if *w == window {
                self.root = None;
                return;
            }
        }
        if let Some(root) = self.root.take() {
            self.root = Self::remove_from(root, window);
        }
    }

    fn remove_from(node: Node, window: Window) -> Option<Node> {
        match node {
            Node::Leaf(w) if w == window => None,
            Node::Leaf(w) => Some(Node::Leaf(w)),
            Node::Split {
                dir,
                ratio,
                first,
                second,
            } => {
                let first = Self::remove_from(*first, window);
                let second = Self::remove_from(*second, window);
                match (first, second) {
                    (Some(f), Some(s)) => Some(Node::Split {
                        dir,
                        ratio,
                        first: Box::new(f),
                        second: Box::new(s),
                    }),
                    (Some(f), None) => Some(f),
                    (None, Some(s)) => Some(s),
                    (None, None) => None,
                }
            }
        }
    }

    /// Ağaçtaki yaprağın (pencerenin) split oranını `delta` kadar değiştirir
    /// (örn. `qwmctl node -r 10%` -> delta = 0.10). `window`i doğrudan
    /// tutan Split düğümünü bulup oranını günceller.
    pub fn resize(&mut self, window: Window, delta: f32) {
        if let Some(root) = &mut self.root {
            Self::resize_in(root, window, delta);
        }
    }

    fn resize_in(node: &mut Node, window: Window, delta: f32) -> bool {
        match node {
            Node::Leaf(w) => *w == window,
            Node::Split {
                ratio,
                first,
                second,
                ..
            } => {
                if Self::resize_in(first, window, delta) {
                    *ratio = (*ratio + delta).clamp(0.05, 0.95);
                    true
                } else if Self::resize_in(second, window, delta) {
                    *ratio = (*ratio - delta).clamp(0.05, 0.95);
                    true
                } else {
                    false
                }
            }
        }
    }

    pub fn windows(&self) -> Vec<Window> {
        let mut out = Vec::new();
        if let Some(root) = &self.root {
            Self::collect(root, &mut out);
        }
        out
    }

    fn collect(node: &Node, out: &mut Vec<Window>) {
        match node {
            Node::Leaf(w) => out.push(*w),
            Node::Split { first, second, .. } => {
                Self::collect(first, out);
                Self::collect(second, out);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn insert_and_remove_restores_single_leaf() {
        let mut tree = BspTree::new(0.5);
        tree.insert(1, None, SplitDir::Vertical);
        tree.insert(2, Some(1), SplitDir::Horizontal);
        assert_eq!(tree.windows().len(), 2);

        tree.remove(1);
        assert_eq!(tree.windows(), vec![2]);

        tree.remove(2);
        assert!(tree.root.is_none());
    }
}
