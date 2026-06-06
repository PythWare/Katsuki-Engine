import hashlib, math, os, random
import tkinter as tk
from dataclasses import dataclass
from io import BytesIO
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageTk

from .katsuki_gauntlets import BLAST_THEME, ModManagerLogic, WinMMAudioPlayer, apply_lilac_to_root, log

BG = BLAST_THEME["bg"]
BG_ALT = BLAST_THEME["bg_alt"]
PANEL = BLAST_THEME["panel"]
PANEL_ALT = BLAST_THEME["panel_alt"]
PANEL_SOFT = BLAST_THEME["panel_soft"]
TEXT = BLAST_THEME["text"]
TEXT_MUTED = BLAST_THEME["text_muted"]
TEXT_DARK = BLAST_THEME["text_dark"]
ACCENT = BLAST_THEME["accent"]
ACCENT_BRIGHT = BLAST_THEME["accent_bright"]
ACCENT_DEEP = BLAST_THEME["accent_deep"]
GREEN = BLAST_THEME["accent_green"]
GREEN_BRIGHT = BLAST_THEME["accent_green_bright"]
DANGER = BLAST_THEME["danger"]
METAL = BLAST_THEME["metal"]
BORDER = BLAST_THEME["border"]
PREVIEW_BG = BLAST_THEME["preview_bg"]

MOD_GENRES = ["All", "Texture", "Audio", "Model", "Overhaul"]
BLAST_ZONES = {
    "All": {"center": (0.0, -980.0), "label": "Ground Zero", "accent": ACCENT_BRIGHT, "text": "Universal payloads and cross-system files."},
    "Texture": {"center": (-1500.0, -120.0), "label": "Spark Layer", "accent": ACCENT, "text": "Visual swaps, UI edits, and texture detonations."},
    "Audio": {"center": (-520.0, 1040.0), "label": "Blast Echo", "accent": GREEN_BRIGHT, "text": "Music, SFX, and embedded audio payloads."},
    "Model": {"center": (1460.0, -90.0), "label": "Shrapnel Forge", "accent": METAL, "text": "Character, mesh, and model file changes."},
    "Overhaul": {"center": (780.0, 1090.0), "label": "Howitzer Core", "accent": ACCENT_DEEP, "text": "Large installers and major gameplay overhauls."},
}


def stable_hash(text: str) -> int:
    return int(hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:8], 16)


def style_button(button: tk.Button, role: str = "secondary"):
    palette = {
        "primary": (ACCENT, TEXT_DARK, ACCENT_BRIGHT, TEXT_DARK),
        "success": (GREEN, TEXT, GREEN_BRIGHT, TEXT_DARK),
        "danger": (DANGER, TEXT, ACCENT_DEEP, TEXT),
        "ghost": (PANEL_ALT, TEXT, PANEL_SOFT, TEXT),
        "secondary": (PANEL_SOFT, TEXT, ACCENT, TEXT_DARK),
    }
    bg, fg, active_bg, active_fg = palette.get(role, palette["secondary"])
    button.configure(
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=active_fg,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        cursor="hand2",
        padx=14,
        pady=8,
    )


@dataclass
class BlastModRecord:
    path: str
    filename: str
    title: str
    author: str
    version: str
    description: str
    genre: str
    mode: str
    package_type: str
    active: bool
    image_count: int
    has_audio: bool
    header: dict
    parse_error: str = ""
    x: float = 0.0
    y: float = 0.0


class BlastMapCanvas(tk.Canvas):
    def __init__(self, parent: tk.Misc, controller: "BlastChamberWindow"):
        super().__init__(parent, bg=PREVIEW_BG, highlightthickness=0, bd=0, relief="flat")
        self.controller = controller
        self.camera_x = 0.0
        self.camera_y = 120.0
        self.zoom = 0.24
        self.dragging = False
        self.last_drag = (0, 0)
        self.item_to_mod: Dict[int, BlastModRecord] = {}
        rnd = random.Random(2718)
        self.embers = [(rnd.uniform(-2900, 2900), rnd.uniform(-2400, 2400), rnd.choice((1, 1, 2, 2, 3))) for _ in range(280)]
        self.bind("<Configure>", lambda _e: self.render())
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-Button-1>", self.on_double_click)
        self.bind("<MouseWheel>", self.on_mousewheel)

    def fit_overview(self):
        self.camera_x = 0.0
        self.camera_y = 120.0
        self.zoom = 0.24
        self.render()

    def focus_world(self, wx: float, wy: float, zoom: Optional[float] = None):
        self.camera_x = wx
        self.camera_y = wy
        if zoom is not None:
            self.zoom = max(0.18, min(1.45, zoom))
        self.render()

    def world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        return ((x - self.camera_x) * self.zoom + (width / 2), (y - self.camera_y) * self.zoom + (height / 2))

    def screen_to_world(self, x: float, y: float) -> Tuple[float, float]:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        return ((x - (width / 2)) / self.zoom + self.camera_x, (y - (height / 2)) / self.zoom + self.camera_y)

    def zoom_at(self, sx: float, sy: float, factor: float):
        old_zoom = self.zoom
        before_x, before_y = self.screen_to_world(sx, sy)
        self.zoom = max(0.18, min(1.45, old_zoom * factor))
        if abs(old_zoom - self.zoom) < 0.001:
            return
        after_x, after_y = self.screen_to_world(sx, sy)
        self.camera_x += before_x - after_x
        self.camera_y += before_y - after_y
        self.render()

    def on_mousewheel(self, event):
        self.zoom_at(event.x, event.y, 1.12 if event.delta > 0 else (1 / 1.12))

    def on_press(self, event):
        self.dragging = False
        self.last_drag = (event.x, event.y)

    def on_drag(self, event):
        self.dragging = True
        dx = event.x - self.last_drag[0]
        dy = event.y - self.last_drag[1]
        self.last_drag = (event.x, event.y)
        self.camera_x -= dx / self.zoom
        self.camera_y -= dy / self.zoom
        self.render()

    def on_release(self, event):
        if not self.dragging:
            self.pick_mod(event.x, event.y)

    def on_double_click(self, event):
        mod = self.pick_mod(event.x, event.y, select=False)
        if mod:
            self.focus_world(mod.x, mod.y, zoom=max(0.72, self.zoom))

    def pick_mod(self, sx: float, sy: float, select: bool = True) -> Optional[BlastModRecord]:
        for item_id in reversed(self.find_overlapping(sx - 6, sy - 6, sx + 6, sy + 6)):
            mod = self.item_to_mod.get(item_id)
            if mod:
                if select:
                    self.controller.select_mod(mod)
                return mod
        if select:
            self.controller.clear_mod_selection()
        return None

    def render(self):
        self.delete("all")
        self.item_to_mod.clear()
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.create_rectangle(0, 0, width, height, fill=PREVIEW_BG, outline="")
        for idx in range(-6, 18):
            start_x = idx * 96
            self.create_line(start_x, 0, start_x - height, height, fill="#161210", width=2)

        cx, cy = self.world_to_screen(0.0, 120.0)
        for radius, color in ((1600, "#2C1B13"), (1020, "#3B2418"), (520, "#4A2D1D")):
            r = radius * self.zoom
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=max(1, int(self.zoom * 7)))
        self.create_line(cx - 120, cy - 120, cx + 120, cy + 120, fill="#4C2A19", width=3)
        self.create_line(cx - 120, cy + 120, cx + 120, cy - 120, fill="#4C2A19", width=3)

        for x, y, size in self.embers:
            sx, sy = self.world_to_screen(x, y)
            if -8 <= sx <= width + 8 and -8 <= sy <= height + 8:
                color = ACCENT_BRIGHT if (stable_hash(f"{x:.2f}:{y:.2f}") % 11) < 3 else "#72513A"
                self.create_oval(sx - size, sy - size, sx + size, sy + size, fill=color, outline="")

        current_filter = self.controller.current_filter
        for genre in MOD_GENRES:
            if current_filter != "__all__" and genre != current_filter:
                continue
            meta = BLAST_ZONES[genre]
            zx, zy = self.world_to_screen(*meta["center"])
            label_offset = max(64, 180 * self.zoom)
            desc_offset = max(78, 196 * self.zoom)
            self.create_text(zx, zy - label_offset, text=meta["label"], fill=meta["accent"], font=("Impact", max(16, int(12 + self.zoom * 20))))
            if self.zoom >= 0.24:
                self.create_text(zx, zy + desc_offset, text=meta["text"], fill=TEXT_MUTED, width=260, font=("Segoe UI", 9))
            if self.zoom >= 0.22:
                for idx in range(3):
                    phase = stable_hash(f"{genre}:{idx}") % 360
                    ang = math.radians(phase + (self.controller.hero_phase * (4 + idx)))
                    dist = 26 + idx * 16
                    sx = zx + math.cos(ang) * dist
                    sy = zy - label_offset * 0.48 + math.sin(ang) * 11
                    radius = 1 + (idx % 2)
                    self.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, fill=meta["accent"], outline="")

        for mod in self.controller.visible_mods():
            zone = BLAST_ZONES.get(mod.genre, BLAST_ZONES["All"])
            zx, zy = self.world_to_screen(*zone["center"])
            sx, sy = self.world_to_screen(mod.x, mod.y)
            if not (-40 <= sx <= width + 40 and -40 <= sy <= height + 40):
                continue
            self.create_line(zx, zy, sx, sy, fill=GREEN_BRIGHT if mod.active else "#4A2F20", width=1)

            if mod.parse_error:
                fill, outline = "#3B1919", DANGER
            elif mod.active:
                fill, outline = GREEN, GREEN_BRIGHT
            else:
                fill, outline = PANEL_SOFT, zone["accent"]

            radius = 11 if mod.active else 9
            if self.controller.current_mod and self.controller.current_mod.filename == mod.filename:
                halo = radius + 9
                self.create_oval(sx - halo, sy - halo, sx + halo, sy + halo, outline=ACCENT_BRIGHT, width=2)

            if mod.package_type == "installer":
                item = self.create_polygon(
                    sx, sy - radius - 4,
                    sx + radius + 4, sy,
                    sx, sy + radius + 4,
                    sx - radius - 4, sy,
                    fill=fill,
                    outline=outline,
                    width=2,
                )
            else:
                item = self.create_oval(sx - radius, sy - radius, sx + radius, sy + radius, fill=fill, outline=outline, width=2)
            self.item_to_mod[item] = mod
            core = self.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill=ACCENT_BRIGHT if not mod.active else BLAST_THEME["field"], outline="")
            self.item_to_mod[core] = mod
            if self.zoom >= 0.58:
                label = self.create_text(sx, sy - 22, text=mod.title[:24], fill=TEXT, font=("Segoe UI", 9, "bold"))
                self.item_to_mod[label] = mod

        if not self.controller.mod_records:
            self.create_text(width / 2, height / 2 - 10, text="No mods in the blast chamber", fill=TEXT, font=("Impact", 24))
            self.create_text(width / 2, height / 2 + 24, text="Drop .aot2m or .aot2mi files into the Mods folder to populate this field.", fill=TEXT_MUTED, font=("Segoe UI", 11))


class BlastChamberWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Katsuki Mod Manager")
        self.geometry("1520x1000")
        self.minsize(1280, 860)
        apply_lilac_to_root(self)

        self.logic = ModManagerLogic()
        self.audio_player = WinMMAudioPlayer(log=log)
        self.music_enabled = tk.BooleanVar(value=True)
        self.search_var = tk.StringVar(value="")
        self.current_filter = "__all__"
        self.current_mod: Optional[BlastModRecord] = None
        self.current_mod_data = None
        self.image_index = 0
        self.preview_photo = None
        self.mod_records: List[BlastModRecord] = []
        self.filter_buttons: Dict[str, tk.Button] = {}

        self.status_var = tk.StringVar(value="Blast chamber ready.")
        self.stats_var = tk.StringVar(value="0 mods loaded")
        self.audio_var = tk.StringVar(value="Embedded audio idle")
        self.hero_phase = 0.0
        self.hero_after_id = None
        self.hero_bursts = [
            {"x": 0.14, "y": 0.58, "size": 56, "speed": 0.19, "phase": 0.1, "color": ACCENT},
            {"x": 0.44, "y": 0.38, "size": 74, "speed": 0.23, "phase": 1.1, "color": ACCENT_BRIGHT},
            {"x": 0.70, "y": 0.52, "size": 62, "speed": 0.17, "phase": 2.0, "color": ACCENT_DEEP},
            {"x": 0.90, "y": 0.34, "size": 88, "speed": 0.21, "phase": 0.7, "color": ACCENT_BRIGHT},
        ]

        self.build_ui()
        self.refresh_mod_list()
        self.animate_hero()

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.hero = tk.Canvas(self, height=148, bg=BG, highlightthickness=0)
        self.hero.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self.hero.bind("<Configure>", self.draw_hero)

        toolbar = tk.Frame(self, bg=PANEL, padx=14, pady=12, highlightthickness=1, highlightbackground=BORDER)
        toolbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        toolbar.grid_columnconfigure(1, weight=1)

        left = tk.Frame(toolbar, bg=PANEL)
        left.grid(row=0, column=0, sticky="w")
        for text, handler, role in [
            ("Overview", self.show_overview, "secondary"),
            ("Rescan Chamber", self.refresh_mod_list, "ghost"),
            ("Disable All Mods", self.hard_reset_mods, "danger"),
        ]:
            btn = tk.Button(left, text=text, command=handler)
            btn.pack(side="left", padx=(0, 8))
            style_button(btn, role)

        right = tk.Frame(toolbar, bg=PANEL)
        right.grid(row=0, column=1, sticky="ew")
        right.grid_columnconfigure(1, weight=1)
        tk.Label(right, text="Search", bg=PANEL, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(8, 8))
        self.search_entry = tk.Entry(
            right,
            textvariable=self.search_var,
            font=("Segoe UI", 11),
            bg=BLAST_THEME["field"],
            fg=TEXT_DARK,
            insertbackground=ACCENT_DEEP,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), ipady=4)
        self.search_var.trace_add("write", lambda *_: self.on_search_change())
        self.search_entry.bind("<Return>", lambda _e: self.focus_first_match())

        audio_toggle = tk.Checkbutton(
            right,
            text="Play Mod Audio",
            variable=self.music_enabled,
            command=self.refresh_audio_state,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=ACCENT_BRIGHT,
            selectcolor=PANEL_SOFT,
            bd=0,
            highlightthickness=0,
        )
        audio_toggle.grid(row=0, column=2, sticky="e")

        filter_row = tk.Frame(toolbar, bg=PANEL)
        filter_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        for label, value in [("All Mods", "__all__"), ("Universal", "All"), ("Texture", "Texture"), ("Audio", "Audio"), ("Model", "Model"), ("Overhaul", "Overhaul")]:
            btn = tk.Button(filter_row, text=label, command=lambda v=value: self.set_filter(v))
            btn.pack(side="left", padx=4)
            self.filter_buttons[value] = btn
        tk.Label(filter_row, textvariable=self.stats_var, bg=PANEL, fg=TEXT_MUTED, font=("Segoe UI", 9, "italic")).pack(side="right")
        self.update_filter_buttons()

        content = tk.Frame(self, bg=BG)
        content.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.canvas = BlastMapCanvas(content, self)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.build_scrollable_detail_shell(content)
        self.build_detail_panel()
        self.bind_detail_scroll_events(self.detail)

        footer = tk.Frame(self, bg=BG_ALT, height=38)
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        footer.grid_propagate(False)
        self.status_label = tk.Label(footer, textvariable=self.status_var, bg=BG_ALT, fg=TEXT, anchor="w", font=("Segoe UI", 9))
        self.status_label.pack(side="left", padx=14, pady=8)
        tk.Label(footer, textvariable=self.audio_var, bg=BG_ALT, fg=TEXT_MUTED, anchor="e", font=("Segoe UI", 9)).pack(side="right", padx=14, pady=8)

    def build_scrollable_detail_shell(self, parent: tk.Misc):
        self.detail_shell = tk.Frame(parent, bg=PANEL_ALT, width=430, highlightthickness=1, highlightbackground=BORDER)
        self.detail_shell.grid(row=0, column=1, sticky="ns")
        self.detail_shell.grid_propagate(False)
        self.detail_shell.grid_rowconfigure(0, weight=1)
        self.detail_shell.grid_columnconfigure(0, weight=1)

        self.detail_canvas = tk.Canvas(self.detail_shell, bg=PANEL_ALT, highlightthickness=0, bd=0)
        self.detail_canvas.grid(row=0, column=0, sticky="nsew")
        self.detail_scrollbar = tk.Scrollbar(self.detail_shell, orient="vertical", command=self.detail_canvas.yview, bg=PANEL_SOFT, troughcolor=PANEL, activebackground=ACCENT)
        self.detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.detail_canvas.configure(yscrollcommand=self.detail_scrollbar.set)

        self.detail = tk.Frame(self.detail_canvas, bg=PANEL_ALT)
        self.detail_window = self.detail_canvas.create_window((0, 0), window=self.detail, anchor="nw")
        self.detail.bind("<Configure>", self.refresh_detail_scroll_region)
        self.detail_canvas.bind("<Configure>", self.resize_detail_scroll_window)

    def refresh_detail_scroll_region(self, _event=None):
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox("all"))

    def resize_detail_scroll_window(self, event):
        self.detail_canvas.itemconfigure(self.detail_window, width=event.width)

    def bind_detail_scroll_events(self, widget: tk.Misc):
        widget.bind("<MouseWheel>", self.on_detail_mousewheel, add="+")
        widget.bind("<Button-4>", self.on_detail_mousewheel, add="+")
        widget.bind("<Button-5>", self.on_detail_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_detail_scroll_events(child)

    def on_detail_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            self.detail_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.detail_canvas.yview_scroll(1, "units")
        elif event.delta:
            steps = max(1, abs(event.delta) // 120)
            self.detail_canvas.yview_scroll((-1 if event.delta > 0 else 1) * steps, "units")
        return "break"

    def scroll_detail_to_top(self):
        if hasattr(self, "detail_canvas"):
            self.detail_canvas.yview_moveto(0)

    def build_detail_panel(self):
        head = tk.Frame(self.detail, bg=PANEL_ALT)
        head.pack(fill="x", padx=18, pady=(18, 12))
        tk.Label(head, text="Mod Strike Analysis", bg=PANEL_ALT, fg=ACCENT_BRIGHT, font=("Impact", 22), anchor="w").pack(fill="x")
        tk.Label(head, text="Select a blast node to inspect mods, compatibility state, and launch actions.", bg=PANEL_ALT, fg=TEXT_MUTED, wraplength=360, justify="left", anchor="w", font=("Segoe UI", 9)).pack(fill="x", pady=(6, 0))

        self.lbl_title = tk.Label(self.detail, text="", bg=PANEL_ALT, fg=TEXT, font=("Segoe UI", 18, "bold"), wraplength=370, justify="left", anchor="w")
        self.lbl_title.pack(fill="x", padx=18)
        self.lbl_author = tk.Label(self.detail, text="", bg=PANEL_ALT, fg=TEXT_MUTED, font=("Segoe UI", 10), justify="left", anchor="w")
        self.lbl_author.pack(fill="x", padx=18, pady=(4, 8))

        chips = tk.Frame(self.detail, bg=PANEL_ALT)
        chips.pack(fill="x", padx=18, pady=(0, 12))
        self.lbl_version_chip = tk.Label(chips, text="Version: ", bg=PANEL_SOFT, fg=TEXT, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        self.lbl_version_chip.pack(side="left", padx=(0, 6))
        self.lbl_genre_chip = tk.Label(chips, text="Zone: ", bg=PANEL_SOFT, fg=TEXT, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        self.lbl_genre_chip.pack(side="left", padx=6)
        self.lbl_mode_chip = tk.Label(chips, text="Mode: ", bg=PANEL_SOFT, fg=TEXT, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        self.lbl_mode_chip.pack(side="left", padx=6)
        self.lbl_image_count = tk.Label(chips, text="Images: 0/0", bg=PANEL_SOFT, fg=TEXT, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        self.lbl_image_count.pack(side="right")

        tk.Label(self.detail, text="Description", bg=PANEL_ALT, fg=ACCENT_BRIGHT, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=18)
        desc_frame = tk.Frame(self.detail, bg=PANEL_ALT)
        desc_frame.pack(fill="x", padx=18, pady=(6, 12))
        self.txt_desc = tk.Text(desc_frame, height=5, wrap="word", font=("Segoe UI", 10), bg=BLAST_THEME["field"], fg=TEXT_DARK, insertbackground=ACCENT_DEEP, relief="flat", bd=0, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        self.txt_desc.pack(side="left", fill="x", expand=True)
        desc_scroll = tk.Scrollbar(desc_frame, orient="vertical", command=self.txt_desc.yview, bg=PANEL_SOFT, troughcolor=PANEL, activebackground=ACCENT)
        desc_scroll.pack(side="right", fill="y")
        self.txt_desc.configure(yscrollcommand=desc_scroll.set)
        self.txt_desc.config(state="disabled")

        preview_shell = tk.Frame(self.detail, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        preview_shell.pack(fill="x", padx=18, pady=(0, 12))
        top = tk.Frame(preview_shell, bg=PANEL)
        top.pack(fill="x", padx=12, pady=(10, 8))
        tk.Label(top, text="Preview Gallery", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        self.preview_state = tk.Label(top, text="No visual data", bg=PANEL, fg=TEXT_MUTED, font=("Segoe UI", 9))
        self.preview_state.pack(side="right")
        self.img_frame = tk.Frame(preview_shell, bg=PREVIEW_BG, highlightthickness=1, highlightbackground="#2A1E17", height=250)
        self.img_frame.pack(fill="x", padx=12, pady=(0, 10))
        self.img_frame.pack_propagate(False)
        self.img_label = tk.Label(self.img_frame, bg=PREVIEW_BG, fg=ACCENT_BRIGHT, font=("Consolas", 11), justify="center")
        self.img_label.pack(fill="both", expand=True)
        nav = tk.Frame(preview_shell, bg=PANEL)
        nav.pack(fill="x", padx=12, pady=(0, 12))
        self.btn_prev = tk.Button(nav, text="Prev Image", command=lambda: self.cycle_image(-1))
        self.btn_prev.pack(side="left")
        self.btn_next = tk.Button(nav, text="Next Image", command=lambda: self.cycle_image(1))
        self.btn_next.pack(side="left", padx=(8, 0))
        style_button(self.btn_prev, "ghost")
        style_button(self.btn_next, "ghost")

        actions = tk.Frame(self.detail, bg=PANEL_ALT)
        actions.pack(fill="x", padx=18, pady=(0, 10))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        self.btn_apply = tk.Button(actions, text="Enable Mod", command=self.apply_selected_mod, font=("Segoe UI", 10, "bold"))
        self.btn_apply.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        self.btn_disable = tk.Button(actions, text="Disable Mod", command=self.disable_selected_mod)
        self.btn_disable.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))
        self.btn_folder = tk.Button(actions, text="Reveal Package Folder", command=self.reveal_selected_mod)
        self.btn_folder.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.btn_clear = tk.Button(actions, text="Clear Selection", command=self.clear_mod_selection)
        self.btn_clear.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        style_button(self.btn_apply, "primary")
        style_button(self.btn_disable, "danger")
        style_button(self.btn_folder, "ghost")
        style_button(self.btn_clear, "secondary")

        self.clear_mod_selection()

    def draw_hero(self, _event=None):
        width = max(1, self.hero.winfo_width())
        height = max(1, self.hero.winfo_height())
        self.hero.delete("all")
        self.hero.create_rectangle(0, 0, width, height, fill=BG_ALT, outline="")
        for idx in range(18):
            x = (idx * 110 + 44) % width
            self.hero.create_line(x, 0, x - 76, height, fill="#201711", width=2)
        for burst in self.hero_bursts:
            self.draw_hero_burst(width, height, burst)

        for idx in range(18):
            pulse = self.hero_phase * 0.6 + idx * 0.72
            ember_x = (width * ((idx * 0.062) % 1.0)) + math.sin(pulse) * 42
            ember_y = 18 + ((idx * 13) % max(24, height - 30)) + math.cos(pulse * 1.3) * 8
            radius = 1 + (idx % 3)
            fill = ACCENT_BRIGHT if idx % 4 else ACCENT
            self.hero.create_oval(ember_x - radius, ember_y - radius, ember_x + radius, ember_y + radius, fill=fill, outline="")

        self.hero.create_text(34, 28, anchor="nw", text="Katsuki Mod Manager", fill=TEXT, font=("Impact", 28))
        self.hero.create_text(36, 74, anchor="nw", text="A Bakugo inspired detonation map Mod Manager.", fill=TEXT_MUTED, font=("Segoe UI", 11))
        self.hero.create_text(width - 22, height - 18, anchor="se", text="Drag to pan. Scroll to zoom. Click a blast node to inspect it.", fill=TEXT_MUTED, font=("Segoe UI", 9, "italic"))

    def burst_points(self, cx: float, cy: float, inner: float, outer: float, arms: int, angle_offset: float, stretch: float = 0.74) -> List[float]:
        points: List[float] = []
        for idx in range(arms * 2):
            angle = angle_offset + (math.pi * idx / arms)
            radius = outer if idx % 2 == 0 else inner
            points.extend([cx + math.cos(angle) * radius, cy + math.sin(angle) * radius * stretch])
        return points

    def draw_hero_burst(self, width: int, height: int, burst: dict):
        cx = width * burst["x"] + math.sin(self.hero_phase * burst["speed"] + burst["phase"]) * 26
        cy = height * burst["y"] + math.cos(self.hero_phase * (burst["speed"] + 0.05) + burst["phase"]) * 8
        phase = self.hero_phase * burst["speed"] + burst["phase"]
        outer = burst["size"] * (1.0 + 0.14 * math.sin(phase))
        mid = outer * 0.62
        inner = outer * 0.34

        glow_r = outer * 1.16
        self.hero.create_oval(cx - glow_r, cy - glow_r * 0.7, cx + glow_r, cy + glow_r * 0.7, fill="#2A160E", outline="")
        self.hero.create_polygon(self.burst_points(cx, cy, mid, outer, 8, phase), fill=burst["color"], outline="")
        self.hero.create_polygon(self.burst_points(cx, cy, inner, mid * 0.96, 7, -phase * 1.15), fill=ACCENT_BRIGHT, outline="")
        self.hero.create_oval(cx - inner * 0.56, cy - inner * 0.42, cx + inner * 0.56, cy + inner * 0.42, fill=TEXT, outline="")
        self.hero.create_oval(cx - inner * 0.34, cy - inner * 0.24, cx + inner * 0.34, cy + inner * 0.24, fill=ACCENT_BRIGHT, outline="")

        for idx in range(5):
            angle = phase + idx * (2 * math.pi / 5)
            streak = outer * (1.2 + 0.18 * math.sin(phase + idx))
            x2 = cx + math.cos(angle) * streak
            y2 = cy + math.sin(angle) * streak * 0.7
            self.hero.create_line(cx, cy, x2, y2, fill=burst["color"], width=2)

    def animate_hero(self):
        self.hero_phase += 0.48
        if self.winfo_exists():
            self.draw_hero()
            self.hero_after_id = self.after(80, self.animate_hero)

    def visible_mods(self) -> List[BlastModRecord]:
        query = self.search_var.get().strip().lower()
        visible = []
        for mod in self.mod_records:
            if self.current_filter != "__all__" and mod.genre != self.current_filter:
                continue
            if query:
                hay = " ".join([mod.filename, mod.title, mod.author, mod.version, mod.genre, mod.mode, mod.package_type]).lower()
                if query not in hay:
                    continue
            visible.append(mod)
        return visible

    def update_stats(self):
        total = len(self.mod_records)
        visible = len(self.visible_mods())
        active = sum(1 for mod in self.mod_records if mod.active)
        self.stats_var.set("0 mods loaded" if total == 0 else f"{visible}/{total} visible | {active} active")

    def layout_mods(self):
        grouped: Dict[str, List[BlastModRecord]] = {genre: [] for genre in MOD_GENRES}
        for mod in sorted(self.mod_records, key=lambda item: (item.genre, item.title.lower(), item.filename.lower())):
            grouped.setdefault(mod.genre, []).append(mod)
        for genre, items in grouped.items():
            center_x, center_y = BLAST_ZONES.get(genre, BLAST_ZONES["All"])["center"]
            cursor = 0
            ring = 0
            while cursor < len(items):
                ring_capacity = 1 if len(items) == 1 and ring == 0 else 6 + ring * 4
                chunk = items[cursor: cursor + ring_capacity]
                radius = 0 if len(items) == 1 and ring == 0 else 190 + ring * 118
                for idx, mod in enumerate(chunk):
                    if radius == 0:
                        mod.x, mod.y = center_x, center_y
                    else:
                        angle = (2 * math.pi * idx / max(1, len(chunk))) + ((stable_hash(mod.filename) % 19) * 0.025)
                        rx = radius + (stable_hash(mod.filename) % 44) - 20
                        ry = radius * 0.72 + (stable_hash(mod.title) % 28) - 12
                        mod.x = center_x + math.cos(angle) * rx
                        mod.y = center_y + math.sin(angle) * ry
                cursor += ring_capacity
                ring += 1

    def refresh_mod_list(self, *_args):
        selected_name = self.current_mod.filename if self.current_mod else None
        os.makedirs("Mods", exist_ok=True)
        applied_mods = self.logic.get_applied_mods()
        mod_files = sorted([name for name in os.listdir("Mods") if name.lower().endswith((".aot2m", ".aot2mi"))], key=str.lower)

        self.mod_records = []
        for mod_file in mod_files:
            mod_path = os.path.join("Mods", mod_file)
            active = mod_file in applied_mods
            header = self.logic.get_mod_header(mod_path)
            if not header:
                self.mod_records.append(BlastModRecord(mod_path, mod_file, os.path.splitext(mod_file)[0].replace("_", " "), "Unknown", "-", "This package could not be parsed by the Katsuki manager.", "All", "Unknown", "standard", active, 0, False, {}, "Header parse failed"))
                continue
            meta = header.get("meta", {})
            genre = meta.get("genre", "All")
            if genre not in MOD_GENRES:
                genre = "All"
            title = meta.get("name") or os.path.splitext(mod_file)[0].replace("_", " ")
            self.mod_records.append(
                BlastModRecord(
                    mod_path,
                    mod_file,
                    title,
                    meta.get("author", "Unknown"),
                    meta.get("version", "-"),
                    meta.get("description", ""),
                    genre,
                    "Release" if header.get("is_release", True) else "Debug",
                    header.get("type", "standard"),
                    active,
                    len(header.get("images", [])),
                    bool(header.get("audio")),
                    header,
                )
            )

        self.layout_mods()
        self.update_stats()
        if selected_name:
            match = next((mod for mod in self.mod_records if mod.filename == selected_name), None)
            if match:
                self.select_mod(match, focus=False)
            else:
                self.clear_mod_selection()
        else:
            self.clear_mod_selection()
        self.canvas.render()
        self.set_status("Blast chamber synchronized.", TEXT_MUTED)

    def update_filter_buttons(self):
        for key, button in self.filter_buttons.items():
            if key == self.current_filter:
                style_button(button, "primary")
            elif key == "Audio":
                style_button(button, "success")
            else:
                style_button(button, "ghost")

    def set_filter(self, value: str):
        self.current_filter = value
        self.update_filter_buttons()
        self.update_stats()
        if value == "__all__":
            self.show_overview()
            return
        zone = BLAST_ZONES.get(value)
        if zone:
            self.canvas.focus_world(zone["center"][0], zone["center"][1], zoom=max(0.36, self.canvas.zoom))
        self.canvas.render()

    def show_overview(self):
        self.canvas.fit_overview()
        self.canvas.render()

    def on_search_change(self):
        self.update_stats()
        self.canvas.render()
        visible = self.visible_mods()
        if len(visible) == 1 and self.search_var.get().strip():
            self.select_mod(visible[0], focus=False)

    def focus_first_match(self):
        visible = self.visible_mods()
        if visible:
            self.select_mod(visible[0])

    def select_mod(self, mod: BlastModRecord, focus: bool = True):
        self.current_mod = mod
        self.current_mod_data = mod.header
        self.image_index = 0
        self.lbl_title.config(text=mod.title)
        self.lbl_author.config(text=f"Package: {mod.filename}\nAuthor: {mod.author}")
        self.lbl_version_chip.config(text=f"Version: {mod.version or '-'}")
        self.lbl_genre_chip.config(text=f"Zone: {mod.genre}")
        self.lbl_mode_chip.config(text=f"Mode: {mod.mode}")
        self.lbl_image_count.config(text=f"Images: {1 if mod.image_count else 0}/{mod.image_count}")
        self.preview_state.config(text=f"{mod.package_type.title()} payload")
        self.txt_desc.config(state="normal")
        self.txt_desc.delete("1.0", tk.END)
        desc = mod.description or "No description provided."
        if mod.parse_error:
            desc = f"{desc}\n\nParse note: {mod.parse_error}"
        self.txt_desc.insert("1.0", desc)
        self.txt_desc.config(state="disabled")
        self.btn_apply.config(text="Launch Installer Wizard" if mod.package_type == "installer" else "Enable Mod", command=self.apply_selected_mod, state="disabled" if mod.parse_error else "normal")
        self.btn_disable.config(state="normal")
        self.btn_folder.config(state="normal")
        self.update_image_display()
        self.refresh_audio_state()
        self.scroll_detail_to_top()
        self.canvas.render()
        if focus:
            self.canvas.focus_world(mod.x, mod.y, zoom=max(0.72, self.canvas.zoom))

    def clear_mod_selection(self):
        self.current_mod = None
        self.current_mod_data = None
        self.image_index = 0
        self.stop_audio()
        self.lbl_title.config(text="No blast node selected")
        self.lbl_author.config(text="Click a mod in the field to inspect it here.")
        self.lbl_version_chip.config(text="Version: -")
        self.lbl_genre_chip.config(text="Zone: -")
        self.lbl_mode_chip.config(text="Mode: -")
        self.lbl_image_count.config(text="Images: 0/0")
        self.preview_state.config(text="No visual data")
        self.txt_desc.config(state="normal")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", "Select a package from the blast field to review metadata, preview art, and action controls.")
        self.txt_desc.config(state="disabled")
        self.img_label.config(image="", text="[No Mod Selected]", bg=PREVIEW_BG, fg=ACCENT_BRIGHT)
        self.btn_apply.config(state="disabled")
        self.btn_disable.config(state="disabled")
        self.btn_folder.config(state="disabled")
        self.btn_prev.config(state="disabled")
        self.btn_next.config(state="disabled")
        self.audio_var.set("Embedded audio idle")
        self.scroll_detail_to_top()
        self.canvas.render()

    def update_image_display(self):
        images = self.current_mod_data.get("images", []) if self.current_mod_data else []
        if not images:
            self.lbl_image_count.config(text="Images: 0/0")
            self.preview_state.config(text="No preview art embedded")
            self.img_label.config(image="", text="[NO VISUAL DATA]", bg=PREVIEW_BG, fg=TEXT_MUTED)
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            return

        total = len(images)
        self.image_index %= total
        self.lbl_image_count.config(text=f"Images: {self.image_index + 1}/{total}")
        self.preview_state.config(text=f"Preview {self.image_index + 1} of {total}")
        state = "normal" if total > 1 else "disabled"
        self.btn_prev.config(state=state)
        self.btn_next.config(state=state)
        try:
            img = Image.open(BytesIO(images[self.image_index]))
            resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            self.img_frame.update_idletasks()
            width = self.img_frame.winfo_width()
            height = self.img_frame.winfo_height()
            if width <= 1:
                width = 380
            if height <= 1:
                height = int(self.img_frame.cget("height") or 250)
            img = img.resize((max(1, width), max(1, height)), resample=resampling)
            self.preview_photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.preview_photo, text="", bg=PREVIEW_BG)
        except Exception as exc:
            self.img_label.config(image="", text=f"IMG ERROR\n{exc}", bg=PREVIEW_BG, fg=DANGER)

    def cycle_image(self, delta: int):
        images = self.current_mod_data.get("images", []) if self.current_mod_data else []
        if images:
            self.image_index = (self.image_index + delta) % len(images)
            self.update_image_display()

    def refresh_audio_state(self):
        audio = self.current_mod_data.get("audio") if self.current_mod_data else None
        if not audio:
            self.stop_audio()
            self.audio_var.set("No embedded WAV detected")
            return
        if not self.music_enabled.get():
            self.stop_audio()
            self.audio_var.set("Embedded audio muted")
            return
        if len(audio) >= 12 and audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
            self.audio_player.play_loop_bytes(audio)
            self.audio_var.set("Embedded audio playing")
        else:
            self.stop_audio()
            self.audio_var.set("Embedded audio is not a WAV")

    def stop_audio(self):
        self.audio_player.stop()

    def set_status(self, text: str, color: str):
        self.status_var.set(text)
        self.status_label.config(fg=color)

    def confirm_collision_apply(self, mod_path, keys):
        collisions, skipped_mods = self.logic.get_active_collision_report(keys, exclude_mod_name=os.path.basename(mod_path))
        if not collisions and not skipped_mods:
            return True
        message = self.logic.build_collision_message(os.path.basename(mod_path), collisions, skipped_mods, len(keys))
        return messagebox.askyesno("Mod Collision Detected", message)

    def apply_selected_mod(self):
        if not self.current_mod:
            return
        if self.current_mod.package_type == "installer":
            self.launch_wizard()
            return
        mod_name = self.current_mod.filename
        records = self.logic.iter_standard_mod_records(self.current_mod.path, include_data=False)
        keys = {record["key"] for record in records}
        if not self.confirm_collision_apply(self.current_mod.path, keys):
            return
        success, msg = self.logic.apply_mod(self.current_mod.path)
        (messagebox.showinfo if success else messagebox.showerror)("Operation Result", msg)
        self.refresh_mod_list()
        if success:
            self.set_status(f"Enabled {mod_name}.", GREEN_BRIGHT)

    def disable_selected_mod(self):
        if not self.current_mod:
            return
        mod_name = self.current_mod.filename
        success, msg = self.logic.disable_mod(self.current_mod.path)
        (messagebox.showinfo if success else messagebox.showerror)("Operation Result", msg)
        self.refresh_mod_list()
        if success:
            self.set_status(f"Disabled {mod_name}.", ACCENT_BRIGHT)

    def hard_reset_mods(self):
        if not messagebox.askyesno("System Warning", "Restoring vanilla LINKDATA.\nThis will wipe all active mods. Proceed?"):
            return
        success, level, msg = self.logic.disable_all()
        {"info": messagebox.showinfo, "warning": messagebox.showwarning, "error": messagebox.showerror}.get(level, messagebox.showinfo)("System Reset", msg)
        if success:
            self.refresh_mod_list()
            self.set_status("All active mods were disabled.", ACCENT_BRIGHT)

    def reveal_selected_mod(self):
        if self.current_mod:
            folder = os.path.dirname(self.current_mod.path)
            if os.path.isdir(folder):
                try:
                    os.startfile(folder)
                except Exception:
                    messagebox.showinfo("Folder", folder)

    def launch_wizard(self):
        if not self.current_mod:
            return
        self.stop_audio()
        from .katsuki_gui import InstallerWizard
        InstallerWizard(self, self.current_mod.path, self.logic)

    def destroy(self):
        if self.hero_after_id is not None:
            try:
                self.after_cancel(self.hero_after_id)
            except Exception:
                pass
            self.hero_after_id = None
        self.stop_audio()
        super().destroy()
