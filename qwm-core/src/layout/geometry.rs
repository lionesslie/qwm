use super::bsp_tree::{Node, SplitDir};
use x11rb::protocol::xproto::Window;

#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub x: i32,
    pub y: i32,
    pub w: u32,
    pub h: u32,
}

/// Ağacı verilen alana (`region`) göre yerleştirir; her pencere için
/// `inner_gap` uygulanmış nihai dikdörtgeni döner. Dönen sıralama
/// önemsizdir, her pencere tam olarak bir kez geçer.
pub fn layout(node: &Node, region: Rect, inner_gap: i32) -> Vec<(Window, Rect)> {
    let mut out = Vec::new();
    layout_into(node, region, inner_gap, &mut out);
    out
}

fn layout_into(node: &Node, region: Rect, inner_gap: i32, out: &mut Vec<(Window, Rect)>) {
    match node {
        Node::Leaf(w) => {
            let x = region.x + inner_gap;
            let y = region.y + inner_gap;
            let width = (region.w as i32 - 2 * inner_gap).max(1) as u32;
            let height = (region.h as i32 - 2 * inner_gap).max(1) as u32;
            out.push((
                *w,
                Rect {
                    x,
                    y,
                    w: width,
                    h: height,
                },
            ));
        }
        Node::Split {
            dir,
            ratio,
            first,
            second,
        } => {
            let (r1, r2) = split_region(region, *dir, *ratio);
            layout_into(first, r1, inner_gap, out);
            layout_into(second, r2, inner_gap, out);
        }
    }
}

fn split_region(region: Rect, dir: SplitDir, ratio: f32) -> (Rect, Rect) {
    match dir {
        SplitDir::Vertical => {
            let w1 = ((region.w as f32) * ratio) as u32;
            let w2 = region.w.saturating_sub(w1);
            (
                Rect {
                    x: region.x,
                    y: region.y,
                    w: w1,
                    h: region.h,
                },
                Rect {
                    x: region.x + w1 as i32,
                    y: region.y,
                    w: w2,
                    h: region.h,
                },
            )
        }
        SplitDir::Horizontal => {
            let h1 = ((region.h as f32) * ratio) as u32;
            let h2 = region.h.saturating_sub(h1);
            (
                Rect {
                    x: region.x,
                    y: region.y,
                    w: region.w,
                    h: h1,
                },
                Rect {
                    x: region.x,
                    y: region.y + h1 as i32,
                    w: region.w,
                    h: h2,
                },
            )
        }
    }
}
