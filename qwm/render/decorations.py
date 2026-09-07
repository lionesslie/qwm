def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def rgb_to_x11_pixel(r, g, b):
    return (r << 16) | (g << 8) | b


def color_to_pixel(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_x11_pixel(r, g, b)


class DecorationConfig:
    def __init__(self, border_width, border_radius, active_color, inactive_color, inner_gap, outer_gap):
        self.border_width = border_width
        self.border_radius = border_radius
        self.active_pixel = color_to_pixel(active_color)
        self.inactive_pixel = color_to_pixel(inactive_color)
        self.inner_gap = inner_gap
        self.outer_gap = outer_gap

    @classmethod
    def from_config(cls, general_cfg, colors_cfg):
        return cls(
            border_width=general_cfg.get("border_width", 2),
            border_radius=general_cfg.get("border_radius", 12),
            active_color=colors_cfg.get("border_active", "#89b4fa"),
            inactive_color=colors_cfg.get("border_inactive", "#45475a"),
            inner_gap=general_cfg.get("gap_inner", 10),
            outer_gap=general_cfg.get("gap_outer", 15),
        )

    def rounded_rect_mask_points(self, width, height, radius, segments=8):
        import math
        radius = min(radius, width // 2, height // 2)
        points = []
        corners = [
            (radius, radius, 180, 270),
            (width - radius, radius, 270, 360),
            (width - radius, height - radius, 0, 90),
            (radius, height - radius, 90, 180),
        ]
        for cx, cy, start_deg, end_deg in corners:
            for i in range(segments + 1):
                angle = math.radians(start_deg + (end_deg - start_deg) * i / segments)
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                points.append((round(x), round(y)))
        return points
