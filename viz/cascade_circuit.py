"""
viz/cascade_circuit.py
======================
Kademeli devrenin şematik gösterimi. viz.circuit._CircuitCanvas primitiflerini
yeniden kullanır (tel/düğüm/etiket/direnç/terminal — anti-spaghetti, DRY).

Soldan sağa: Kaynak → eleman zinciri → Yük. Her eleman bir yatay dilim kaplar:
* İletim hattı  → etiketli ray bölümü (Z₀, εr, θ)
* Seri stub     → üst rayda kesinti + yukarı çıkan iki iletken (gerçek seri)
* Paralel stub  → iki rayı köprüleyen aşağı inen yan hat

Ayrıntılı/ölçülü tek-eleman çizimleri ise eşleme alt-sekmesindeki build_circuit
tarafından sağlanır; buradaki şema zinciri bütün olarak özetler.
"""

from __future__ import annotations

import plotly.graph_objects as go

from viz.circuit import _CircuitCanvas, W, H
from viz.theme import PALETTE
from services.cascade import KIND_LINE, KIND_SERIES, KIND_SHUNT


def _term_str(termination: str) -> str:
    return "açık devre" if termination == "open" else "kısa devre"


def _zl_text(z: complex) -> str:
    return f"Z<sub>L</sub> = {z.real:.0f}{z.imag:+.0f}j Ω"


def build_cascade_circuit(result) -> go.Figure:
    c = _CircuitCanvas()
    y_top, y_bot = 245, 180
    y_mid = (y_top + y_bot) / 2
    x_left, x_load = 130, 870

    els = list(reversed(result.elements))   # kaynak → yük sırası

    c.label(x_left - 36, y_mid, "Kaynak", size=11, bold=True)
    c.label(x_left + 2, y_top + 34,
            f"Z<sub>in</sub> = {result.z_in.real:.0f}{result.z_in.imag:+.0f}j Ω",
            size=9, color=PALETTE.matched, bold=True, anchor="left")

    if not els:
        c.wire(x_left, y_top, x_load, y_top)
        c.wire(x_left, y_bot, x_load, y_bot)
        c.resistor_v(x_load, y_top, y_bot)
        c.label(x_load, y_top + 26, _zl_text(result.start_load), size=9, bold=True)
        return c.finalize("Kademeli Devre Şeması", "Henüz eleman eklenmedi")

    weights = [2.0 if e.kind == KIND_LINE else 1.3 for e in els]
    unit = (x_load - x_left) / sum(weights)

    x = x_left
    for k, (w, e) in enumerate(zip(weights, els)):
        seg = w * unit
        xc = x + seg / 2
        lab_dy = -16 if k % 2 == 0 else -30   # komşu etiketler çakışmasın

        if e.kind == KIND_SERIES:
            # üst ray kesilir; iki iletken yukarı (gerçek seri bağlantı)
            sx1, sx2 = xc - 7, xc + 7
            c.wire(x, y_top, sx1, y_top)
            c.wire(sx2, y_top, x + seg, y_top)
            c.wire(x, y_bot, x + seg, y_bot)
            c.node(sx1, y_top); c.node(sx2, y_top)
            up = y_top + 58
            c.wire(sx1, y_top, sx1, up, color=PALETTE.circuit_ink, width=2.2)
            c.wire(sx2, y_top, sx2, up, color=PALETTE.circuit_ink, width=2.2)
            c.stub_terminal(sx1, sx2, up, _term_str(e.termination), label_dy=12)
            c.label(xc, y_bot + lab_dy - 18, f"Seri · {e.z0:.0f}Ω", size=8, bold=True)
            c.label(xc, y_bot + lab_dy - 30, f"εr={e.epsilon_r:g} · {e.theta_deg:.0f}°",
                    size=8, color=PALETTE.muted)

        elif e.kind == KIND_SHUNT:
            c.wire(x, y_top, x + seg, y_top)
            c.wire(x, y_bot, x + seg, y_bot)
            sx1, sx2 = xc, xc + 16
            c.node(sx1, y_top); c.node(sx2, y_bot)
            down = y_bot - 58
            c.wire(sx1, y_top, sx1, down, color=PALETTE.circuit_ink, width=2.2)
            c.wire(sx2, y_bot, sx2, down, color=PALETTE.circuit_ink, width=2.2)
            c.stub_terminal(sx1, sx2, down, _term_str(e.termination), label_dy=-14)
            c.label(xc + 8, y_bot + lab_dy - 18, f"Paralel · {e.z0:.0f}Ω",
                    size=8, bold=True)
            c.label(xc + 8, y_bot + lab_dy - 30, f"εr={e.epsilon_r:g} · {e.theta_deg:.0f}°",
                    size=8, color=PALETTE.muted)

        else:  # KIND_LINE
            c.wire(x, y_top, x + seg, y_top)
            c.wire(x, y_bot, x + seg, y_bot)
            c.label(xc, y_bot + lab_dy, f"Z₀={e.z0:.0f}Ω", size=8, bold=True)
            c.label(xc, y_bot + lab_dy - 12, f"εr={e.epsilon_r:g} · {e.theta_deg:.0f}°",
                    size=8, color=PALETTE.muted)

        # düğüm ayraç çizgisi (ince)
        if k < len(els) - 1:
            c.fig.add_trace(go.Scatter(
                x=[x + seg, x + seg], y=[y_bot - 4, y_top + 4], mode="lines",
                line=dict(color=PALETTE.grid_minor, width=0.8, dash="dot"),
                hoverinfo="skip", showlegend=False))
        x += seg

    c.resistor_v(x_load, y_top, y_bot)
    c.label(x_load, y_top + 26, _zl_text(result.start_load), size=9, bold=True)

    return c.finalize("Kademeli Devre Şeması", "Kaynak → eleman zinciri → Yük")
