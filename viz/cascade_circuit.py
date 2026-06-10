"""
viz/cascade_circuit.py
======================
Kademeli devrenin şematik gösterimi. viz.circuit._CircuitCanvas primitiflerini
yeniden kullanır (anti-spaghetti, DRY).

Soldan sağa: Kaynak → eleman zinciri → Yük. Elemanlar merkeze toplanır,
aralarındaki boşluk kısa tutulur. İletim hatları çeyrek-dalga çözümündeki gibi
kalın/vurgulu çizilir; paralel ve seri stub'lar ayrıntılı çizimlerle aynı
biçimde (terminal uçlu yan hatlar) gösterilir.
"""

from __future__ import annotations

import plotly.graph_objects as go

from viz.circuit import _CircuitCanvas
from viz.theme import PALETTE, base_circuit_layout
from services.cascade import KIND_LINE, KIND_SERIES, KIND_SHUNT

_W, _H = 1000.0, 500.0
_Y_TOP, _Y_BOT = 288.0, 214.0
_Y_MID = (_Y_TOP + _Y_BOT) / 2
_X_SRC, _X_LOAD = 110.0, 890.0


def _term_str(t: str) -> str:
    return "açık devre" if t == "open" else "kısa devre"


def _zl_text(z: complex) -> str:
    return f"Z<sub>L</sub> = {z.real:.0f}{z.imag:+.0f}j Ω"


def _elem_caption(e) -> list[str]:
    """Eleman altı kısa etiket satırları."""
    length = e.d_lambda if e.kind == KIND_LINE else e.stub_len_lambda
    return [f"Z₀={e.z0:.0f}Ω · εr={e.epsilon_r:g}", f"ℓ={length:.3f}λ"]


def build_cascade_circuit(result) -> go.Figure:
    c = _CircuitCanvas()
    draw = list(reversed(result.elements))   # kaynak → yük

    # --- yerleşim: elemanları ortala, aralar kısa --------------------
    slot = {KIND_LINE: 172.0, KIND_SERIES: 150.0, KIND_SHUNT: 150.0}
    widths = [slot[e.kind] for e in draw]
    content = sum(widths)
    avail = (_X_LOAD - _X_SRC) - 110
    if content > avail and content > 0:
        k = avail / content
        widths = [w * k for w in widths]
        content = sum(widths)
    cluster_start = (_X_SRC + _X_LOAD) / 2 - content / 2

    # --- kaynak + lead ray -------------------------------------------
    c.label(_X_SRC - 4, _Y_MID, "Kaynak", size=14, bold=True)
    c.label(_X_SRC + 6, _Y_TOP + 40,
            f"Z<sub>in</sub> = {result.z_in.real:.0f}{result.z_in.imag:+.0f}j Ω",
            size=12, color=PALETTE.matched, bold=True, anchor="left")
    c.wire(_X_SRC, _Y_TOP, cluster_start, _Y_TOP)
    c.wire(_X_SRC, _Y_BOT, cluster_start, _Y_BOT)

    x = cluster_start
    for k, (w, e) in enumerate(zip(widths, draw)):
        xs, xe, xc = x, x + w, x + w / 2
        cap = _elem_caption(e)
        lab_y = _Y_BOT - 24 if k % 2 == 0 else _Y_BOT - 54

        if e.kind == KIND_LINE:
            # çeyrek-dalga gibi kalın/vurgulu hat
            c.wire(xs, _Y_TOP, xe, _Y_TOP, color=PALETTE.qw_highlight, width=5)
            c.wire(xs, _Y_BOT, xe, _Y_BOT, color=PALETTE.qw_highlight, width=5)
            tag = "Yük hattı" if e.is_load_line else "İletim hattı"
            c.label(xc, lab_y, tag, size=13, bold=True, color=PALETTE.qw_highlight)
            for i, line in enumerate(cap):
                c.label(xc, lab_y - 16 - 14 * i, line, size=11, color=PALETTE.muted)

        elif e.kind == KIND_SERIES:
            # üst rayda kesinti + yukarı çıkan iki iletken (gerçek seri)
            g = 9
            c.wire(xs, _Y_TOP, xc - g, _Y_TOP)
            c.wire(xc + g, _Y_TOP, xe, _Y_TOP)
            c.wire(xs, _Y_BOT, xe, _Y_BOT)
            c.node(xc - g, _Y_TOP); c.node(xc + g, _Y_TOP)
            up = _Y_TOP + 72
            c.wire(xc - g, _Y_TOP, xc - g, up, color=PALETTE.circuit_ink, width=2.8)
            c.wire(xc + g, _Y_TOP, xc + g, up, color=PALETTE.circuit_ink, width=2.8)
            c.stub_terminal(xc - g, xc + g, up, _term_str(e.termination),
                            label_dy=16, size=12)
            c.label(xc, lab_y, "Seri stub", size=13, bold=True)
            for i, line in enumerate(cap):
                c.label(xc, lab_y - 16 - 14 * i, line, size=11, color=PALETTE.muted)

        else:  # KIND_SHUNT — ayrıntılı çizimle AYNI biçim (net açık devre)
            c.wire(xs, _Y_TOP, xe, _Y_TOP)
            c.wire(xs, _Y_BOT, xe, _Y_BOT)
            c.node(xc, _Y_TOP, None)
            c.node(xc, _Y_BOT, None)
            # iki iletken 34px aralıklı → açık devre çubukları net ayrık
            sx1, sx2 = xc - 17, xc + 17
            down = _Y_BOT - 76
            c.wire(xc, _Y_TOP, sx1, _Y_TOP)        # üst raydan (A) sola
            c.wire(xc, _Y_BOT, sx2, _Y_BOT)        # alt raydan (B) sağa
            c.wire(sx1, _Y_TOP, sx1, down, color=PALETTE.circuit_ink, width=2.8)
            c.wire(sx2, _Y_BOT, sx2, down, color=PALETTE.circuit_ink, width=2.8)
            c.stub_terminal(sx1, sx2, down, _term_str(e.termination),
                            label_dy=-18, size=12)
            # paralel stub aşağı iner → etiket rayın ÜSTÜNE (çakışma olmasın)
            top_y = _Y_TOP + 22 if k % 2 == 0 else _Y_TOP + 56
            c.label(xc, top_y + 16, "Paralel stub", size=13, bold=True)
            for i, line in enumerate(cap):
                c.label(xc, top_y - 14 * i, line, size=11, color=PALETTE.muted)

        # düğüm ayraç (ince noktalı)
        if k < len(draw) - 1:
            c.fig.add_trace(go.Scatter(
                x=[xe, xe], y=[_Y_BOT - 3, _Y_TOP + 3], mode="lines",
                line=dict(color=PALETTE.grid_minor, width=0.8, dash="dot"),
                hoverinfo="skip", showlegend=False))
        x = xe

    # --- yüke lead ray + direnç --------------------------------------
    cluster_end = x
    c.wire(cluster_end, _Y_TOP, _X_LOAD, _Y_TOP)
    c.wire(cluster_end, _Y_BOT, _X_LOAD, _Y_BOT)
    c.resistor_v(_X_LOAD, _Y_TOP, _Y_BOT)
    c.label(_X_LOAD, _Y_TOP + 30, _zl_text(result.start_load), size=13, bold=True)

    # --- başlık (özel yükseklikle finalize) --------------------------
    c.label(_W / 2, _H - 20, "Kademeli Devre Şeması", size=16, bold=True)
    c.label(_W / 2, _H - 42, "Kaynak → eleman zinciri → Yük",
            color=PALETTE.muted, size=12)
    c.fig.update_layout(**base_circuit_layout("", "", _W, _H))
    return c.fig
