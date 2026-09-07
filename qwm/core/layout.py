def _apply_gaps(x, y, w, h, gap):
    return x + gap, y + gap, max(1, w - 2 * gap), max(1, h - 2 * gap)


def master_stack(windows, area, inner_gap, outer_gap, master_ratio=0.55):
    ax, ay, aw, ah = area
    ax, ay, aw, ah = ax + outer_gap, ay + outer_gap, aw - 2 * outer_gap, ah - 2 * outer_gap
    n = len(windows)
    result = {}
    if n == 0:
        return result
    if n == 1:
        result[windows[0].id] = _apply_gaps(ax, ay, aw, ah, 0)
        return result

    master_w = int(aw * master_ratio)
    stack_w = aw - master_w
    master = windows[0]
    stack = windows[1:]

    mx, my, mw, mh = _apply_gaps(ax, ay, master_w, ah, inner_gap // 2)
    result[master.id] = (mx, my, mw, mh)

    stack_count = len(stack)
    stack_h = ah // stack_count
    for i, win in enumerate(stack):
        sx = ax + master_w
        sy = ay + i * stack_h
        sh = stack_h if i < stack_count - 1 else ah - stack_h * (stack_count - 1)
        gx, gy, gw, gh = _apply_gaps(sx, sy, stack_w, sh, inner_gap // 2)
        result[win.id] = (gx, gy, gw, gh)
    return result


def grid(windows, area, inner_gap, outer_gap, **kwargs):
    ax, ay, aw, ah = area
    ax, ay, aw, ah = ax + outer_gap, ay + outer_gap, aw - 2 * outer_gap, ah - 2 * outer_gap
    n = len(windows)
    result = {}
    if n == 0:
        return result

    cols = 1
    while cols * cols < n:
        cols += 1
    rows = (n + cols - 1) // cols

    cell_w = aw // cols
    cell_h = ah // rows

    for i, win in enumerate(windows):
        col = i % cols
        row = i // cols
        items_in_row = min(cols, n - row * cols)
        row_w = aw // items_in_row
        cx = ax + col * row_w
        cy = ay + row * cell_h
        cw = row_w
        ch = cell_h if row < rows - 1 else ah - cell_h * (rows - 1)
        gx, gy, gw, gh = _apply_gaps(cx, cy, cw, ch, inner_gap // 2)
        result[win.id] = (gx, gy, gw, gh)
    return result


def monocle(windows, area, inner_gap, outer_gap, **kwargs):
    ax, ay, aw, ah = area
    result = {}
    for win in windows:
        gx, gy, gw, gh = _apply_gaps(ax, ay, aw, ah, outer_gap)
        result[win.id] = (gx, gy, gw, gh)
    return result


def spiral(windows, area, inner_gap, outer_gap, **kwargs):
    ax, ay, aw, ah = area
    ax, ay, aw, ah = ax + outer_gap, ay + outer_gap, aw - 2 * outer_gap, ah - 2 * outer_gap
    result = {}
    n = len(windows)
    if n == 0:
        return result
    if n == 1:
        gx, gy, gw, gh = _apply_gaps(ax, ay, aw, ah, 0)
        result[windows[0].id] = (gx, gy, gw, gh)
        return result

    x, y, w, h = ax, ay, aw, ah
    vertical = True
    for i, win in enumerate(windows):
        last = i == n - 1
        if last:
            gx, gy, gw, gh = _apply_gaps(x, y, w, h, inner_gap // 2)
            result[win.id] = (gx, gy, gw, gh)
            break
        if vertical:
            half = w // 2
            gx, gy, gw, gh = _apply_gaps(x, y, half, h, inner_gap // 2)
            result[win.id] = (gx, gy, gw, gh)
            x = x + half
            w = w - half
        else:
            half = h // 2
            gx, gy, gw, gh = _apply_gaps(x, y, w, half, inner_gap // 2)
            result[win.id] = (gx, gy, gw, gh)
            y = y + half
            h = h - half
        vertical = not vertical
    return result


LAYOUTS = {
    "master_stack": master_stack,
    "grid": grid,
    "monocle": monocle,
    "spiral": spiral,
}


def apply_layout(name, windows, area, inner_gap, outer_gap, master_ratio=0.55):
    fn = LAYOUTS.get(name, master_stack)
    if name == "master_stack":
        return fn(windows, area, inner_gap, outer_gap, master_ratio=master_ratio)
    return fn(windows, area, inner_gap, outer_gap)
