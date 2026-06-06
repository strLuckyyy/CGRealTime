
import json
import csv
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ============================================================
# Matemática das curvas
# ============================================================

EPS = 1e-9


def safe_norm(v):
    n = np.linalg.norm(v)
    return n if n > EPS else EPS


def normalize(v):
    n = np.linalg.norm(v)
    if n < EPS:
        return np.array([0.0, 0.0])
    return v / n


def bezier_cubic(P0, P1, P2, P3, t):
    return (
        ((1 - t) ** 3) * P0
        + 3 * ((1 - t) ** 2) * t * P1
        + 3 * (1 - t) * (t ** 2) * P2
        + (t ** 3) * P3
    )


def bezier_cubic_derivative(P0, P1, P2, P3, t):
    return (
        3 * ((1 - t) ** 2) * (P1 - P0)
        + 6 * (1 - t) * t * (P2 - P1)
        + 3 * (t ** 2) * (P3 - P2)
    )


def bezier_cubic_second_derivative(P0, P1, P2, P3, t):
    return (
        6 * (1 - t) * (P2 - 2 * P1 + P0)
        + 6 * t * (P3 - 2 * P2 + P1)
    )


def de_casteljau_points(points, t):
    levels = [np.array(points, dtype=float)]
    current = np.array(points, dtype=float)
    while len(current) > 1:
        current = np.array([(1 - t) * current[i] + t * current[i + 1] for i in range(len(current) - 1)])
        levels.append(current)
    return levels


def hermite_curve(P1, P2, M1, M2, t):
    return (
        (2 * t ** 3 - 3 * t ** 2 + 1) * P1
        + (t ** 3 - 2 * t ** 2 + t) * M1
        + (-2 * t ** 3 + 3 * t ** 2) * P2
        + (t ** 3 - t ** 2) * M2
    )


def hermite_derivative(P1, P2, M1, M2, t):
    return (
        (6 * t ** 2 - 6 * t) * P1
        + (3 * t ** 2 - 4 * t + 1) * M1
        + (-6 * t ** 2 + 6 * t) * P2
        + (3 * t ** 2 - 2 * t) * M2
    )


def hermite_second_derivative(P1, P2, M1, M2, t):
    return (
        (12 * t - 6) * P1
        + (6 * t - 4) * M1
        + (-12 * t + 6) * P2
        + (6 * t - 2) * M2
    )


def catmull_uniform(P0, P1, P2, P3, t):
    return 0.5 * (
        (2 * P1)
        + (-P0 + P2) * t
        + (2 * P0 - 5 * P1 + 4 * P2 - P3) * (t ** 2)
        + (-P0 + 3 * P1 - 3 * P2 + P3) * (t ** 3)
    )


def catmull_uniform_derivative(P0, P1, P2, P3, t):
    return 0.5 * (
        (-P0 + P2)
        + 2 * (2 * P0 - 5 * P1 + 4 * P2 - P3) * t
        + 3 * (-P0 + 3 * P1 - 3 * P2 + P3) * (t ** 2)
    )


def catmull_uniform_second_derivative(P0, P1, P2, P3, t):
    return 0.5 * (
        2 * (2 * P0 - 5 * P1 + 4 * P2 - P3)
        + 6 * (-P0 + 3 * P1 - 3 * P2 + P3) * t
    )


def catmull_nonuniform(P0, P1, P2, P3, t, alpha=0.5):
    # t local normalizado [0, 1], com parametrização chordal/centripetal.
    def tj(ti, Pi, Pj):
        return ti + (safe_norm(Pj - Pi) ** alpha)

    t0 = 0.0
    t1 = tj(t0, P0, P1)
    t2 = tj(t1, P1, P2)
    t3 = tj(t2, P2, P3)

    if abs(t2 - t1) < EPS:
        return P1.copy()

    u = t1 + t * (t2 - t1)

    def lerp_time(A, B, ta, tb):
        if abs(tb - ta) < EPS:
            return A.copy()
        return ((tb - u) / (tb - ta)) * A + ((u - ta) / (tb - ta)) * B

    A1 = lerp_time(P0, P1, t0, t1)
    A2 = lerp_time(P1, P2, t1, t2)
    A3 = lerp_time(P2, P3, t2, t3)

    B1 = lerp_time(A1, A2, t0, t2)
    B2 = lerp_time(A2, A3, t1, t3)

    C = lerp_time(B1, B2, t1, t2)
    return C


def numerical_derivative(func, t, h=1e-4):
    t0 = max(0.0, t - h)
    t1 = min(1.0, t + h)
    if abs(t1 - t0) < EPS:
        return np.array([0.0, 0.0])
    return (func(t1) - func(t0)) / (t1 - t0)


def numerical_second_derivative(func, t, h=1e-3):
    t0 = max(0.0, t - h)
    t2 = min(1.0, t + h)
    if abs(t2 - t0) < EPS:
        return np.array([0.0, 0.0])
    tm = (t0 + t2) / 2
    return (func(t2) - 2 * func(tm) + func(t0)) / (((t2 - t0) / 2) ** 2)


def curvature_from_derivatives(d1, d2):
    denom = safe_norm(d1) ** 3
    cross = abs(d1[0] * d2[1] - d1[1] * d2[0])
    return cross / denom


def perpendicular(v):
    return np.array([-v[1], v[0]])


# ============================================================
# Utilidades
# ============================================================

def parse_point(text):
    text = text.strip().replace(";", ",")
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        raise ValueError("Use o formato x, y")
    return np.array([float(parts[0]), float(parts[1])], dtype=float)


def fmt_point(p):
    return f"{p[0]:.2f}, {p[1]:.2f}"


def apply_theme(root):
    style = ttk.Style()
    style.theme_use("clam")

    root.configure(bg="#eef1f7")

    style.configure("TFrame", background="#eef1f7")
    style.configure("Card.TFrame", background="#ffffff", relief="flat")
    style.configure("TLabel", background="#eef1f7", foreground="#172033", font=("Segoe UI", 10))
    style.configure("Card.TLabel", background="#ffffff", foreground="#172033", font=("Segoe UI", 10))
    style.configure("Muted.Card.TLabel", background="#ffffff", foreground="#64748b", font=("Segoe UI", 9))
    style.configure("Title.TLabel", background="#eef1f7", foreground="#0f172a", font=("Segoe UI", 18, "bold"))
    style.configure("Section.Card.TLabel", background="#ffffff", foreground="#0f172a", font=("Segoe UI", 12, "bold"))
    style.configure("TButton", font=("Segoe UI", 10), padding=(8, 6))
    style.configure("TEntry", font=("Consolas", 10), padding=6)
    style.configure("TCheckbutton", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TRadiobutton", background="#ffffff", font=("Segoe UI", 10))
    style.configure("TNotebook", background="#eef1f7", borderwidth=0)
    style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(18, 9))
    style.configure("TSeparator", background="#e2e8f0")


@dataclass
class HistoryState:
    data: dict


# ============================================================
# Classe base
# ============================================================

class CurveEditor:
    def __init__(self, parent, app, name, color):
        self.parent = parent
        self.app = app
        self.name = name
        self.color = color

        self.xlim = [-2.0, 10.0]
        self.ylim = [-4.0, 8.0]

        self.curve = np.empty((0, 2))
        self.t_values = np.empty(0)
        self.segment_ids = np.empty(0, dtype=int)

        self.dragging = None
        self.hover_index = None
        self.history = []
        self.redo_stack = []
        self.suspend_history = False
        self.suspend_entry_update = False

        self.segments = tk.IntVar(value=32)
        self.t_slider = tk.DoubleVar(value=0.5)

        self.show_samples = tk.BooleanVar(value=False)
        self.show_tangent = tk.BooleanVar(value=True)
        self.show_normal = tk.BooleanVar(value=False)
        self.show_curvature = tk.BooleanVar(value=False)
        self.show_equation = tk.BooleanVar(value=True)
        self.animate_vehicle = tk.BooleanVar(value=False)

        self.animation_after = None
        self.vehicle_t = 0.0

        self.build_layout()
        self.bind_shortcuts()

    def build_layout(self):
        self.container = ttk.Frame(self.parent, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.graph_frame = ttk.Frame(self.container)
        self.graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Painel lateral com scroll vertical
        panel_container = ttk.Frame(self.container, width=360)
        panel_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(14, 0))
        panel_container.pack_propagate(False)

        panel_canvas = tk.Canvas(
            panel_container,
            bg="#ffffff",
            highlightthickness=0,
            bd=0
        )

        panel_scrollbar = ttk.Scrollbar(
            panel_container,
            orient="vertical",
            command=panel_canvas.yview
        )

        self.panel = ttk.Frame(panel_canvas, style="Card.TFrame", padding=14)

        panel_window = panel_canvas.create_window(
            (0, 0),
            window=self.panel,
            anchor="nw"
        )

        def _configure_scroll_region(event=None):
            panel_canvas.configure(scrollregion=panel_canvas.bbox("all"))

        def _configure_canvas_width(event):
            panel_canvas.itemconfig(panel_window, width=event.width)

        self.panel.bind("<Configure>", _configure_scroll_region)
        panel_canvas.bind("<Configure>", _configure_canvas_width)

        panel_canvas.configure(yscrollcommand=panel_scrollbar.set)

        panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        panel_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            panel_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        panel_canvas.bind("<Enter>", lambda e: panel_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        panel_canvas.bind("<Leave>", lambda e: panel_canvas.unbind_all("<MouseWheel>"))

        self.fig, self.ax = plt.subplots(figsize=(8.8, 7.2), dpi=100)
        self.fig.patch.set_facecolor("#eef1f7")
        self.ax.set_facecolor("#ffffff")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.tooltip = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#94a3b8", alpha=0.96),
            fontsize=9,
            visible=False,
        )

        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)

    def bind_shortcuts(self):
        widget = self.canvas.get_tk_widget()
        widget.bind("<Control-z>", lambda e: self.undo())
        widget.bind("<Control-y>", lambda e: self.redo())
        widget.bind("<Control-s>", lambda e: self.save_json())
        widget.bind("<Control-o>", lambda e: self.load_json())
        widget.focus_set()

    def add_common_panel(self):
        ttk.Separator(self.panel).pack(fill=tk.X, pady=12)

        ttk.Label(self.panel, text="Amostragem", style="Section.Card.TLabel").pack(anchor="w", pady=(0, 8))

        row = ttk.Frame(self.panel, style="Card.TFrame")
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Segmentos", style="Card.TLabel").pack(side=tk.LEFT)
        spin = ttk.Spinbox(row, from_=1, to=500, textvariable=self.segments, width=7, command=self.draw)
        spin.pack(side=tk.RIGHT)
        spin.bind("<KeyRelease>", lambda e: self.draw())

        t_row = ttk.Frame(self.panel, style="Card.TFrame")
        t_row.pack(fill=tk.X, pady=(8, 2))
        ttk.Label(t_row, text="t", style="Card.TLabel").pack(side=tk.LEFT)
        self.t_readout = ttk.Label(t_row, text="0.500", style="Muted.Card.TLabel")
        self.t_readout.pack(side=tk.RIGHT)

        t_scale = ttk.Scale(
            self.panel,
            from_=0.0,
            to=1.0,
            variable=self.t_slider,
            command=lambda value: self.on_t_slider(value),
        )
        t_scale.pack(fill=tk.X, pady=(0, 8))

        ttk.Checkbutton(self.panel, text="Mostrar pontos amostrados", variable=self.show_samples, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(self.panel, text="Mostrar tangente", variable=self.show_tangent, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(self.panel, text="Mostrar normal", variable=self.show_normal, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(self.panel, text="Mostrar curvatura", variable=self.show_curvature, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(self.panel, text="Mostrar fórmula/estado", variable=self.show_equation, command=self.draw).pack(anchor="w")

        ttk.Separator(self.panel).pack(fill=tk.X, pady=12)

        ttk.Label(self.panel, text="Uso", style="Section.Card.TLabel").pack(anchor="w", pady=(0, 8))

        buttons1 = ttk.Frame(self.panel, style="Card.TFrame")
        buttons1.pack(fill=tk.X, pady=3)
        ttk.Button(buttons1, text="Undo", command=self.undo).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(buttons1, text="Redo", command=self.redo).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        buttons2 = ttk.Frame(self.panel, style="Card.TFrame")
        buttons2.pack(fill=tk.X, pady=3)
        ttk.Button(buttons2, text="Resetar", command=self.reset).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(buttons2, text="PNG", command=self.export_png).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        buttons3 = ttk.Frame(self.panel, style="Card.TFrame")
        buttons3.pack(fill=tk.X, pady=3)
        ttk.Button(buttons3, text="Salvar JSON", command=self.save_json).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(buttons3, text="Carregar", command=self.load_json).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        buttons4 = ttk.Frame(self.panel, style="Card.TFrame")
        buttons4.pack(fill=tk.X, pady=3)
        ttk.Button(buttons4, text="Exportar CSV", command=self.export_csv).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Checkbutton(
            self.panel,
            text="Animar veículo",
            variable=self.animate_vehicle,
            command=self.toggle_animation,
        ).pack(anchor="w", pady=(10, 0))

        ttk.Label(
            self.panel,
            text="Scroll altera o zoom. Ctrl+Z/Ctrl+Y desfaz/refaz. Segure Shift ao arrastar para travar no eixo dominante.",
            style="Muted.Card.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(12, 0))

    def setup_axes(self):
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.grid(True, color="#e2e8f0", linewidth=0.8)
        self.ax.axhline(0, color="#cbd5e1", linewidth=1)
        self.ax.axvline(0, color="#cbd5e1", linewidth=1)
        self.ax.set_title(self.name, fontsize=15, pad=12, color="#0f172a")

    def on_scroll(self, event):
        if event.xdata is None or event.ydata is None:
            return

        scale = 0.85 if event.button == "up" else 1.15
        x, y = event.xdata, event.ydata
        x0, x1 = self.xlim
        y0, y1 = self.ylim

        self.xlim = [x - (x - x0) * scale, x + (x1 - x) * scale]
        self.ylim = [y - (y - y0) * scale, y + (y1 - y) * scale]
        self.draw()

    def push_history(self):
        if self.suspend_history:
            return
        self.history.append(HistoryState(self.serialize()))
        self.redo_stack.clear()
        if len(self.history) > 100:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            return
        self.redo_stack.append(HistoryState(self.serialize()))
        state = self.history.pop()
        self.suspend_history = True
        self.deserialize(state.data)
        self.suspend_history = False
        self.sync_entries()
        self.draw()

    def redo(self):
        if not self.redo_stack:
            return
        self.history.append(HistoryState(self.serialize()))
        state = self.redo_stack.pop()
        self.suspend_history = True
        self.deserialize(state.data)
        self.suspend_history = False
        self.sync_entries()
        self.draw()

    def on_t_slider(self, value):
        self.t_readout.configure(text=f"{float(value):.3f}")
        self.draw()

    def nearest_curve_index(self, event):
        if event.xdata is None or event.ydata is None or len(self.curve) == 0:
            return None

        mouse = np.array([event.xdata, event.ydata])
        distances = np.linalg.norm(self.curve - mouse, axis=1)
        index = int(np.argmin(distances))

        threshold = max(self.xlim[1] - self.xlim[0], self.ylim[1] - self.ylim[0]) * 0.035
        if distances[index] > threshold:
            return None
        return index

    def update_hover(self, event):
        index = self.nearest_curve_index(event)
        self.hover_index = index

        if index is None:
            self.tooltip.set_visible(False)
            self.draw(keep_hover=True)
            return

        p = self.curve[index]
        t = self.t_values[index]
        seg = int(self.segment_ids[index]) if len(self.segment_ids) else 0

        self.tooltip.xy = p
        self.tooltip.set_text(f"segmento = {seg}\nt = {t:.3f}\n({p[0]:.3f}, {p[1]:.3f})")
        self.tooltip.set_visible(True)
        self.draw(keep_hover=True)

    def draw_curve_with_curvature(self):
        if len(self.curve) < 2:
            return

        if not self.show_curvature.get():
            self.ax.plot(self.curve[:, 0], self.curve[:, 1], color=self.color, linewidth=3, solid_capstyle="round")
            return

        points = self.curve.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        curvatures = np.array([self.curvature_at(float(t), int(s)) for t, s in zip(self.t_values, self.segment_ids)])
        if len(curvatures) > 1:
            c = curvatures[:-1]
        else:
            c = curvatures

        lc = LineCollection(segments, cmap="plasma", linewidth=3)
        lc.set_array(c)
        self.ax.add_collection(lc)

    def draw_samples(self):
        if self.show_samples.get() and len(self.curve):
            self.ax.scatter(self.curve[:, 0], self.curve[:, 1], s=16, color="#334155", alpha=0.45, zorder=4)

    def draw_t_marker(self):
        if len(self.curve) == 0:
            return

        t = float(self.t_slider.get())
        seg = self.active_segment_for_slider()
        point = self.evaluate(t, seg)
        tangent = self.derivative_at(t, seg)
        normal = perpendicular(normalize(tangent))

        self.ax.scatter([point[0]], [point[1]], s=120, color="#facc15", edgecolor="#0f172a", linewidth=1.2, zorder=8)

        if self.show_tangent.get():
            v = normalize(tangent)
            self.ax.arrow(point[0], point[1], v[0], v[1], head_width=0.18, length_includes_head=True, color="#0f172a", linewidth=2, zorder=8)

        if self.show_normal.get():
            self.ax.arrow(point[0], point[1], normal[0], normal[1], head_width=0.18, length_includes_head=True, color="#7c3aed", linewidth=2, zorder=8)

        if self.animate_vehicle.get():
            self.draw_vehicle(point, tangent)

    def draw_vehicle(self, point, tangent):
        direction = normalize(tangent)
        if safe_norm(direction) < EPS:
            direction = np.array([1.0, 0.0])
        side = perpendicular(direction)

        length = 0.7
        width = 0.38

        p_front = point + direction * length
        p_back = point - direction * length * 0.55
        corners = np.array([
            p_front + side * width,
            p_front - side * width,
            p_back - side * width,
            p_back + side * width,
            p_front + side * width,
        ])

        self.ax.plot(corners[:, 0], corners[:, 1], color="#111827", linewidth=2.5, zorder=9)
        self.ax.fill(corners[:, 0], corners[:, 1], color="#38bdf8", alpha=0.75, zorder=8)

    def draw_hover_marker(self):
        if self.hover_index is None or len(self.curve) == 0 or self.hover_index >= len(self.curve):
            return
        p = self.curve[self.hover_index]
        self.ax.scatter([p[0]], [p[1]], s=80, color="#ffffff", edgecolor="#ef4444", linewidth=2, zorder=10)

    def draw_equation_box(self, text):
        if not self.show_equation.get():
            return
        self.ax.text(
            0.015,
            0.985,
            text,
            transform=self.ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            family="Consolas",
            bbox=dict(boxstyle="round,pad=0.5", fc="#ffffff", ec="#cbd5e1", alpha=0.93),
        )

    def toggle_animation(self):
        if self.animate_vehicle.get():
            self.run_animation()
        else:
            if self.animation_after is not None:
                self.parent.after_cancel(self.animation_after)
                self.animation_after = None
            self.draw()

    def run_animation(self):
        if not self.animate_vehicle.get():
            return
        self.vehicle_t = (self.vehicle_t + 0.01) % 1.0
        self.t_slider.set(self.vehicle_t)
        self.t_readout.configure(text=f"{self.vehicle_t:.3f}")
        self.draw()
        self.animation_after = self.parent.after(35, self.run_animation)

    def snap_if_shift(self, event, old_point, new_point):
        # Tk usa diferentes máscaras em plataformas diferentes; 0x0001 costuma indicar Shift.
        if event.key == "shift" or (hasattr(event, "guiEvent") and False):
            pass
        if getattr(event, "guiEvent", None) is not None:
            pass

        # Matplotlib nem sempre expõe shift de forma uniforme. Usa event.key quando disponível.
        if getattr(event, "key", None) == "shift":
            delta = new_point - old_point
            if abs(delta[0]) >= abs(delta[1]):
                new_point[1] = old_point[1]
            else:
                new_point[0] = old_point[0]
        return new_point

    def export_csv(self):
        if len(self.curve) == 0:
            return

        path = filedialog.asksaveasfilename(
            title="Exportar curva como CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["segmento", "t", "x", "y"])
            for seg, t, p in zip(self.segment_ids, self.t_values, self.curve):
                writer.writerow([int(seg), float(t), float(p[0]), float(p[1])])

    def export_png(self):
        path = filedialog.asksaveasfilename(
            title="Exportar imagem",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        self.fig.savefig(path, dpi=180, bbox_inches="tight")

    def save_json(self):
        path = filedialog.asksaveasfilename(
            title="Salvar configuração",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return

        data = self.serialize()
        data["curve_type"] = self.name

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self):
        path = filedialog.askopenfilename(
            title="Carregar configuração",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.push_history()
        self.deserialize(data)
        self.sync_entries()
        self.draw()

    def active_segment_for_slider(self):
        return 0

    def evaluate(self, t, segment=0):
        return np.array([0.0, 0.0])

    def derivative_at(self, t, segment=0):
        return np.array([1.0, 0.0])

    def second_derivative_at(self, t, segment=0):
        return np.array([0.0, 0.0])

    def curvature_at(self, t, segment=0):
        return curvature_from_derivatives(self.derivative_at(t, segment), self.second_derivative_at(t, segment))

    def serialize(self):
        return {}

    def deserialize(self, data):
        pass

    def sync_entries(self):
        pass

    def reset(self):
        pass

    def on_press(self, event):
        pass

    def on_release(self, event):
        self.dragging = None

    def on_motion(self, event):
        self.update_hover(event)

    def draw(self, keep_hover=False):
        pass


# ============================================================
# Bézier
# ============================================================

class BezierEditor(CurveEditor):
    def __init__(self, parent, app):
        self.points = np.array([
            [0.0, 0.0],
            [2.0, 5.0],
            [6.0, 5.0],
            [8.0, 0.0],
        ], dtype=float)
        self.entries = []
        self.show_casteljau = tk.BooleanVar(value=True)

        super().__init__(parent, app, "Bézier cúbica", "#2563eb")
        self.build_panel()
        self.draw()

    def build_panel(self):
        ttk.Label(self.panel, text="Bézier cúbica", style="Section.Card.TLabel").pack(anchor="w")
        ttk.Label(
            self.panel,
            text="A curva começa em P0, termina em P3 e é influenciada por P1 e P2.",
            style="Muted.Card.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(3, 12))

        for i in range(4):
            row = ttk.Frame(self.panel, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=f"P{i}", width=4, style="Card.TLabel").pack(side=tk.LEFT)
            e = ttk.Entry(row)
            e.insert(0, fmt_point(self.points[i]))
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            e.bind("<KeyRelease>", self.update_from_entries)
            self.entries.append(e)

        ttk.Checkbutton(self.panel, text="Mostrar construção de De Casteljau", variable=self.show_casteljau, command=self.draw).pack(anchor="w", pady=(10, 0))

        self.add_common_panel()

    def update_from_entries(self, event=None):
        if self.suspend_entry_update:
            return
        try:
            new_points = self.points.copy()
            for i, e in enumerate(self.entries):
                new_points[i] = parse_point(e.get())
            self.push_history()
            self.points = new_points
            self.draw()
        except ValueError:
            pass

    def sync_entries(self):
        self.suspend_entry_update = True
        for i, e in enumerate(self.entries):
            e.delete(0, tk.END)
            e.insert(0, fmt_point(self.points[i]))
        self.suspend_entry_update = False

    def evaluate(self, t, segment=0):
        return bezier_cubic(*self.points, t)

    def derivative_at(self, t, segment=0):
        return bezier_cubic_derivative(*self.points, t)

    def second_derivative_at(self, t, segment=0):
        return bezier_cubic_second_derivative(*self.points, t)

    def draw_casteljau(self):
        if not self.show_casteljau.get():
            return

        t = float(self.t_slider.get())
        levels = de_casteljau_points(self.points, t)
        colors = ["#94a3b8", "#f97316", "#22c55e", "#facc15"]

        for idx, level in enumerate(levels[:-1]):
            if len(level) > 1:
                self.ax.plot(level[:, 0], level[:, 1], "--", color=colors[idx], linewidth=1.5, alpha=0.8)
            self.ax.scatter(level[:, 0], level[:, 1], s=32, color=colors[idx], zorder=6)

    def draw(self, keep_hover=False):
        self.ax.clear()
        self.setup_axes()

        n = max(1, int(self.segments.get()))
        t = np.linspace(0, 1, n + 1)
        self.curve = np.array([self.evaluate(float(ti)) for ti in t])
        self.t_values = t
        self.segment_ids = np.zeros(len(t), dtype=int)

        self.draw_curve_with_curvature()
        self.draw_samples()

        self.ax.plot(self.points[:, 0], self.points[:, 1], "--", color="#94a3b8", linewidth=1.5, zorder=2)
        self.ax.scatter(self.points[:, 0], self.points[:, 1], s=82, color="#ef4444", edgecolor="#ffffff", linewidth=1.4, zorder=7)

        for i, p in enumerate(self.points):
            self.ax.text(p[0] + 0.12, p[1] + 0.12, f"P{i}", fontsize=11, weight="bold", color="#0f172a")

        self.draw_casteljau()
        self.draw_t_marker()
        self.draw_hover_marker()

        self.draw_equation_box(
            "B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t)t^2 P2 + t^3 P3\n"
            "t ∈ [0, 1]"
        )

        self.canvas.draw_idle()

    def on_press(self, event):
        if event.xdata is None or event.ydata is None:
            return

        mouse = np.array([event.xdata, event.ydata])
        for i, p in enumerate(self.points):
            if np.linalg.norm(p - mouse) < 0.35:
                self.push_history()
                self.dragging = ("point", i, p.copy())
                return

    def on_motion(self, event):
        if self.dragging is not None and event.xdata is not None and event.ydata is not None:
            kind, i, original = self.dragging
            new_point = np.array([event.xdata, event.ydata])
            if getattr(event, "key", None) == "shift":
                new_point = self.snap_if_shift(event, original, new_point)
            self.points[i] = new_point
            self.sync_entries()
            self.draw()
            return

        self.update_hover(event)

    def serialize(self):
        return {
            "points": self.points.tolist(),
            "segments": int(self.segments.get()),
            "xlim": self.xlim,
            "ylim": self.ylim,
            "show_casteljau": bool(self.show_casteljau.get()),
        }

    def deserialize(self, data):
        if "points" in data:
            self.points = np.array(data["points"], dtype=float)
        self.segments.set(int(data.get("segments", self.segments.get())))
        self.xlim = data.get("xlim", self.xlim)
        self.ylim = data.get("ylim", self.ylim)
        self.show_casteljau.set(bool(data.get("show_casteljau", self.show_casteljau.get())))

    def reset(self):
        self.push_history()
        self.points = np.array([[0.0, 0.0], [2.0, 5.0], [6.0, 5.0], [8.0, 0.0]], dtype=float)
        self.xlim = [-2, 10]
        self.ylim = [-4, 8]
        self.sync_entries()
        self.draw()


# ============================================================
# Hermite
# ============================================================

class HermiteEditor(CurveEditor):
    def __init__(self, parent, app):
        self.P1 = np.array([0.0, 0.0], dtype=float)
        self.P2 = np.array([8.0, 0.0], dtype=float)
        self.M1 = np.array([3.0, 4.0], dtype=float)
        self.M2 = np.array([3.0, -4.0], dtype=float)
        self.entries = {}

        super().__init__(parent, app, "Hermite", "#ea580c")
        self.build_panel()
        self.draw()

    def build_panel(self):
        ttk.Label(self.panel, text="Hermite", style="Section.Card.TLabel").pack(anchor="w")
        ttk.Label(
            self.panel,
            text="A curva passa por P1 e P2. M1 e M2 definem as tangentes de saída e chegada.",
            style="Muted.Card.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(3, 12))

        for name, value in [("P1", self.P1), ("P2", self.P2), ("M1", self.M1), ("M2", self.M2)]:
            row = ttk.Frame(self.panel, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=name, width=4, style="Card.TLabel").pack(side=tk.LEFT)
            e = ttk.Entry(row)
            e.insert(0, fmt_point(value))
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            e.bind("<KeyRelease>", self.update_from_entries)
            self.entries[name] = e

        self.add_common_panel()

    def update_from_entries(self, event=None):
        if self.suspend_entry_update:
            return
        try:
            self.push_history()
            self.P1 = parse_point(self.entries["P1"].get())
            self.P2 = parse_point(self.entries["P2"].get())
            self.M1 = parse_point(self.entries["M1"].get())
            self.M2 = parse_point(self.entries["M2"].get())
            self.draw()
        except ValueError:
            pass

    def sync_entries(self):
        self.suspend_entry_update = True
        values = {"P1": self.P1, "P2": self.P2, "M1": self.M1, "M2": self.M2}
        for name, value in values.items():
            self.entries[name].delete(0, tk.END)
            self.entries[name].insert(0, fmt_point(value))
        self.suspend_entry_update = False

    def evaluate(self, t, segment=0):
        return hermite_curve(self.P1, self.P2, self.M1, self.M2, t)

    def derivative_at(self, t, segment=0):
        return hermite_derivative(self.P1, self.P2, self.M1, self.M2, t)

    def second_derivative_at(self, t, segment=0):
        return hermite_second_derivative(self.P1, self.P2, self.M1, self.M2, t)

    def draw(self, keep_hover=False):
        self.ax.clear()
        self.setup_axes()

        n = max(1, int(self.segments.get()))
        t = np.linspace(0, 1, n + 1)
        self.curve = np.array([self.evaluate(float(ti)) for ti in t])
        self.t_values = t
        self.segment_ids = np.zeros(len(t), dtype=int)

        M1_tip = self.P1 + self.M1
        M2_tip = self.P2 + self.M2

        self.draw_curve_with_curvature()
        self.draw_samples()

        self.ax.scatter([self.P1[0], self.P2[0]], [self.P1[1], self.P2[1]], s=86, color="#ef4444", edgecolor="#ffffff", linewidth=1.4, zorder=7)
        self.ax.scatter([M1_tip[0], M2_tip[0]], [M1_tip[1], M2_tip[1]], s=76, color="#22c55e", edgecolor="#ffffff", linewidth=1.4, zorder=7)

        self.ax.annotate("", xy=M1_tip, xytext=self.P1, arrowprops=dict(arrowstyle="->", lw=2.2, color="#22c55e"))
        self.ax.annotate("", xy=M2_tip, xytext=self.P2, arrowprops=dict(arrowstyle="->", lw=2.2, color="#22c55e"))

        for label, p in [("P1", self.P1), ("P2", self.P2), ("M1", M1_tip), ("M2", M2_tip)]:
            self.ax.text(p[0] + 0.12, p[1] + 0.12, label, fontsize=11, weight="bold", color="#0f172a")

        self.draw_t_marker()
        self.draw_hover_marker()

        self.draw_equation_box(
            "H(t) = (2t^3-3t^2+1)P1 + (t^3-2t^2+t)M1\n"
            "     + (-2t^3+3t^2)P2 + (t^3-t^2)M2"
        )

        self.canvas.draw_idle()

    def on_press(self, event):
        if event.xdata is None or event.ydata is None:
            return

        mouse = np.array([event.xdata, event.ydata])
        M1_tip = self.P1 + self.M1
        M2_tip = self.P2 + self.M2
        targets = {"P1": self.P1, "P2": self.P2, "M1": M1_tip, "M2": M2_tip}

        for name, p in targets.items():
            if np.linalg.norm(p - mouse) < 0.35:
                self.push_history()
                self.dragging = (name, p.copy())
                return

    def on_motion(self, event):
        if self.dragging is not None and event.xdata is not None and event.ydata is not None:
            name, original = self.dragging
            mouse = np.array([event.xdata, event.ydata])
            if getattr(event, "key", None) == "shift":
                mouse = self.snap_if_shift(event, original, mouse)

            if name == "P1":
                self.P1 = mouse
            elif name == "P2":
                self.P2 = mouse
            elif name == "M1":
                self.M1 = mouse - self.P1
            elif name == "M2":
                self.M2 = mouse - self.P2

            self.sync_entries()
            self.draw()
            return

        self.update_hover(event)

    def serialize(self):
        return {
            "P1": self.P1.tolist(),
            "P2": self.P2.tolist(),
            "M1": self.M1.tolist(),
            "M2": self.M2.tolist(),
            "segments": int(self.segments.get()),
            "xlim": self.xlim,
            "ylim": self.ylim,
        }

    def deserialize(self, data):
        self.P1 = np.array(data.get("P1", self.P1), dtype=float)
        self.P2 = np.array(data.get("P2", self.P2), dtype=float)
        self.M1 = np.array(data.get("M1", self.M1), dtype=float)
        self.M2 = np.array(data.get("M2", self.M2), dtype=float)
        self.segments.set(int(data.get("segments", self.segments.get())))
        self.xlim = data.get("xlim", self.xlim)
        self.ylim = data.get("ylim", self.ylim)

    def reset(self):
        self.push_history()
        self.P1 = np.array([0.0, 0.0], dtype=float)
        self.P2 = np.array([8.0, 0.0], dtype=float)
        self.M1 = np.array([3.0, 4.0], dtype=float)
        self.M2 = np.array([3.0, -4.0], dtype=float)
        self.xlim = [-2, 10]
        self.ylim = [-4, 8]
        self.sync_entries()
        self.draw()


# ============================================================
# Catmull-Rom
# ============================================================

class CatmullRomEditor(CurveEditor):
    def __init__(self, parent, app):
        self.points = [
            np.array([0.0, 0.0], dtype=float),
            np.array([2.0, 3.0], dtype=float),
            np.array([5.0, 4.0], dtype=float),
            np.array([8.0, 0.0], dtype=float),
            np.array([9.0, 3.0], dtype=float),
        ]
        self.entries = []
        self.variant = tk.StringVar(value="centripetal")
        self.closed = tk.BooleanVar(value=False)
        self.highlight_segment = tk.IntVar(value=0)
        self.point_list_frame = None

        super().__init__(parent, app, "Catmull-Rom", "#16a34a")
        self.build_panel()
        self.draw()

    def build_panel(self):
        ttk.Label(self.panel, text="Catmull-Rom", style="Section.Card.TLabel").pack(anchor="w")
        ttk.Label(
            self.panel,
            text="A curva é construída por janelas de 4 pontos e cada trecho passa pelos dois pontos centrais.",
            style="Muted.Card.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(3, 12))

        btns = ttk.Frame(self.panel, style="Card.TFrame")
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text="Adicionar ponto", command=self.add_point).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btns, text="Remover último", command=self.remove_point).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        ttk.Checkbutton(self.panel, text="Loop fechado", variable=self.closed, command=self.draw).pack(anchor="w", pady=(2, 8))

        ttk.Label(self.panel, text="Tipo", style="Card.TLabel").pack(anchor="w")
        for value, text in [("uniform", "Uniforme"), ("centripetal", "Centripetal"), ("chordal", "Chordal")]:
            ttk.Radiobutton(self.panel, text=text, value=value, variable=self.variant, command=self.draw).pack(anchor="w")
            
        ttk.Label(
            self.panel,
            text="(Recomendado: Centripetal para evitar overshoot)",
            style="Muted.Card.TLabel",
            wraplength=300
        ).pack(anchor="w", pady=(4, 8))

        ttk.Label(self.panel, text="Pontos", style="Section.Card.TLabel").pack(anchor="w", pady=(12, 6))

        self.point_list_frame = ttk.Frame(self.panel, style="Card.TFrame")
        self.point_list_frame.pack(fill=tk.BOTH, expand=True)

        self.add_common_panel()
        self.rebuild_point_entries()

    def rebuild_point_entries(self):
        for child in self.point_list_frame.winfo_children():
            child.destroy()

        self.entries = []

        for i, p in enumerate(self.points):
            row = ttk.Frame(self.point_list_frame, style="Card.TFrame")
            row.pack(fill=tk.X, pady=3)

            ttk.Label(row, text=f"P{i}", width=4, style="Card.TLabel").pack(side=tk.LEFT)

            e = ttk.Entry(row)
            e.insert(0, fmt_point(p))
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            e.bind("<KeyRelease>", self.update_from_entries)
            self.entries.append(e)

    def update_from_entries(self, event=None):
        if self.suspend_entry_update:
            return
        try:
            new_points = []
            for e in self.entries:
                new_points.append(parse_point(e.get()))
            self.push_history()
            self.points = new_points
            self.draw()
        except ValueError:
            pass

    def sync_entries(self):
        self.suspend_entry_update = True
        if len(self.entries) != len(self.points):
            self.rebuild_point_entries()
        for i, e in enumerate(self.entries):
            e.delete(0, tk.END)
            e.insert(0, fmt_point(self.points[i]))
        self.suspend_entry_update = False

    def add_point(self):
        self.push_history()
        if len(self.points) >= 2:
            delta = self.points[-1] - self.points[-2]
            if safe_norm(delta) < EPS:
                delta = np.array([1.5, 1.0])
            self.points.append(self.points[-1] + delta)
        else:
            self.points.append(np.array([0.0, 0.0]))
        self.rebuild_point_entries()
        self.draw()

    def remove_point(self):
        if len(self.points) > 4:
            self.push_history()
            self.points.pop()
            self.rebuild_point_entries()
            self.draw()

    def prepared_points(self):
        pts = [p.copy() for p in self.points]

        if self.closed.get():
            if len(pts) < 4:
                return pts
            return [pts[-1]] + pts + [pts[0], pts[1]]

        if len(pts) >= 2:
            return [pts[0]] + pts + [pts[-1]]
        return pts

    def segment_count(self):
        if self.closed.get():
            return len(self.points)
        return max(0, len(self.points) - 1)

    def get_segment_points(self, segment):
        pts = self.prepared_points()
        segment = max(0, min(segment, self.segment_count() - 1))
        return pts[segment], pts[segment + 1], pts[segment + 2], pts[segment + 3]

    def active_segment_for_slider(self):
        return max(0, min(int(self.highlight_segment.get()), max(0, self.segment_count() - 1)))

    def evaluate(self, t, segment=0):
        P0, P1, P2, P3 = self.get_segment_points(segment)
        mode = self.variant.get()

        if mode == "uniform":
            return catmull_uniform(P0, P1, P2, P3, t)

        alpha = 0.5 if mode == "centripetal" else 1.0
        return catmull_nonuniform(P0, P1, P2, P3, t, alpha=alpha)

    def derivative_at(self, t, segment=0):
        P0, P1, P2, P3 = self.get_segment_points(segment)
        mode = self.variant.get()

        if mode == "uniform":
            return catmull_uniform_derivative(P0, P1, P2, P3, t)

        return numerical_derivative(lambda u: self.evaluate(u, segment), t)

    def second_derivative_at(self, t, segment=0):
        P0, P1, P2, P3 = self.get_segment_points(segment)
        mode = self.variant.get()

        if mode == "uniform":
            return catmull_uniform_second_derivative(P0, P1, P2, P3, t)

        return numerical_second_derivative(lambda u: self.evaluate(u, segment), t)

    def draw(self, keep_hover=False):
        self.ax.clear()
        self.setup_axes()

        n = max(1, int(self.segments.get()))
        self.curve = []
        self.t_values = []
        self.segment_ids = []

        count = self.segment_count()
        active = self.active_segment_for_slider()

        for seg in range(count):
            t = np.linspace(0, 1, n + 1)
            segment_curve = np.array([self.evaluate(float(ti), seg) for ti in t])

            self.curve.extend(segment_curve)
            self.t_values.extend(t)
            self.segment_ids.extend([seg] * len(t))

            linewidth = 4.5 if seg == active else 2.7
            alpha = 1.0 if seg == active else 0.55
            self.ax.plot(segment_curve[:, 0], segment_curve[:, 1], color=self.color, linewidth=linewidth, alpha=alpha, solid_capstyle="round")

        self.curve = np.array(self.curve) if self.curve else np.empty((0, 2))
        self.t_values = np.array(self.t_values) if self.t_values else np.empty(0)
        self.segment_ids = np.array(self.segment_ids, dtype=int) if self.segment_ids else np.empty(0, dtype=int)

        # Curvatura por cima, se ligada.
        if self.show_curvature.get() and len(self.curve) > 1:
            self.draw_curve_with_curvature()

        self.draw_samples()

        pts = np.array(self.points)
        if len(pts):
            self.ax.plot(pts[:, 0], pts[:, 1], "--", color="#94a3b8", linewidth=1.5, zorder=2)
            self.ax.scatter(pts[:, 0], pts[:, 1], s=82, color="#ef4444", edgecolor="#ffffff", linewidth=1.4, zorder=7)

            for i, p in enumerate(self.points):
                self.ax.text(p[0] + 0.12, p[1] + 0.12, f"P{i}", fontsize=11, weight="bold", color="#0f172a")

        if count > 0:
            P0, P1, P2, P3 = self.get_segment_points(active)
            window = np.array([P0, P1, P2, P3])
            self.ax.plot(window[:, 0], window[:, 1], ":", color="#f59e0b", linewidth=2.2, zorder=3)
            self.ax.scatter(window[:, 0], window[:, 1], s=44, color="#f59e0b", zorder=6)

        self.draw_t_marker()
        self.draw_hover_marker()

        formula = {
            "uniform": "Catmull-Rom uniforme\nC(t)=0.5[(2P1)+(-P0+P2)t+(2P0-5P1+4P2-P3)t²+(-P0+3P1-3P2+P3)t³]",
            "centripetal": "Catmull-Rom centripetal\nusa parametrização por distância^0.5 para reduzir overshoot",
            "chordal": "Catmull-Rom chordal\nusa parametrização por distância para seguir melhor espaçamentos irregulares",
        }[self.variant.get()]

        self.draw_equation_box(
            f"{formula}\nsegmento ativo = {active}\nloop fechado = {self.closed.get()}"
        )

        self.canvas.draw_idle()

    def on_press(self, event):
        if event.xdata is None or event.ydata is None:
            return

        if event.button == 3:
            self.push_history()
            self.points.append(np.array([event.xdata, event.ydata], dtype=float))
            self.rebuild_point_entries()
            self.draw()
            return

        mouse = np.array([event.xdata, event.ydata])
        for i, p in enumerate(self.points):
            if np.linalg.norm(p - mouse) < 0.35:
                self.push_history()
                self.dragging = (i, p.copy())
                return

        idx = self.nearest_curve_index(event)
        if idx is not None and len(self.segment_ids):
            self.highlight_segment.set(int(self.segment_ids[idx]))
            self.draw()

    def on_motion(self, event):
        if self.dragging is not None and event.xdata is not None and event.ydata is not None:
            i, original = self.dragging
            new_point = np.array([event.xdata, event.ydata])
            if getattr(event, "key", None) == "shift":
                new_point = self.snap_if_shift(event, original, new_point)
            self.points[i] = new_point
            self.sync_entries()
            self.draw()
            return

        self.update_hover(event)

    def serialize(self):
        return {
            "points": [p.tolist() for p in self.points],
            "segments": int(self.segments.get()),
            "xlim": self.xlim,
            "ylim": self.ylim,
            "variant": self.variant.get(),
            "closed": bool(self.closed.get()),
            "highlight_segment": int(self.highlight_segment.get()),
        }

    def deserialize(self, data):
        if "points" in data:
            self.points = [np.array(p, dtype=float) for p in data["points"]]
        self.segments.set(int(data.get("segments", self.segments.get())))
        self.xlim = data.get("xlim", self.xlim)
        self.ylim = data.get("ylim", self.ylim)
        self.variant.set(data.get("variant", self.variant.get()))
        self.closed.set(bool(data.get("closed", self.closed.get())))
        self.highlight_segment.set(int(data.get("highlight_segment", self.highlight_segment.get())))
        self.rebuild_point_entries()

    def reset(self):
        self.push_history()
        self.points = [
            np.array([0.0, 0.0], dtype=float),
            np.array([2.0, 3.0], dtype=float),
            np.array([5.0, 4.0], dtype=float),
            np.array([8.0, 0.0], dtype=float),
            np.array([9.0, 3.0], dtype=float),
        ]
        self.variant.set("centripetal")
        self.closed.set(False)
        self.highlight_segment.set(0)
        self.xlim = [-2, 10]
        self.ylim = [-4, 8]
        self.rebuild_point_entries()
        self.draw()


# ============================================================
# Comparação
# ============================================================

class CompareEditor(CurveEditor):
    def __init__(self, parent, app):
        self.points = np.array([
            [0.0, 0.0],
            [2.0, 5.0],
            [6.0, 5.0],
            [8.0, 0.0],
        ], dtype=float)
        self.entries = []
        self.show_bezier = tk.BooleanVar(value=True)
        self.show_hermite = tk.BooleanVar(value=True)
        self.show_catmull = tk.BooleanVar(value=True)

        super().__init__(parent, app, "Comparação de curvas", "#0f172a")
        self.build_panel()
        self.draw()

    def build_panel(self):
        ttk.Label(self.panel, text="Comparação", style="Section.Card.TLabel").pack(anchor="w")
        ttk.Label(
            self.panel,
            text="Compara Bézier, Hermite e Catmull-Rom usando a mesma base visual de pontos.",
            style="Muted.Card.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(3, 12))

        for i in range(4):
            row = ttk.Frame(self.panel, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=f"P{i}", width=4, style="Card.TLabel").pack(side=tk.LEFT)
            e = ttk.Entry(row)
            e.insert(0, fmt_point(self.points[i]))
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            e.bind("<KeyRelease>", self.update_from_entries)
            self.entries.append(e)

        ttk.Checkbutton(self.panel, text="Bézier", variable=self.show_bezier, command=self.draw).pack(anchor="w", pady=(10, 0))
        ttk.Checkbutton(self.panel, text="Hermite equivalente", variable=self.show_hermite, command=self.draw).pack(anchor="w")
        ttk.Checkbutton(self.panel, text="Catmull-Rom", variable=self.show_catmull, command=self.draw).pack(anchor="w")

        self.add_common_panel()

    def update_from_entries(self, event=None):
        try:
            new_points = self.points.copy()
            for i, e in enumerate(self.entries):
                new_points[i] = parse_point(e.get())
            self.push_history()
            self.points = new_points
            self.draw()
        except ValueError:
            pass

    def sync_entries(self):
        for i, e in enumerate(self.entries):
            e.delete(0, tk.END)
            e.insert(0, fmt_point(self.points[i]))

    def hermite_values(self):
        P0, P1, P2, P3 = self.points
        return P0, P3, 3 * (P1 - P0), 3 * (P3 - P2)

    def evaluate(self, t, segment=0):
        return bezier_cubic(*self.points, t)

    def derivative_at(self, t, segment=0):
        return bezier_cubic_derivative(*self.points, t)

    def second_derivative_at(self, t, segment=0):
        return bezier_cubic_second_derivative(*self.points, t)

    def draw(self, keep_hover=False):
        self.ax.clear()
        self.setup_axes()

        n = max(1, int(self.segments.get()))
        t = np.linspace(0, 1, n + 1)

        plotted = []

        if self.show_bezier.get():
            b = np.array([bezier_cubic(*self.points, ti) for ti in t])
            self.ax.plot(b[:, 0], b[:, 1], color="#2563eb", linewidth=3, label="Bézier")
            plotted.append(b)

        if self.show_hermite.get():
            P1, P2, M1, M2 = self.hermite_values()
            h = np.array([hermite_curve(P1, P2, M1, M2, ti) for ti in t])
            self.ax.plot(h[:, 0], h[:, 1], color="#ea580c", linewidth=2.5, linestyle="--", label="Hermite equivalente")
            plotted.append(h)

        if self.show_catmull.get():
            c = np.array([catmull_uniform(*self.points, ti) for ti in t])
            self.ax.plot(c[:, 0], c[:, 1], color="#16a34a", linewidth=2.5, linestyle="-.", label="Catmull-Rom")
            plotted.append(c)

        self.curve = np.array([bezier_cubic(*self.points, ti) for ti in t])
        self.t_values = t
        self.segment_ids = np.zeros(len(t), dtype=int)

        self.ax.plot(self.points[:, 0], self.points[:, 1], ":", color="#94a3b8", linewidth=1.5)
        self.ax.scatter(self.points[:, 0], self.points[:, 1], s=82, color="#ef4444", edgecolor="#ffffff", linewidth=1.4, zorder=7)

        for i, p in enumerate(self.points):
            self.ax.text(p[0] + 0.12, p[1] + 0.12, f"P{i}", fontsize=11, weight="bold", color="#0f172a")

        self.ax.legend(loc="lower right")
        self.draw_t_marker()
        self.draw_hover_marker()
        self.draw_equation_box("Comparação visual: mesma base de pontos, comportamentos diferentes.")
        self.canvas.draw_idle()

    def on_press(self, event):
        if event.xdata is None or event.ydata is None:
            return

        mouse = np.array([event.xdata, event.ydata])
        for i, p in enumerate(self.points):
            if np.linalg.norm(p - mouse) < 0.35:
                self.push_history()
                self.dragging = (i, p.copy())
                return

    def on_motion(self, event):
        if self.dragging is not None and event.xdata is not None and event.ydata is not None:
            i, original = self.dragging
            new_point = np.array([event.xdata, event.ydata])
            if getattr(event, "key", None) == "shift":
                new_point = self.snap_if_shift(event, original, new_point)
            self.points[i] = new_point
            self.sync_entries()
            self.draw()
            return

        self.update_hover(event)

    def serialize(self):
        return {
            "points": self.points.tolist(),
            "segments": int(self.segments.get()),
            "xlim": self.xlim,
            "ylim": self.ylim,
        }

    def deserialize(self, data):
        if "points" in data:
            self.points = np.array(data["points"], dtype=float)
        self.segments.set(int(data.get("segments", self.segments.get())))
        self.xlim = data.get("xlim", self.xlim)
        self.ylim = data.get("ylim", self.ylim)

    def reset(self):
        self.push_history()
        self.points = np.array([[0.0, 0.0], [2.0, 5.0], [6.0, 5.0], [8.0, 0.0]], dtype=float)
        self.xlim = [-2, 10]
        self.ylim = [-4, 8]
        self.sync_entries()
        self.draw()


# ============================================================
# App
# ============================================================

class CurveApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Laboratório Interativo de Curvas Paramétricas")
        self.root.geometry("1400x880")
        self.root.minsize(1180, 760)

        apply_theme(self.root)

        header = ttk.Frame(self.root, padding=(18, 14))
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="Laboratório Interativo de Curvas Paramétricas",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Bézier, Hermite, Catmull-Rom e comparação visual. Arraste pontos, edite valores, ajuste t, exporte e anime o movimento.",
            foreground="#475569",
        ).pack(anchor="w", pady=(4, 0))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        self.tabs = {}

        self.add_tab("Bézier cúbica", BezierEditor)
        self.add_tab("Hermite", HermiteEditor)
        self.add_tab("Catmull-Rom", CatmullRomEditor)
        self.add_tab("Comparação", CompareEditor)

    def add_tab(self, title, editor_cls):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        self.tabs[title] = editor_cls(frame, self)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CurveApp()
    app.run()
