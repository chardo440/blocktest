#!/usr/bin/env python3
"""Groot's Workshop — Price Calculator (desktop edition).

A Tkinter port of the Groot's Workshop web price calculator.
Covers all three modes of the original app:

  * Stickers & Decals — vinyl / holographic / chrome / unlaminated,
    die-cut / kiss-cut / transfer, rush pricing, multi-item cart with
    design-setup fees, whole-order rush, and roll-usage estimates.
  * Banners — tiered $/sqft pricing with a combined-cart discount.
  * Signs — substrate + vinyl cost calculator with editable material
    costs, labor, single/double sided, markup, and a quote cart.

Run it with:

    python groots_workshop.py

Requires only the Python standard library (tkinter, which ships with
the official python.org installers on Windows and macOS; on
Debian/Ubuntu install it with `sudo apt install python3-tk`).
"""

import math

# ======================================================================
# Pricing engine (pure Python — no GUI dependencies)
# ======================================================================

BLEED = 0.25  # bleed added to each side of a sticker, in inches

# Piecewise-linear rate curve: (total sqft, $/sqft).  The original web
# calculator lists ~80 points, but every point past 42 sqft is a constant
# $4.00/sqft, so the flat tail is collapsed to its endpoints — linear
# interpolation gives identical results.
GROOTS_RATE = [
    (2.1701, 22.3262), (4.2535, 13.1891), (4.3403, 13.1891), (7.0312, 9.5503),
    (8.5069, 8.573), (8.6806, 8.4838), (10.5035, 7.5261), (13.0208, 6.6977),
    (14.0625, 6.2076), (14.6701, 6.2076), (17.0139, 6.067), (19.5312, 6.067),
    (21.0069, 5.2683), (21.7014, 5.2683), (25.0868, 5.2683), (25.5208, 5.1438),
    (28.125, 4.3931), (29.3403, 4.3931), (31.3368, 4.3931), (32.5521, 4.3931),
    (38.2812, 4.3742), (39.0625, 4.3742), (42.0139, 4.0), (42.1875, 4.0),
    (42.5347, 4.0), (43.4028, 4.0), (2934.0278, 4.0),
]

MATERIALS = ("vinyl", "holo", "chrome", "unlam")
MATERIAL_LABELS = {
    "vinyl": "Vinyl",
    "holo": "Holographic",
    "chrome": "Chrome",
    "unlam": "Unlaminated",
}
MATERIAL_MULT = {"vinyl": 1.00, "holo": 1.30, "chrome": 1.30, "unlam": 0.70}

CUT_LABELS = {"die": "Die Cut", "kiss": "Kiss Cut", "transfer": "Transfer"}
CUT_MULT = {"die": 1.00, "kiss": 1.10, "transfer": 1.20}

RUSH_MULT = 1.40  # +40%

# Roll usage / material-cost estimate
ROLL_WIDTH = 54        # inches
ROLL_LENGTH_FT = 150   # feet
ROLL_GAP = 0.25        # gap per side around each sticker (matches bleed)
ROLL_COST = {"vinyl": 395, "holo": 595, "chrome": 595, "unlam": 200}

# Sign materials (costs are editable in the app's settings panel)
SUBSTRATES = [
    {"id": "acm-8th", "name": 'ACM 1/8"', "sheetW": 48, "sheetH": 96, "cost": 85.0},
    {"id": "acm-qtr", "name": 'ACM 1/4"', "sheetW": 48, "sheetH": 96, "cost": 120.0},
    {"id": "coro", "name": "Coroplast 4mm", "sheetW": 48, "sheetH": 96, "cost": 18.0},
    {"id": "ply-qtr", "name": 'Plywood 1/4"', "sheetW": 48, "sheetH": 96, "cost": 28.0},
    {"id": "ply-hlf", "name": 'Plywood 1/2"', "sheetW": 48, "sheetH": 96, "cost": 42.0},
    {"id": "ply-3qtr", "name": 'Plywood 3/4"', "sheetW": 48, "sheetH": 96, "cost": 58.0},
]
VINYLS = [
    {"id": "v1", "name": "White Cast", "rollW": 54, "rollL": 150, "cost": 395.0},
    {"id": "v2", "name": "White Calendered", "rollW": 54, "rollL": 150, "cost": 90.0},
    {"id": "v3", "name": "Clear Cast", "rollW": 54, "rollL": 150, "cost": 210.0},
    {"id": "v4", "name": "Black Cast", "rollW": 54, "rollL": 150, "cost": 185.0},
    {"id": "v5", "name": "Matte White", "rollW": 54, "rollL": 150, "cost": 395.0},
    {"id": "v6", "name": "Reflective", "rollW": 48, "rollL": 50, "cost": 220.0},
    {"id": "v7", "name": "Chrome/Metallic", "rollW": 54, "rollL": 50, "cost": 150.0},
    {"id": "v8", "name": "Printable (OWV)", "rollW": 54, "rollL": 150, "cost": 240.0},
]


def fmt(n):
    """Format a number as $1,234.56."""
    return f"${n:,.2f}"


def rect_sqft(w, h):
    """Square footage of a w×h inch rectangle (banners, signs)."""
    return w * h / 144.0


def sticker_sqft(w, h):
    """Square footage of one sticker including bleed on every side."""
    return (w + 2 * BLEED) * (h + 2 * BLEED) / 144.0


def interp_rate(sqft, curve=GROOTS_RATE):
    """Linearly interpolate the $/sqft rate for a total order square footage."""
    if sqft <= curve[0][0]:
        return curve[0][1]
    if sqft >= curve[-1][0]:
        return curve[-1][1]
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if x0 <= sqft <= x1:
            t = (sqft - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return curve[0][1]


def sticker_order_price(sqft, mult=1.0):
    """Price for a sticker order of `sqft` total square feet.

    Never drops below material cost (sqft * $0.81 + $6 setup) plus 10%.
    """
    if sqft <= 0:
        return 0.0
    material_floor = (sqft * 0.81 + 6) * 1.10
    return max(sqft * interp_rate(sqft), material_floor) * mult


def sticker_line_price(w, h, qty, mat="vinyl", cut="die", rush=False):
    """Live price for a single sticker configuration (not in a cart)."""
    total_sqft = sticker_sqft(w, h) * qty
    price = sticker_order_price(total_sqft, MATERIAL_MULT[mat])
    return price * CUT_MULT[cut] * (RUSH_MULT if rush else 1.0)


def sticker_cart_prices(items):
    """Price each cart item by its share of the combined order square footage.

    Items are dicts with keys w, h, qty, mat, cut, rush.  Combining items
    pushes the whole order further down the rate curve, so every item gets
    the bulk rate.  Returns (list of per-item prices, subtotal).
    """
    total_sqft = sum(sticker_sqft(i["w"], i["h"]) * i["qty"] for i in items)
    base = sticker_order_price(total_sqft, 1.0)
    prices = []
    for i in items:
        isqft = sticker_sqft(i["w"], i["h"]) * i["qty"]
        share = isqft / total_sqft if total_sqft > 0 else 0.0
        p = base * share * MATERIAL_MULT[i["mat"]] * CUT_MULT[i["cut"]]
        if i["rush"]:
            p *= RUSH_MULT
        prices.append(max(p, 0.01))
    return prices, sum(prices)


def design_fee(n):
    """Design setup fee: 1st design free, designs 2–5 are $15, 6+ are $20."""
    if n <= 1:
        return 0
    return sum(15 if i <= 5 else 20 for i in range(2, n + 1))


def design_fee_text(n):
    if n <= 1:
        return "1st design included free"
    if n <= 5:
        return f"1 free + {n - 1} × $15 = {fmt(design_fee(n))}"
    return f"1 free + 4 × $15 + {n - 5} × $20 = {fmt(design_fee(n))}"


def roll_usage(items):
    """Estimate linear roll feet used and material cost for sticker items.

    Stickers are nested across the 54" roll width with a 0.25" gap on each
    side.  Returns (linear feet, estimated material cost).
    """
    total_ft = 0.0
    total_cost = 0.0
    for i in items:
        fw = i["w"] + 2 * ROLL_GAP
        fh = i["h"] + 2 * ROLL_GAP
        across = max(1, math.floor(ROLL_WIDTH / fw))
        rows = math.ceil(i["qty"] / across)
        lin_ft = rows * fh / 12.0
        total_ft += lin_ft
        total_cost += lin_ft * ROLL_COST.get(i["mat"], 395) / ROLL_LENGTH_FT
    return total_ft, total_cost


def banner_price(sqft):
    """Tiered banner pricing: $4.00 to 25 sqft, $3.75 to 50, $3.25 beyond."""
    if sqft <= 0:
        return 0.0
    if sqft <= 25:
        return sqft * 4.00
    if sqft <= 50:
        return 100.0 + (sqft - 25) * 3.75
    return 193.75 + (sqft - 50) * 3.25


def banner_tier(sqft):
    return 1 if sqft <= 25 else 2 if sqft <= 50 else 3


def sub_cost_per_sqft(sub):
    return sub["cost"] / rect_sqft(sub["sheetW"], sub["sheetH"])


def vinyl_cost_per_sqft(vin):
    return vin["cost"] / ((vin["rollW"] / 12.0) * vin["rollL"])


def sign_quote(sub, vin, w, h, qty, labor, sides, markup):
    """Cost + suggested price for a sign.  `vin` may be None (print only)."""
    sqft = rect_sqft(w, h)
    sub_cost = sub_cost_per_sqft(sub) * sqft
    vin_cost = (vinyl_cost_per_sqft(vin) * sqft * sides) if vin else 0.0
    unit_cost = sub_cost + vin_cost + labor
    total_cost = unit_cost * qty
    suggested = total_cost * markup
    margin = (suggested - total_cost) / suggested * 100 if suggested else 0.0
    return {
        "sqft": sqft, "sub_cost": sub_cost, "vin_cost": vin_cost,
        "unit_cost": unit_cost, "total_cost": total_cost,
        "suggested": suggested, "margin": margin,
    }


# ======================================================================
# GUI
# ======================================================================

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:  # keeps the pricing engine importable without tkinter
    tk = None

if tk is not None:

    # -- theme -----------------------------------------------------------
    BG = "#0a0c10"
    SURFACE = "#14161d"
    SURFACE2 = "#1c1f28"
    BORDER = "#2a2f40"
    TEXT = "#eef0f8"
    MUTED = "#9aa0c0"
    GREEN = "#00e87a"
    ACCENT = "#8a84ff"
    AMBER = "#ffb020"
    ORANGE = "#ff6b35"
    RED = "#ff4d6d"
    HOLO = "#d966ff"
    CHROME = "#c0c8d8"
    CYAN = "#00cfff"

    MAT_COLORS = {"vinyl": GREEN, "holo": HOLO, "chrome": CHROME, "unlam": AMBER}

    FONT = "Helvetica"

    class ScrollFrame(tk.Frame):
        """A vertically scrollable frame (canvas + interior frame)."""

        def __init__(self, parent):
            super().__init__(parent, bg=BG)
            self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
            self.vbar = tk.Scrollbar(self, orient="vertical",
                                     command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=self.vbar.set)
            self.vbar.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)
            self.body = tk.Frame(self.canvas, bg=BG)
            self._win = self.canvas.create_window((0, 0), window=self.body,
                                                  anchor="nw")
            self.body.bind("<Configure>", self._on_body_configure)
            self.canvas.bind("<Configure>", self._on_canvas_configure)

        def _on_body_configure(self, _e):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_configure(self, e):
            self.canvas.itemconfigure(self._win, width=e.width)

    def flat_button(parent, text, command, fg=TEXT, bg=SURFACE2, size=10,
                    bold=True, padx=12, pady=6):
        """A themed clickable label (tk.Button ignores bg on some platforms)."""
        lbl = tk.Label(parent, text=text, fg=fg, bg=bg, cursor="hand2",
                       font=(FONT, size, "bold" if bold else "normal"),
                       padx=padx, pady=pady, bd=1, relief="solid",
                       highlightthickness=0)
        lbl.configure(highlightbackground=BORDER)
        lbl.bind("<Button-1>", lambda _e: command())
        return lbl

    class ToggleGroup:
        """A row of mutually-exclusive toggle buttons."""

        def __init__(self, parent, options, command=None, colors=None,
                     size=10, pady=6):
            """options: list of (value, label). colors: {value: active_fg}."""
            self.value = options[0][0]
            self.command = command
            self.colors = colors or {}
            self.buttons = {}
            self.frame = tk.Frame(parent, bg=parent["bg"])
            for i, (val, label) in enumerate(options):
                b = flat_button(self.frame, label,
                                lambda v=val: self.set(v),
                                size=size, pady=pady)
                b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))
                self.frame.grid_columnconfigure(i, weight=1)
                self.buttons[val] = b
            self._paint()

        def set(self, value, fire=True):
            self.value = value
            self._paint()
            if fire and self.command:
                self.command(value)

        def _paint(self):
            for val, b in self.buttons.items():
                if val == self.value:
                    fg = self.colors.get(val, ACCENT)
                    b.configure(fg=fg, bg=SURFACE)
                else:
                    b.configure(fg=MUTED, bg=SURFACE2)

    def dark_entry(parent, textvariable, width=8, justify="left"):
        e = tk.Entry(parent, textvariable=textvariable, width=width,
                     bg=SURFACE2, fg=TEXT, insertbackground=TEXT,
                     relief="solid", bd=1, justify=justify,
                     font=("Courier", 11),
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT)
        return e

    def section_label(parent, text):
        return tk.Label(parent, text=text.upper(), fg=MUTED, bg=parent["bg"],
                        font=("Courier", 9), anchor="w")

    def card(parent):
        f = tk.Frame(parent, bg=SURFACE, bd=1, relief="solid",
                     highlightthickness=0, padx=14, pady=12)
        return f

    def parse_float(var, default=0.0):
        try:
            return float(var.get())
        except (ValueError, tk.TclError):
            return default

    def parse_int(var, default=0):
        try:
            return int(float(var.get()))
        except (ValueError, tk.TclError):
            return default

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Groot's Workshop — Price Calculator")
            self.configure(bg=BG)
            self.geometry("760x900")
            self.minsize(640, 600)

            # ---- state ----
            self.sticker_cart = []
            self.banner_cart = []
            self.sign_cart = []
            self.cart_rush = tk.BooleanVar(value=False)
            self.design_count = tk.IntVar(value=1)
            self.sign_markup = 2.5
            self.sign_sides = 1

            self._build_header()
            self._build_modes()
            # One global mousewheel handler routed to whichever ScrollFrame
            # the pointer is over (per-widget Enter/Leave bindings break when
            # hovering child widgets).
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.bind_all(seq, self._on_mousewheel)
            self.show_mode("sticker")
            self.recalc_sticker()
            self.recalc_banner()
            self.recalc_sign()

        # ---------------------------------------------------------------
        # Header + mode switching
        # ---------------------------------------------------------------
        def _build_header(self):
            head = tk.Frame(self, bg=BG)
            head.pack(fill="x", padx=16, pady=(14, 6))
            tk.Label(head, text="⬢ PRICE CALCULATOR", fg=GREEN, bg=BG,
                     font=("Courier", 9)).pack()
            title = tk.Frame(head, bg=BG)
            title.pack()
            tk.Label(title, text="Groot's ", fg=TEXT, bg=BG,
                     font=(FONT, 22, "bold")).pack(side="left")
            tk.Label(title, text="Workshop", fg=GREEN, bg=BG,
                     font=(FONT, 22, "bold")).pack(side="left")
            tk.Label(head, text="// stickers · decals · banners · signs",
                     fg=MUTED, bg=BG, font=("Courier", 9)).pack()

            self.mode_group = ToggleGroup(
                head,
                [("sticker", "🏷 Stickers & Decals"),
                 ("banner", "🚩 Banners"),
                 ("sign", "📷 Signs")],
                command=self.show_mode,
                colors={"sticker": ACCENT, "banner": AMBER, "sign": ORANGE},
                pady=8)
            self.mode_group.frame.pack(fill="x", pady=(10, 0))

        def _build_modes(self):
            self.mode_frames = {}
            container = tk.Frame(self, bg=BG)
            container.pack(fill="both", expand=True)
            for mode, builder in (("sticker", self._build_sticker_tab),
                                  ("banner", self._build_banner_tab),
                                  ("sign", self._build_sign_tab)):
                sf = ScrollFrame(container)
                builder(sf.body)
                self.mode_frames[mode] = sf

        def _on_mousewheel(self, e):
            w = e.widget
            while w is not None and not isinstance(w, ScrollFrame):
                w = getattr(w, "master", None)
            if w is None:
                return
            delta = -1 if (getattr(e, "num", 0) == 4 or e.delta > 0) else 1
            w.canvas.yview_scroll(delta, "units")

        def show_mode(self, mode):
            self.mode_group.set(mode, fire=False)
            for m, f in self.mode_frames.items():
                if m == mode:
                    f.pack(fill="both", expand=True, padx=12, pady=6)
                else:
                    f.pack_forget()

        # ---------------------------------------------------------------
        # Stickers tab
        # ---------------------------------------------------------------
        def _build_sticker_tab(self, root):
            self.st_unit = "in"
            self.st_w = tk.StringVar(value="3")
            self.st_h = tk.StringVar(value="3")
            self.st_qty = tk.IntVar(value=100)
            self.st_custom_qty = tk.StringVar()

            self.st_mat_group = ToggleGroup(
                root,
                [("vinyl", "🏷 Vinyl"), ("holo", "✨ Holographic"),
                 ("chrome", "⬢ Chrome"), ("unlam", "🎁 Unlaminated")],
                command=lambda _v: self.recalc_sticker(),
                colors=MAT_COLORS, size=9)
            self.st_mat_group.frame.pack(fill="x", pady=(4, 8))

            c = card(root)
            c.pack(fill="x", pady=4)
            section_label(c, "01 — Size").pack(fill="x")
            self.st_unit_group = ToggleGroup(
                c, [("in", "Inches"), ("ft", "Feet")],
                command=self._st_set_unit)
            self.st_unit_group.frame.pack(fill="x", pady=(6, 8))
            dims = tk.Frame(c, bg=SURFACE)
            dims.pack(fill="x")
            self.st_unit_lbls = []
            for col, (label, var, hi_in) in enumerate(
                    (("Width", self.st_w, 48), ("Height", self.st_h, 120))):
                g = tk.Frame(dims, bg=SURFACE)
                g.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 12, 0))
                dims.grid_columnconfigure(col, weight=1)
                tk.Label(g, text=label.upper(), fg=MUTED, bg=SURFACE,
                         font=("Courier", 8)).pack(anchor="w")
                row = tk.Frame(g, bg=SURFACE)
                row.pack(fill="x")
                flat_button(row, "−",
                            lambda v=var, m=hi_in: self._st_step(v, -1, m),
                            padx=10).pack(side="left")
                e = dark_entry(row, var, width=7)
                e.pack(side="left", fill="x", expand=True, padx=4)
                e.bind("<KeyRelease>", lambda _e: self.recalc_sticker())
                ul = tk.Label(row, text=self.st_unit, fg=MUTED, bg=SURFACE,
                              font=("Courier", 9))
                ul.pack(side="left", padx=(0, 4))
                self.st_unit_lbls.append(ul)
                flat_button(row, "+",
                            lambda v=var, m=hi_in: self._st_step(v, 1, m),
                            padx=10).pack(side="left")

            section_label(c, "02 — Quantity").pack(fill="x", pady=(12, 4))
            qgrid = tk.Frame(c, bg=SURFACE)
            qgrid.pack(fill="x")
            self.st_qty_buttons = {}
            for i, q in enumerate((1, 10, 20, 50, 100, 200, 500, 1000)):
                b = flat_button(qgrid, str(q), lambda q=q: self._st_set_qty(q),
                                size=9, padx=8, pady=4)
                b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0))
                qgrid.grid_columnconfigure(i, weight=1)
                self.st_qty_buttons[q] = b
            crow = tk.Frame(c, bg=SURFACE)
            crow.pack(fill="x", pady=(6, 0))
            tk.Label(crow, text="Custom qty:", fg=MUTED, bg=SURFACE,
                     font=("Courier", 9)).pack(side="left")
            ce = dark_entry(crow, self.st_custom_qty, width=8)
            ce.pack(side="left", padx=6)
            ce.bind("<KeyRelease>", lambda _e: self._st_set_custom_qty())

            section_label(c, "Cut Type").pack(fill="x", pady=(12, 4))
            self.st_cut_group = ToggleGroup(
                c, [("die", "✂ Die Cut"), ("kiss", "💋 Kiss Cut +10%"),
                    ("transfer", "📋 Transfer +20%")],
                command=lambda _v: self.recalc_sticker(),
                colors={"die": GREEN, "kiss": ACCENT, "transfer": CYAN}, size=9)
            self.st_cut_group.frame.pack(fill="x")

            section_label(c, "Turnaround").pack(fill="x", pady=(12, 4))
            self.st_rush_group = ToggleGroup(
                c, [("std", "🗓 Standard"), ("rush", "⚡ Rush +40%")],
                command=lambda _v: self.recalc_sticker(),
                colors={"std": GREEN, "rush": RED}, size=9)
            self.st_rush_group.frame.pack(fill="x")

            flat_button(c, "+ Add to Cart", self.add_sticker_to_cart,
                        fg=ACCENT, pady=8).pack(fill="x", pady=(12, 0))

            # price panel
            pc = card(root)
            pc.pack(fill="x", pady=4)
            self.st_badge = tk.Label(pc, text="✦ LOWEST PRICE GUARANTEED",
                                     fg="#000000", bg=GREEN,
                                     font=("Courier", 8, "bold"), padx=10, pady=2)
            self.st_badge.pack()
            tk.Label(pc, text="GROOT'S WORKSHOP PRICE", fg=MUTED, bg=SURFACE,
                     font=("Courier", 8)).pack(pady=(6, 0))
            self.st_price = tk.Label(pc, text="—", fg=GREEN, bg=SURFACE,
                                     font=(FONT, 30, "bold"))
            self.st_price.pack()
            self.st_price_ea = tk.Label(pc, text="", fg=MUTED, bg=SURFACE,
                                        font=("Courier", 10))
            self.st_price_ea.pack()
            self.st_detail = tk.Label(pc, text="", fg=MUTED, bg=SURFACE,
                                      font=("Courier", 9), justify="center")
            self.st_detail.pack(pady=(6, 0))

            # cart
            cc = card(root)
            cc.pack(fill="x", pady=4)
            section_label(cc, "03 — Order Cart").pack(fill="x")
            self.st_cart_frame = tk.Frame(cc, bg=SURFACE)
            self.st_cart_frame.pack(fill="x", pady=(6, 0))

            drow = tk.Frame(cc, bg=SURFACE)
            self.st_design_row = drow
            tk.Label(drow, text="✎ DESIGNS IN ORDER", fg=MUTED, bg=SURFACE,
                     font=("Courier", 8)).pack(side="left")
            flat_button(drow, "−", lambda: self._step_designs(-1),
                        padx=10, pady=2).pack(side="left", padx=(10, 4))
            de = dark_entry(drow, self.design_count, width=4, justify="center")
            de.pack(side="left")
            de.bind("<KeyRelease>", lambda _e: self.render_sticker_cart())
            flat_button(drow, "+", lambda: self._step_designs(1),
                        padx=10, pady=2).pack(side="left", padx=4)
            self.st_design_hint = tk.Label(drow, text="", fg=ACCENT, bg=SURFACE,
                                           font=("Courier", 8))
            self.st_design_hint.pack(side="left", padx=8)

            trow = tk.Frame(cc, bg=SURFACE)
            self.st_totals_frame = trow
            self.st_rush_check = tk.Checkbutton(
                trow, text="⚡ Rush entire order  (+40% on everything)",
                variable=self.cart_rush, command=self.render_sticker_cart,
                fg=RED, bg=SURFACE, activebackground=SURFACE,
                activeforeground=RED, selectcolor=SURFACE2,
                font=(FONT, 10, "bold"), anchor="w")
            self.st_rush_check.pack(fill="x", pady=(8, 4))
            self.st_subtotal = self._total_row(trow, "PRINT SUBTOTAL", MUTED)
            self.st_fee_line = self._total_row(trow, "DESIGN SETUP FEE", ACCENT)
            self.st_rush_line = self._total_row(trow, "⚡ RUSH (+40%)", RED)
            self.st_total = self._total_row(trow, "ORDER TOTAL", AMBER, size=13)
            flat_button(trow, "↻ Clear Cart", self.reset_sticker_cart,
                        fg=RED, pady=5).pack(fill="x", pady=(8, 0))

            # roll usage
            rc = card(root)
            rc.pack(fill="x", pady=(4, 12))
            section_label(rc, "✂ Roll Usage & Material Cost").pack(fill="x")
            rrow = tk.Frame(rc, bg=SURFACE)
            rrow.pack(fill="x", pady=(6, 0))
            self.st_roll_ft = tk.Label(rrow, text="0.00 ft", fg=GREEN,
                                       bg=SURFACE2, font=("Courier", 13, "bold"),
                                       padx=12, pady=8)
            self.st_roll_ft.pack(side="left", expand=True, fill="x")
            self.st_roll_cost = tk.Label(rrow, text="$0.00", fg=AMBER,
                                         bg=SURFACE2, font=("Courier", 13, "bold"),
                                         padx=12, pady=8)
            self.st_roll_cost.pack(side="left", expand=True, fill="x", padx=(8, 0))
            lblrow = tk.Frame(rc, bg=SURFACE)
            lblrow.pack(fill="x")
            tk.Label(lblrow, text="LINEAR ROLL USED", fg=MUTED, bg=SURFACE,
                     font=("Courier", 7)).pack(side="left", expand=True)
            tk.Label(lblrow, text="EST. MATERIAL COST", fg=MUTED, bg=SURFACE,
                     font=("Courier", 7)).pack(side="left", expand=True)
            self.st_roll_detail = tk.Label(rc, text="", fg=MUTED, bg=SURFACE,
                                           font=("Courier", 8), justify="left",
                                           anchor="w")
            self.st_roll_detail.pack(fill="x", pady=(6, 0))

        def _total_row(self, parent, label, color, size=10):
            row = tk.Frame(parent, bg=SURFACE)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, fg=color, bg=SURFACE,
                     font=("Courier", 8)).pack(side="left")
            val = tk.Label(row, text="$0.00", fg=color, bg=SURFACE,
                           font=("Courier", size, "bold"))
            val.pack(side="right")
            row.value_label = val
            return row

        def _st_set_unit(self, unit):
            if unit == self.st_unit:
                return
            w = parse_float(self.st_w, 3)
            h = parse_float(self.st_h, 3)
            if unit == "ft":
                self.st_w.set(str(round(w / 12 * 100) / 100))
                self.st_h.set(str(round(h / 12 * 100) / 100))
            else:
                self.st_w.set(str(round(w * 12 * 4) / 4))
                self.st_h.set(str(round(h * 12 * 4) / 4))
            self.st_unit = unit
            for lbl in self.st_unit_lbls:
                lbl.configure(text=unit)
            self.recalc_sticker()

        def _st_step(self, var, direction, hi_in):
            v = parse_float(var, 0.25 if self.st_unit == "ft" else 3)
            delta = direction / 12 if self.st_unit == "ft" else direction * 0.25
            lo, hi = (0.04, hi_in / 12) if self.st_unit == "ft" else (0.5, hi_in)
            v = max(lo, min(hi, round((v + delta) * 100) / 100))
            var.set(f"{v:g}")
            self.recalc_sticker()

        def _st_set_qty(self, q):
            self.st_qty.set(q)
            self.st_custom_qty.set("")
            self._paint_qty_buttons()
            self.recalc_sticker()

        def _st_set_custom_qty(self):
            q = parse_int(self.st_custom_qty)
            if q >= 1:
                self.st_qty.set(q)
                self._paint_qty_buttons()
                self.recalc_sticker()

        def _paint_qty_buttons(self):
            custom = bool(self.st_custom_qty.get().strip())
            for q, b in self.st_qty_buttons.items():
                on = not custom and q == self.st_qty.get()
                b.configure(fg=ACCENT if on else MUTED,
                            bg=SURFACE if on else SURFACE2)

        def _st_dims_inches(self):
            w = parse_float(self.st_w, 3)
            h = parse_float(self.st_h, 3)
            if self.st_unit == "ft":
                w *= 12
                h *= 12
            return w, h

        def recalc_sticker(self):
            w, h = self._st_dims_inches()
            qty = max(1, self.st_qty.get())
            mat = self.st_mat_group.value
            cut = self.st_cut_group.value
            rush = self.st_rush_group.value == "rush"
            each_sqft = sticker_sqft(w, h)
            total_sqft = each_sqft * qty
            price = sticker_line_price(w, h, qty, mat, cut, rush)
            rate = interp_rate(total_sqft)

            self.st_price.configure(text=fmt(price), fg=MAT_COLORS[mat])
            self.st_price_ea.configure(text=f"{fmt(price / qty)} per sticker")
            self.st_badge.configure(bg=MAT_COLORS[mat])
            mult_note = {"vinyl": "", "holo": "Holographic — 1.30× premium · ",
                         "chrome": "Chrome — 1.30× premium · ",
                         "unlam": "Unlaminated — 30% off vinyl · "}[mat]
            self.st_detail.configure(text=(
                f"{mult_note}{MATERIAL_LABELS[mat]} · {CUT_LABELS[cut]}"
                f" · {'⚡ Rush' if rush else 'Standard'}\n"
                f"Each: {each_sqft:.4f} sqft · Total: {total_sqft:.2f} sqft"
                f" · Rate: ${rate:.2f}/sqft"))
            self.render_sticker_cart()

        def add_sticker_to_cart(self):
            w, h = self._st_dims_inches()
            qty = max(1, self.st_qty.get())
            if self.st_unit == "in":
                wd, hd = f"{w:g}in", f"{h:g}in"
            else:
                wd, hd = f"{w / 12:.2f}ft", f"{h / 12:.2f}ft"
            self.sticker_cart.append({
                "w": w, "h": h, "qty": qty, "wd": wd, "hd": hd,
                "mat": self.st_mat_group.value,
                "cut": self.st_cut_group.value,
                "rush": self.st_rush_group.value == "rush",
            })
            if len(self.sticker_cart) > max(1, self.design_count.get()):
                self.design_count.set(len(self.sticker_cart))
            self.render_sticker_cart()

        def remove_sticker_from_cart(self, index):
            del self.sticker_cart[index]
            if self.design_count.get() > max(1, len(self.sticker_cart)):
                self.design_count.set(max(1, len(self.sticker_cart)))
            self.render_sticker_cart()

        def reset_sticker_cart(self):
            self.sticker_cart = []
            self.cart_rush.set(False)
            self.design_count.set(1)
            self.render_sticker_cart()

        def render_sticker_cart(self):
            for child in self.st_cart_frame.winfo_children():
                child.destroy()
            items = self.sticker_cart
            if not items:
                tk.Label(self.st_cart_frame,
                         text="No items yet — configure a size above and click Add",
                         fg=MUTED, bg=SURFACE, font=("Courier", 9)
                         ).pack(pady=8)
                self.st_design_row.pack_forget()
                self.st_totals_frame.pack_forget()
                self._update_roll_usage()
                return

            prices, subtotal = sticker_cart_prices(items)
            for idx, (item, price) in enumerate(zip(items, prices)):
                row = tk.Frame(self.st_cart_frame, bg=SURFACE2, padx=8, pady=6)
                row.pack(fill="x", pady=2)
                tags = [MATERIAL_LABELS[item["mat"]]]
                if item["cut"] != "die":
                    tags.append(CUT_LABELS[item["cut"]])
                if item["rush"]:
                    tags.append("⚡ Rush")
                info = tk.Frame(row, bg=SURFACE2)
                info.pack(side="left", fill="x", expand=True)
                tk.Label(info,
                         text=f"{item['wd']} × {item['hd']}  × {item['qty']}"
                              f"   [{' · '.join(tags)}]",
                         fg=TEXT, bg=SURFACE2, font=("Courier", 9),
                         anchor="w").pack(fill="x")
                each_sqft = sticker_sqft(item["w"], item["h"])
                tk.Label(info,
                         text=f"{each_sqft:.4f} sqft ea · {fmt(price / item['qty'])} ea",
                         fg=MUTED, bg=SURFACE2, font=("Courier", 8),
                         anchor="w").pack(fill="x")
                tk.Label(row, text=fmt(price), fg=MAT_COLORS[item["mat"]],
                         bg=SURFACE2, font=("Courier", 10, "bold")
                         ).pack(side="left", padx=8)
                flat_button(row, "×", lambda i=idx: self.remove_sticker_from_cart(i),
                            fg=RED, padx=8, pady=2).pack(side="left")

            self.st_design_row.pack(fill="x", pady=(10, 0))
            self.st_totals_frame.pack(fill="x", pady=(6, 0))

            n = max(1, self._safe_int(self.design_count))
            fee = design_fee(n)
            self.st_design_hint.configure(text=design_fee_text(n))
            self.st_subtotal.value_label.configure(text=fmt(subtotal))
            if fee > 0:
                anchor = (self.st_rush_line if self.st_rush_line.winfo_manager()
                          else self.st_total)
                self.st_fee_line.pack(fill="x", pady=1, before=anchor)
                self.st_fee_line.value_label.configure(text="+" + fmt(fee))
            else:
                self.st_fee_line.pack_forget()
            pre_rush = subtotal + fee
            if self.cart_rush.get():
                rush_amt = pre_rush * 0.40
                self.st_rush_line.pack(fill="x", pady=1, before=self.st_total)
                self.st_rush_line.value_label.configure(text="+" + fmt(rush_amt))
                grand = pre_rush + rush_amt
            else:
                self.st_rush_line.pack_forget()
                grand = pre_rush
            self.st_total.value_label.configure(text=fmt(grand))
            self._update_roll_usage()

        def _safe_int(self, var):
            try:
                return var.get()
            except tk.TclError:
                return 0

        def _step_designs(self, d):
            self.design_count.set(max(1, self._safe_int(self.design_count) + d))
            self.render_sticker_cart()

        def _update_roll_usage(self):
            if self.sticker_cart:
                items = self.sticker_cart
                note = ""
            else:
                w, h = self._st_dims_inches()
                items = [{"w": w, "h": h, "qty": max(1, self.st_qty.get()),
                          "mat": self.st_mat_group.value}]
                across = max(1, math.floor(ROLL_WIDTH / (w + 2 * ROLL_GAP)))
                note = f'{across} across the 54" roll · '
            lin_ft, cost = roll_usage(items)
            pct = lin_ft / ROLL_LENGTH_FT * 100
            self.st_roll_ft.configure(text=f"{lin_ft:.2f} ft")
            self.st_roll_cost.configure(text=fmt(cost))
            self.st_roll_detail.configure(text=(
                f"{note}{lin_ft:.2f} ft of your {ROLL_LENGTH_FT} ft roll"
                f" ({pct:.1f}%) · includes 0.25\" gap around each sticker"))

        # ---------------------------------------------------------------
        # Banners tab
        # ---------------------------------------------------------------
        def _build_banner_tab(self, root):
            self.bn_unit = "in"
            self.bn_w = tk.StringVar(value="48")
            self.bn_h = tk.StringVar(value="24")
            self.bn_qty = tk.IntVar(value=1)
            self.bn_custom_qty = tk.StringVar()

            c = card(root)
            c.pack(fill="x", pady=4)
            section_label(c, "01 — Size").pack(fill="x")
            self.bn_unit_group = ToggleGroup(
                c, [("in", "Inches"), ("ft", "Feet")],
                command=self._bn_set_unit)
            self.bn_unit_group.frame.pack(fill="x", pady=(6, 8))
            dims = tk.Frame(c, bg=SURFACE)
            dims.pack(fill="x")
            self.bn_unit_lbls = []
            for col, (label, var, hi_in) in enumerate(
                    (("Width", self.bn_w, 480), ("Height", self.bn_h, 240))):
                g = tk.Frame(dims, bg=SURFACE)
                g.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 12, 0))
                dims.grid_columnconfigure(col, weight=1)
                tk.Label(g, text=label.upper(), fg=MUTED, bg=SURFACE,
                         font=("Courier", 8)).pack(anchor="w")
                row = tk.Frame(g, bg=SURFACE)
                row.pack(fill="x")
                flat_button(row, "−",
                            lambda v=var, m=hi_in: self._bn_step(v, -1, m),
                            padx=10).pack(side="left")
                e = dark_entry(row, var, width=7)
                e.pack(side="left", fill="x", expand=True, padx=4)
                e.bind("<KeyRelease>", lambda _e: self.recalc_banner())
                ul = tk.Label(row, text=self.bn_unit, fg=MUTED, bg=SURFACE,
                              font=("Courier", 9))
                ul.pack(side="left", padx=(0, 4))
                self.bn_unit_lbls.append(ul)
                flat_button(row, "+",
                            lambda v=var, m=hi_in: self._bn_step(v, 1, m),
                            padx=10).pack(side="left")

            section_label(c, "02 — Quantity").pack(fill="x", pady=(12, 4))
            qgrid = tk.Frame(c, bg=SURFACE)
            qgrid.pack(fill="x")
            self.bn_qty_buttons = {}
            for i, q in enumerate((1, 2, 5, 10, 25, 50)):
                b = flat_button(qgrid, str(q), lambda q=q: self._bn_set_qty(q),
                                size=9, padx=8, pady=4)
                b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0))
                qgrid.grid_columnconfigure(i, weight=1)
                self.bn_qty_buttons[q] = b
            crow = tk.Frame(c, bg=SURFACE)
            crow.pack(fill="x", pady=(6, 0))
            tk.Label(crow, text="Custom qty:", fg=MUTED, bg=SURFACE,
                     font=("Courier", 9)).pack(side="left")
            ce = dark_entry(crow, self.bn_custom_qty, width=8)
            ce.pack(side="left", padx=6)
            ce.bind("<KeyRelease>", lambda _e: self._bn_set_custom_qty())
            flat_button(c, "+ Add to Cart", self.add_banner_to_cart,
                        fg=AMBER, pady=8).pack(fill="x", pady=(12, 0))

            pc = card(root)
            pc.pack(fill="x", pady=4)
            tk.Label(pc, text="✦ BANNER PRICING", fg="#000000", bg=AMBER,
                     font=("Courier", 8, "bold"), padx=10, pady=2).pack()
            self.bn_price = tk.Label(pc, text="—", fg=AMBER, bg=SURFACE,
                                     font=(FONT, 30, "bold"))
            self.bn_price.pack(pady=(6, 0))
            self.bn_detail = tk.Label(pc, text="", fg=MUTED, bg=SURFACE,
                                      font=("Courier", 9), justify="center")
            self.bn_detail.pack(pady=(4, 0))

            tc = card(root)
            tc.pack(fill="x", pady=4)
            section_label(tc, "03 — Pricing Tiers").pack(fill="x")
            trow = tk.Frame(tc, bg=SURFACE)
            trow.pack(fill="x", pady=(6, 0))
            self.bn_tier_labels = []
            for i, text in enumerate(("0–25 sqft\n$4.00/sqft",
                                      "25–50 sqft\n$3.75/sqft",
                                      "50+ sqft\n$3.25/sqft")):
                lbl = tk.Label(trow, text=text, fg=MUTED, bg=SURFACE2,
                               font=("Courier", 9), padx=10, pady=6)
                lbl.pack(side="left", expand=True, fill="x",
                         padx=(0 if i == 0 else 6, 0))
                self.bn_tier_labels.append(lbl)

            cc = card(root)
            cc.pack(fill="x", pady=(4, 12))
            section_label(cc, "04 — Order Cart").pack(fill="x")
            self.bn_cart_frame = tk.Frame(cc, bg=SURFACE)
            self.bn_cart_frame.pack(fill="x", pady=(6, 0))
            self.bn_totals_frame = tk.Frame(cc, bg=SURFACE)
            self.bn_total = self._total_row(self.bn_totals_frame, "ORDER TOTAL",
                                            AMBER, size=13)
            flat_button(self.bn_totals_frame, "↻ Clear Cart",
                        self.reset_banner_cart, fg=RED, pady=5
                        ).pack(fill="x", pady=(8, 0))

        def _bn_set_unit(self, unit):
            if unit == self.bn_unit:
                return
            w = parse_float(self.bn_w, 48)
            h = parse_float(self.bn_h, 24)
            if unit == "ft":
                self.bn_w.set(str(round(w / 12 * 100) / 100))
                self.bn_h.set(str(round(h / 12 * 100) / 100))
            else:
                self.bn_w.set(str(round(w * 12 * 4) / 4))
                self.bn_h.set(str(round(h * 12 * 4) / 4))
            self.bn_unit = unit
            for lbl in self.bn_unit_lbls:
                lbl.configure(text=unit)
            self.recalc_banner()

        def _bn_step(self, var, direction, hi_in):
            v = parse_float(var, 4 if self.bn_unit == "ft" else 48)
            delta = direction / 12 if self.bn_unit == "ft" else direction * 0.25
            lo, hi = (0.04, hi_in / 12) if self.bn_unit == "ft" else (0.5, hi_in)
            v = max(lo, min(hi, round((v + delta) * 100) / 100))
            var.set(f"{v:g}")
            self.recalc_banner()

        def _bn_set_qty(self, q):
            self.bn_qty.set(q)
            self.bn_custom_qty.set("")
            self._paint_bn_qty_buttons()
            self.recalc_banner()

        def _bn_set_custom_qty(self):
            q = parse_int(self.bn_custom_qty)
            if q >= 1:
                self.bn_qty.set(q)
                self._paint_bn_qty_buttons()
                self.recalc_banner()

        def _paint_bn_qty_buttons(self):
            custom = bool(self.bn_custom_qty.get().strip())
            for q, b in self.bn_qty_buttons.items():
                on = not custom and q == self.bn_qty.get()
                b.configure(fg=AMBER if on else MUTED,
                            bg=SURFACE if on else SURFACE2)

        def _bn_dims_inches(self):
            w = parse_float(self.bn_w, 48)
            h = parse_float(self.bn_h, 24)
            if self.bn_unit == "ft":
                w *= 12
                h *= 12
            return w, h

        def recalc_banner(self):
            w, h = self._bn_dims_inches()
            qty = max(1, self.bn_qty.get())
            each_sqft = rect_sqft(w, h)
            line_sqft = each_sqft * qty
            cart_sqft = sum(i["sqft"] * i["qty"] for i in self.banner_cart)
            combined = cart_sqft + line_sqft
            add_price = banner_price(combined) - banner_price(cart_sqft)
            eff_rate = add_price / line_sqft if line_sqft > 0 else 4.0

            self.bn_price.configure(text=fmt(add_price))
            cart_note = (f" · cart total: {combined:.2f} sqft"
                         if self.banner_cart else "")
            self.bn_detail.configure(text=(
                f"{fmt(add_price / qty)} per banner · this line:"
                f" {line_sqft:.2f} sqft{cart_note}\n"
                f"Each: {each_sqft:.3f} sqft · eff. rate ${eff_rate:.2f}/sqft"))
            tier = banner_tier(combined)
            for i, lbl in enumerate(self.bn_tier_labels, start=1):
                if i == tier:
                    lbl.configure(fg=AMBER, bg=SURFACE)
                else:
                    lbl.configure(fg=MUTED, bg=SURFACE2)
            self.render_banner_cart()

        def add_banner_to_cart(self):
            w, h = self._bn_dims_inches()
            qty = max(1, self.bn_qty.get())
            if self.bn_unit == "in":
                wd, hd = f"{w:g}in", f"{h:g}in"
            else:
                wd, hd = f"{w / 12:.2f}ft", f"{h / 12:.2f}ft"
            self.banner_cart.append({"w": w, "h": h, "qty": qty,
                                     "sqft": rect_sqft(w, h),
                                     "wd": wd, "hd": hd})
            self.recalc_banner()

        def remove_banner_from_cart(self, index):
            del self.banner_cart[index]
            self.recalc_banner()

        def reset_banner_cart(self):
            self.banner_cart = []
            self.recalc_banner()

        def render_banner_cart(self):
            for child in self.bn_cart_frame.winfo_children():
                child.destroy()
            items = self.banner_cart
            if not items:
                tk.Label(self.bn_cart_frame,
                         text="No items yet — set a size above and click Add",
                         fg=MUTED, bg=SURFACE, font=("Courier", 9)).pack(pady=8)
                self.bn_totals_frame.pack_forget()
                return
            total_sqft = sum(i["sqft"] * i["qty"] for i in items)
            total_price = banner_price(total_sqft)
            for idx, item in enumerate(items):
                isqft = item["sqft"] * item["qty"]
                price = (isqft / total_sqft) * total_price if total_sqft else 0.0
                row = tk.Frame(self.bn_cart_frame, bg=SURFACE2, padx=8, pady=6)
                row.pack(fill="x", pady=2)
                info = tk.Frame(row, bg=SURFACE2)
                info.pack(side="left", fill="x", expand=True)
                tk.Label(info, text=f"{item['wd']} × {item['hd']}  × {item['qty']}",
                         fg=TEXT, bg=SURFACE2, font=("Courier", 9),
                         anchor="w").pack(fill="x")
                tk.Label(info,
                         text=f"{item['sqft']:.3f} sqft ea · {isqft:.3f} sqft total",
                         fg=MUTED, bg=SURFACE2, font=("Courier", 8),
                         anchor="w").pack(fill="x")
                tk.Label(row, text=fmt(price), fg=AMBER, bg=SURFACE2,
                         font=("Courier", 10, "bold")).pack(side="left", padx=8)
                flat_button(row, "×", lambda i=idx: self.remove_banner_from_cart(i),
                            fg=RED, padx=8, pady=2).pack(side="left")
            self.bn_totals_frame.pack(fill="x", pady=(6, 0))
            self.bn_total.value_label.configure(text=fmt(total_price))

        # ---------------------------------------------------------------
        # Signs tab
        # ---------------------------------------------------------------
        def _build_sign_tab(self, root):
            self.sg_w = tk.StringVar(value="24")
            self.sg_h = tk.StringVar(value="18")
            self.sg_qty = tk.StringVar(value="1")
            self.sg_labor = tk.StringVar(value="0")

            flat_button(root, "⚙ Material Costs & Settings",
                        self.open_sign_settings, fg=ORANGE, pady=8
                        ).pack(fill="x", pady=(4, 8))

            c = card(root)
            c.pack(fill="x", pady=4)
            section_label(c, "01 — Substrate").pack(fill="x")
            style = ttk.Style(self)
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("Dark.TCombobox", fieldbackground=SURFACE2,
                            background=SURFACE2, foreground=TEXT,
                            arrowcolor=TEXT, bordercolor=BORDER)
            style.map("Dark.TCombobox",
                      fieldbackground=[("readonly", SURFACE2)],
                      foreground=[("readonly", TEXT)],
                      selectbackground=[("readonly", SURFACE2)],
                      selectforeground=[("readonly", TEXT)])
            self.option_add("*TCombobox*Listbox.background", SURFACE2)
            self.option_add("*TCombobox*Listbox.foreground", TEXT)
            self.sg_substrate = ttk.Combobox(c, state="readonly",
                                             style="Dark.TCombobox")
            self.sg_substrate.pack(fill="x", pady=(4, 8))
            self.sg_substrate.bind("<<ComboboxSelected>>",
                                   lambda _e: self.recalc_sign())

            section_label(c, "02 — Vinyl Overlay (optional)").pack(fill="x")
            self.sg_vinyl = ttk.Combobox(c, state="readonly",
                                         style="Dark.TCombobox")
            self.sg_vinyl.pack(fill="x", pady=(4, 8))
            self.sg_vinyl.bind("<<ComboboxSelected>>",
                               lambda _e: self.recalc_sign())
            self._refresh_sign_selects()

            section_label(c, "03 — Sign Size (inches)").pack(fill="x")
            grid = tk.Frame(c, bg=SURFACE)
            grid.pack(fill="x", pady=(4, 8))
            for col, (label, var) in enumerate(
                    (("Width", self.sg_w), ("Height", self.sg_h),
                     ("Quantity", self.sg_qty), ("Labor ($)", self.sg_labor))):
                g = tk.Frame(grid, bg=SURFACE)
                g.grid(row=col // 2, column=col % 2, sticky="ew",
                       padx=(0 if col % 2 == 0 else 12, 0), pady=2)
                grid.grid_columnconfigure(col % 2, weight=1)
                tk.Label(g, text=label.upper(), fg=MUTED, bg=SURFACE,
                         font=("Courier", 8)).pack(anchor="w")
                e = dark_entry(g, var, width=10)
                e.pack(fill="x")
                e.bind("<KeyRelease>", lambda _e: self.recalc_sign())

            section_label(c, "04 — Sides").pack(fill="x")
            self.sg_sides_group = ToggleGroup(
                c, [(1, "Single Sided"), (2, "Double Sided")],
                command=lambda _v: self.recalc_sign(),
                colors={1: ORANGE, 2: ORANGE})
            self.sg_sides_group.frame.pack(fill="x", pady=(4, 8))

            section_label(c, "05 — Markup").pack(fill="x")
            self.sg_markup_group = ToggleGroup(
                c, [(1.5, "1.5×"), (2.0, "2×"), (2.5, "2.5×"), (3.0, "3×")],
                command=lambda _v: self.recalc_sign(),
                colors={m: ORANGE for m in (1.5, 2.0, 2.5, 3.0)})
            self.sg_markup_group.set(2.5, fire=False)
            self.sg_markup_group.frame.pack(fill="x", pady=(4, 8))

            self.sg_breakdown = tk.Label(c, text="", fg=MUTED, bg=SURFACE2,
                                         font=("Courier", 9), justify="left",
                                         anchor="w", padx=10, pady=8)
            self.sg_breakdown.pack(fill="x", pady=(4, 0))
            flat_button(c, "+ Add to Quote", self.add_sign_to_cart,
                        fg=ORANGE, pady=8).pack(fill="x", pady=(10, 0))

            cc = card(root)
            cc.pack(fill="x", pady=(4, 12))
            section_label(cc, "06 — Quote Summary").pack(fill="x")
            self.sg_cart_frame = tk.Frame(cc, bg=SURFACE)
            self.sg_cart_frame.pack(fill="x", pady=(6, 0))
            self.sg_totals_frame = tk.Frame(cc, bg=SURFACE)
            self.sg_cost_total = self._total_row(self.sg_totals_frame,
                                                 "YOUR TOTAL COST", ORANGE,
                                                 size=12)
            self.sg_suggested_total = self._total_row(self.sg_totals_frame,
                                                      "⬆ SUGGESTED PRICE", GREEN,
                                                      size=13)
            flat_button(self.sg_totals_frame, "↻ Clear Quote",
                        self.reset_sign_cart, fg=RED, pady=5
                        ).pack(fill="x", pady=(8, 0))
            self.render_sign_cart()

        def _refresh_sign_selects(self):
            sub_idx = self.sg_substrate.current()
            vin_idx = self.sg_vinyl.current()
            self.sg_substrate["values"] = ["— Select substrate —"] + [
                f"{s['name']} — ${sub_cost_per_sqft(s):.2f}/sqft"
                for s in SUBSTRATES]
            self.sg_vinyl["values"] = ["— None / Digital print only —"] + [
                f"{v['name']} — ${vinyl_cost_per_sqft(v):.2f}/sqft"
                for v in VINYLS]
            self.sg_substrate.current(max(0, sub_idx))
            self.sg_vinyl.current(max(0, vin_idx))

        def _selected_sign_materials(self):
            sub_i = self.sg_substrate.current() - 1
            vin_i = self.sg_vinyl.current() - 1
            sub = SUBSTRATES[sub_i] if sub_i >= 0 else None
            vin = VINYLS[vin_i] if vin_i >= 0 else None
            return sub, vin

        def _sign_inputs(self):
            return (parse_float(self.sg_w), parse_float(self.sg_h),
                    max(1, parse_int(self.sg_qty, 1)),
                    parse_float(self.sg_labor))

        def recalc_sign(self):
            sub, vin = self._selected_sign_materials()
            w, h, qty, labor = self._sign_inputs()
            if not sub or w <= 0 or h <= 0:
                self.sg_breakdown.configure(
                    text="Select a substrate and enter dimensions to calculate")
                return
            sides = self.sg_sides_group.value
            markup = self.sg_markup_group.value
            q = sign_quote(sub, vin, w, h, qty, labor, sides, markup)
            lines = [f"Size            {w:g}\" × {h:g}\" = {q['sqft']:.3f} sqft",
                     f"Substrate       {sub['name']}: {fmt(q['sub_cost'])} ea"]
            if vin:
                sides_note = " (both sides)" if sides == 2 else ""
                lines.append(f"Vinyl           {vin['name']}{sides_note}:"
                             f" {fmt(q['vin_cost'])} ea")
            lines.append(f"Labor           {fmt(labor)}")
            lines.append(f"Cost per unit   {fmt(q['unit_cost'])}")
            if qty > 1:
                lines.append(f"× {qty} units       {fmt(q['total_cost'])}")
            lines.append(f"YOUR TOTAL COST {fmt(q['total_cost'])}")
            lines.append(f"⬆ SUGGESTED     {fmt(q['suggested'])}"
                         f"  ({markup:g}× — {q['margin']:.0f}% margin)")
            self.sg_breakdown.configure(text="\n".join(lines))

        def add_sign_to_cart(self):
            sub, vin = self._selected_sign_materials()
            w, h, qty, labor = self._sign_inputs()
            if not sub or w <= 0 or h <= 0:
                messagebox.showinfo(
                    "Groot's Workshop",
                    "Please select a substrate and enter dimensions first.")
                return
            sides = self.sg_sides_group.value
            markup = self.sg_markup_group.value
            q = sign_quote(sub, vin, w, h, qty, labor, sides, markup)
            self.sign_cart.append({
                "w": w, "h": h, "qty": qty, "labor": labor, "sides": sides,
                "markup": markup, "sub_name": sub["name"],
                "vin_name": vin["name"] if vin else None,
                "sqft": q["sqft"], "total_cost": q["total_cost"],
                "suggested": q["suggested"],
            })
            self.render_sign_cart()

        def remove_sign_from_cart(self, index):
            del self.sign_cart[index]
            self.render_sign_cart()

        def reset_sign_cart(self):
            self.sign_cart = []
            self.render_sign_cart()

        def render_sign_cart(self):
            for child in self.sg_cart_frame.winfo_children():
                child.destroy()
            items = self.sign_cart
            if not items:
                tk.Label(self.sg_cart_frame,
                         text="No items yet — configure a sign above and Add to Quote",
                         fg=MUTED, bg=SURFACE, font=("Courier", 9)).pack(pady=8)
                self.sg_totals_frame.pack_forget()
                return
            for idx, item in enumerate(items):
                row = tk.Frame(self.sg_cart_frame, bg=SURFACE2, padx=8, pady=6)
                row.pack(fill="x", pady=2)
                info = tk.Frame(row, bg=SURFACE2)
                info.pack(side="left", fill="x", expand=True)
                sided = "  [2-SIDED]" if item["sides"] == 2 else ""
                tk.Label(info,
                         text=f"{item['w']:g}\" × {item['h']:g}\""
                              f"  × {item['qty']}{sided}",
                         fg=TEXT, bg=SURFACE2, font=("Courier", 9),
                         anchor="w").pack(fill="x")
                vin_line = f" + {item['vin_name']}" if item["vin_name"] else ""
                tk.Label(info,
                         text=f"{item['sub_name']}{vin_line} ·"
                              f" {item['sqft']:.3f} sqft ea · labor"
                              f" {fmt(item['labor'])} · {item['markup']:g}× markup",
                         fg=MUTED, bg=SURFACE2, font=("Courier", 8),
                         anchor="w").pack(fill="x")
                prices = tk.Frame(row, bg=SURFACE2)
                prices.pack(side="left", padx=8)
                tk.Label(prices, text=f"{fmt(item['total_cost'])} cost",
                         fg=MUTED, bg=SURFACE2, font=("Courier", 8)
                         ).pack(anchor="e")
                tk.Label(prices, text=fmt(item["suggested"]), fg=ORANGE,
                         bg=SURFACE2, font=("Courier", 10, "bold")
                         ).pack(anchor="e")
                flat_button(row, "×", lambda i=idx: self.remove_sign_from_cart(i),
                            fg=RED, padx=8, pady=2).pack(side="left")
            self.sg_totals_frame.pack(fill="x", pady=(6, 0))
            self.sg_cost_total.value_label.configure(
                text=fmt(sum(i["total_cost"] for i in items)))
            self.sg_suggested_total.value_label.configure(
                text=fmt(sum(i["suggested"] for i in items)))

        # ---- sign settings dialog --------------------------------------
        def open_sign_settings(self):
            win = tk.Toplevel(self)
            win.title("Material Costs & Settings")
            win.configure(bg=BG)
            win.geometry("560x640")
            sf = ScrollFrame(win)
            sf.pack(fill="both", expand=True, padx=10, pady=10)
            body = sf.body

            sc = card(body)
            sc.pack(fill="x", pady=4)
            section_label(sc, "Substrates — enter your sheet cost").pack(fill="x")
            for sub in SUBSTRATES:
                self._settings_substrate_row(sc, sub)

            vc = card(body)
            vc.pack(fill="x", pady=4)
            section_label(vc, "Vinyl — combined vinyl + laminate cost"
                          ).pack(fill="x")
            hdr = tk.Frame(vc, bg=SURFACE)
            hdr.pack(fill="x", pady=(6, 0))
            for text, width in (("NAME", 18), ("W(IN)", 6), ("L(FT)", 6),
                                ("COST", 8), ("$/SQFT", 9)):
                tk.Label(hdr, text=text, fg=MUTED, bg=SURFACE, width=width,
                         font=("Courier", 7), anchor="w").pack(side="left")
            for vin in VINYLS:
                self._settings_vinyl_row(vc, vin)

        def _settings_substrate_row(self, parent, sub):
            row = tk.Frame(parent, bg=SURFACE)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=sub["name"], fg=TEXT, bg=SURFACE, width=16,
                     anchor="w", font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(row, text=f'{sub["sheetW"]}"×{sub["sheetH"]}" sheet',
                     fg=MUTED, bg=SURFACE, font=("Courier", 8)).pack(side="left")
            cpf = tk.Label(row, text=f"${sub_cost_per_sqft(sub):.3f}/sqft",
                           fg=ORANGE, bg=SURFACE, font=("Courier", 9))
            cpf.pack(side="right")
            var = tk.StringVar(value=f"{sub['cost']:g}")
            e = dark_entry(row, var, width=8)
            e.pack(side="right", padx=8)

            def on_change(_e=None):
                sub["cost"] = parse_float(var)
                cpf.configure(text=f"${sub_cost_per_sqft(sub):.3f}/sqft")
                self._refresh_sign_selects()
                self.recalc_sign()
            e.bind("<KeyRelease>", on_change)

        def _settings_vinyl_row(self, parent, vin):
            row = tk.Frame(parent, bg=SURFACE)
            row.pack(fill="x", pady=3)
            name_var = tk.StringVar(value=vin["name"])
            w_var = tk.StringVar(value=f"{vin['rollW']:g}")
            l_var = tk.StringVar(value=f"{vin['rollL']:g}")
            c_var = tk.StringVar(value=f"{vin['cost']:g}")
            ne = dark_entry(row, name_var, width=18)
            ne.pack(side="left")
            we = dark_entry(row, w_var, width=5)
            we.pack(side="left", padx=(6, 0))
            le = dark_entry(row, l_var, width=5)
            le.pack(side="left", padx=(6, 0))
            ce = dark_entry(row, c_var, width=7)
            ce.pack(side="left", padx=(6, 0))
            cpf = tk.Label(row, text=f"${vinyl_cost_per_sqft(vin):.3f}",
                           fg=ORANGE, bg=SURFACE, font=("Courier", 9))
            cpf.pack(side="left", padx=(8, 0))

            def on_change(_e=None):
                vin["name"] = name_var.get() or vin["name"]
                vin["rollW"] = parse_float(w_var, 54) or 54
                vin["rollL"] = parse_float(l_var, 150) or 150
                vin["cost"] = parse_float(c_var)
                cpf.configure(text=f"${vinyl_cost_per_sqft(vin):.3f}")
                self._refresh_sign_selects()
                self.recalc_sign()
            for e in (ne, we, le, ce):
                e.bind("<KeyRelease>", on_change)


def main():
    if tk is None:
        raise SystemExit(
            "tkinter is not available. Install it first:\n"
            "  Debian/Ubuntu:  sudo apt install python3-tk\n"
            "  Fedora:         sudo dnf install python3-tkinter\n"
            "  Windows/macOS:  reinstall Python from python.org and enable "
            "tcl/tk in the installer options.")
    App().mainloop()


if __name__ == "__main__":
    main()
