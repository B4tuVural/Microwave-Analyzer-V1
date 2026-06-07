"""
viz/theme.py
============
Tüm görsel bileşenler için tek renk/font kaynağı (single source of truth).

KARANLIK TEMA. Streamlit kabuğu (.streamlit/config.toml) ile aynı koyu zemini
paylaşır; böylece figürler arayüze gömülü gibi durur. Bir rengi değiştirmek
istediğinde tek yer burasıdır; figür kodlarına dokunmazsın (Open/Closed).
"""

from __future__ import annotations

from dataclasses import dataclass


# ----------------------------------------------------------------------
# Renk paleti (KARANLIK)
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Palette:
    # Yüzeyler — Streamlit dark zeminiyle uyumlu
    paper: str = "#0E1117"
    surface: str = "#11161F"
    panel: str = "#161B26"

    # Izgara / eğriler
    grid_major: str = "#9AA7C2"
    grid_minor: str = "#3C465C"
    unit_circle: str = "#5B8DEF"
    real_axis: str = "#FF6B6B"

    # Yardımcı çemberler
    vswr: str = "#34D399"
    return_loss: str = "#B794F6"

    # Önemli noktalar (semantik renkler — koyu zeminde parlak)
    load: str = "#FF5C5C"
    traveled: str = "#FF74B9"
    matched: str = "#FFD166"
    text: str = "#E6EAF1"
    muted: str = "#9AA7C2"

    # Stub / uygunlama noktaları (en fazla 4 çözüm)
    stub_cycle: tuple = ("#FFA94D", "#51CF66", "#4DABF7", "#CC8FF5")

    # Bölge etiketleri
    inductive: str = "#FF8A8A"
    capacitive: str = "#7FB0FF"

    # 3B'ye özel
    hemisphere_lo: str = "#1B2233"
    hemisphere_hi: str = "#2A3550"
    meridian: str = "#6C8BE0"
    parallel: str = "#3DD6C0"
    back_grid: str = "#4A5670"
    curve_r_3d: str = "#FFB055"
    curve_x_3d: str = "#FFE08A"

    # Devre şeması
    circuit_ink: str = "#E6EAF1"
    circuit_box_fill: str = "rgba(91,141,239,0.18)"
    circuit_box_edge: str = "#5B8DEF"
    accent_blue: str = "#6CA0FF"
    terminal_open: str = "#6CA0FF"
    terminal_short: str = "#FF7B7B"
    qw_highlight: str = "#22D3EE"

    # Hover / legend kutusu
    overlay_bg: str = "rgba(22,27,38,0.92)"


PALETTE = Palette()

FONT_FAMILY = "Georgia, 'Times New Roman', serif"
MONO_FAMILY = "'JetBrains Mono', Consolas, monospace"


def _hoverlabel() -> dict:
    return dict(bgcolor=PALETTE.panel, bordercolor=PALETTE.grid_major,
               font=dict(family=MONO_FAMILY, size=12, color=PALETTE.text))


def _legend(**over) -> dict:
    base = dict(bgcolor=PALETTE.overlay_bg, bordercolor=PALETTE.grid_minor,
                borderwidth=1, font=dict(size=11, family=FONT_FAMILY,
                                         color=PALETTE.text))
    base.update(over)
    return base


# ----------------------------------------------------------------------
# Ortak layout yardımcıları
# ----------------------------------------------------------------------
def base_2d_layout(title: str, limit: float = 1.18) -> dict:
    return dict(
        title=dict(text=title, x=0.5, xanchor="center",
                   font=dict(size=17, color=PALETTE.text, family=FONT_FAMILY)),
        paper_bgcolor=PALETTE.paper,
        plot_bgcolor=PALETTE.surface,
        xaxis=dict(range=[-limit, limit], showgrid=False, zeroline=False,
                   showticklabels=False, visible=False, constrain="domain"),
        yaxis=dict(range=[-limit, limit], showgrid=False, zeroline=False,
                   showticklabels=False, visible=False,
                   scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=52, b=90),
        height=720,
        showlegend=True,
        legend=_legend(orientation="h", yanchor="top", y=-0.10,
                       xanchor="center", x=0.5),
        hoverlabel=_hoverlabel(),
        dragmode="pan",
    )


def base_3d_layout(title: str) -> dict:
    axis = dict(showbackground=False, showgrid=False, zeroline=False,
                showticklabels=False, title="", range=[-1.25, 1.25],
                color=PALETTE.muted)
    return dict(
        title=dict(text=title, x=0.5, xanchor="center",
                   font=dict(size=17, color=PALETTE.text, family=FONT_FAMILY)),
        paper_bgcolor=PALETTE.paper,
        scene=dict(
            xaxis=axis, yaxis=axis,
            zaxis=dict(**{**axis, "range": [-0.15, 1.25]}),
            aspectmode="data",
            bgcolor=PALETTE.paper,
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.1)),
        ),
        margin=dict(l=0, r=0, t=48, b=0),
        showlegend=True,
        legend=_legend(yanchor="top", y=0.98, xanchor="left", x=0.01),
        hoverlabel=_hoverlabel(),
    )


def base_circuit_layout(title: str, subtitle: str,
                        width: float, height: float) -> dict:
    """Devre şeması layout'u. Etiketler add_annotation ile eklendiğinden burada
    `annotations` KOYULMAZ (yoksa update_layout onları ezer)."""
    return dict(
        paper_bgcolor=PALETTE.paper,
        plot_bgcolor=PALETTE.surface,
        xaxis=dict(range=[0, width], showgrid=False, zeroline=False,
                   showticklabels=False, visible=False, constrain="domain"),
        yaxis=dict(range=[0, height], showgrid=False, zeroline=False,
                   showticklabels=False, visible=False,
                   scaleanchor="x", scaleratio=1),
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        hovermode=False,
        dragmode="pan",
    )
