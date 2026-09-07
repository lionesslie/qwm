class Monitor:
    def __init__(self, name, x, y, width, height, primary=False):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.primary = primary

    def area(self):
        return (self.x, self.y, self.width, self.height)

    def __repr__(self):
        return f"<Monitor {self.name} {self.width}x{self.height}+{self.x}+{self.y}>"


class Workspace:
    def __init__(self, index, name, default_layout="master_stack"):
        self.index = index
        self.name = name
        self.layout = default_layout
        self.master_ratio = 0.55
        self.monitor = None
        self.window_ids = []

    def add(self, wid):
        if wid not in self.window_ids:
            self.window_ids.append(wid)

    def remove(self, wid):
        if wid in self.window_ids:
            self.window_ids.remove(wid)

    def cycle_layout(self, order):
        i = order.index(self.layout) if self.layout in order else 0
        self.layout = order[(i + 1) % len(order)]
        return self.layout


class WorkspaceManager:
    def __init__(self, count, names, default_layout="master_stack"):
        self.workspaces = []
        for i in range(count):
            name = names[i] if i < len(names) else str(i + 1)
            self.workspaces.append(Workspace(i, name, default_layout))
        self.current_index = 0
        self.monitors = []

    def current(self):
        return self.workspaces[self.current_index]

    def get(self, index):
        if 0 <= index < len(self.workspaces):
            return self.workspaces[index]
        return None

    def switch_to(self, index):
        if 0 <= index < len(self.workspaces) and index != self.current_index:
            prev = self.current_index
            self.current_index = index
            return prev, index
        return None

    def set_monitors(self, monitors):
        self.monitors = monitors
        if not monitors:
            return
        for i, ws in enumerate(self.workspaces):
            ws.monitor = monitors[i % len(monitors)]

    def find_workspace_of(self, wid):
        for ws in self.workspaces:
            if wid in ws.window_ids:
                return ws
        return None

    def move_window(self, wid, from_ws, to_ws):
        if from_ws:
            from_ws.remove(wid)
        if to_ws:
            to_ws.add(wid)
