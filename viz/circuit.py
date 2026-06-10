"""
viz/circuit.py
==============
Uygunlama çözümüne karşılık gelen devre şemasını Plotly ile çizer.

Tasarım
-------
* `_CircuitCanvas` yalnızca çizim primitiflerini bilir (tel, direnç, stub,
  terminal, ölçü oku, etiket). Tek sorumluluğu "şekil koymak"tır.
* Topolojiye özel fonksiyonlar (`_draw_shunt_stub`, `_draw_series_stub`,
  `_draw_quarter_wave`, `_draw_basic_line`) primitifleri birleştirir.
* `build_circuit` çözüm tipine bakıp doğru çizici fonksiyonu seçer (Strateji
  benzeri dağıtım). Yeni bir topoloji eklemek = yeni bir çizici + tek satır
  dağıtım, mevcut kod değişmez (Open/Closed).

Sayısal bilgi kutusu burada DEĞİL; sayfada st.metric/markdown ile gösterilir.
Böylece şema sade kalır, eski sürümdeki kalabalık ortadan kalkar.
"""

from __future__ import annotations

import plotly.graph_objects as go

from core.models import AnalyzerOutput, MatchingSolution
from viz.theme import PALETTE, FONT_FAMILY, base_circuit_layout
from unit_format import fmt_length, fmt_ohm

W, H = 1000.0, 420.0
INK = PALETTE.circuit_ink


class _CircuitCanvas:
    """Plotly tuvali: tel/direnç/stub/terminal/ölçü primitiflerini biriktirir."""

    def __init__(self) -> None:
        self.fig = go.Figure()

    # ---- temel primitifler -------------------------------------------
    def wire(self, x1, y1, x2, y2, color=INK, width=2.4, dash=None):
        self.fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=width, dash=dash),
            hoverinfo="skip", showlegend=False,
        ))

    def node(self, x, y, label=None):
        self.fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers",
            marker=dict(color=INK, size=8), hoverinfo="skip", showlegend=False,
        ))
        if label:
            self.label(x, y + 18, label, size=12, bold=True)

    def label(self, x, y, text, *, color=INK, size=12, bold=False, anchor="center"):
        self.fig.add_annotation(
            x=x, y=y, text=f"<b>{text}</b>" if bold else text, showarrow=False,
            font=dict(size=size, color=color, family=FONT_FAMILY),
            xanchor=anchor,
        )

    def resistor_v(self, x, y_top, y_bot):
        """Yük direncini dikey zikzak olarak çizer."""
        lead = (y_bot - y_top) * 0.2
        top, bot = y_top + lead, y_bot - lead
        self.wire(x, y_top, x, top)
        self.wire(x, bot, x, y_bot)
        seg, zig = 7, 13
        xs, ys = [x], [top]
        step = (bot - top) / seg
        for i in range(1, seg):
            xs.append(x + (zig if i % 2 else -zig))
            ys.append(top + i * step)
        xs.append(x); ys.append(bot)
        self.fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line=dict(color=INK, width=2.2),
            hoverinfo="skip", showlegend=False,
        ))

    def stub_terminal(self, x1, x2, y, kind: str, label_dy: float = -18,
                      size: int = 10):
        mid = (x1 + x2) / 2
        if "açık" in kind.lower():
            self.wire(x1 - 10, y, x1 + 10, y)
            self.wire(x2 - 10, y, x2 + 10, y)
            self.label(mid, y + label_dy, "Açık devre uç",
                       color=PALETTE.terminal_open, size=size)
        else:
            self.wire(x1, y, x2, y, width=2.6)
            self.label(mid, y + label_dy, "Kısa devre uç",
                       color=PALETTE.terminal_short, size=size)

    def dim_h(self, x1, x2, y, label):
        """Yatay ölçü oku (iki yönlü) + etiket."""
        self.fig.add_annotation(x=x2, y=y, ax=x1, ay=y, xref="x", yref="y",
                                axref="x", ayref="y", showarrow=True, arrowhead=3,
                                arrowsize=1.2, arrowwidth=1.4, arrowcolor=PALETTE.accent_blue)
        self.fig.add_annotation(x=x1, y=y, ax=x2, ay=y, xref="x", yref="y",
                                axref="x", ayref="y", showarrow=True, arrowhead=3,
                                arrowsize=1.2, arrowwidth=1.4, arrowcolor=PALETTE.accent_blue)
        self.label((x1 + x2) / 2, y + 14, label, color=PALETTE.accent_blue, size=11, bold=True)

    def dim_v(self, x, y1, y2, label):
        self.fig.add_annotation(x=x, y=y2, ax=x, ay=y1, xref="x", yref="y",
                                axref="x", ayref="y", showarrow=True, arrowhead=3,
                                arrowsize=1.2, arrowwidth=1.4, arrowcolor=PALETTE.accent_blue)
        self.fig.add_annotation(x=x, y=y1, ax=x, ay=y2, xref="x", yref="y",
                                axref="x", ayref="y", showarrow=True, arrowhead=3,
                                arrowsize=1.2, arrowwidth=1.4, arrowcolor=PALETTE.accent_blue)
        self.label(x + 12, (y1 + y2) / 2, label, color=PALETTE.accent_blue,
                   size=11, bold=True, anchor="left")

    def finalize(self, title, subtitle):
        # Başlık küçük font: 40+ karakterlik metodlar mobil genişlikte sığsın
        self.label(W / 2, H - 18, title, size=11, bold=True)
        if subtitle:
            self.label(W / 2, H - 36, subtitle, color=PALETTE.muted, size=9)
        self.fig.update_layout(**base_circuit_layout(title, subtitle, W, H))
        return self.fig


# ----------------------------------------------------------------------
# Ortak parçalar
# ----------------------------------------------------------------------
def _zl_text(output: AnalyzerOutput) -> str:
    z = output.basic.z_load
    # Kısa format: .0f (tam sayı) — mobil sığması için
    return f"Z_L = {z.real:.0f}{z.imag:+.0f}j Ω"


def _common_frame(c: _CircuitCanvas, output: AnalyzerOutput, x_left, x_load,
                  y_top, y_bot):
    """Kaynak etiketi, iki telli hat, Z0 etiketi, yük direnci ve ZL yazısı."""
    y_mid = (y_top + y_bot) / 2
    c.wire(x_left, y_top, x_load, y_top)
    c.wire(x_left, y_bot, x_load, y_bot)
    c.label(x_left - 36, y_mid, "Kaynak", size=12, bold=True)
    c.label((x_left + x_load) / 2, y_bot - 22,
            f"Z₀ = {output.basic.z0:.2f} Ω", size=12, bold=True)
    c.resistor_v(x_load, y_top, y_bot)
    c.label(x_load, y_top + 28, _zl_text(output), size=9, bold=True, anchor="center")


# ----------------------------------------------------------------------
# Topolojiye özel çizimler
# ----------------------------------------------------------------------
def _draw_basic_line(output: AnalyzerOutput, length_unit="λ", ohm_unit="Ω") -> go.Figure:
    c = _CircuitCanvas()
    y_top, y_bot = 250, 150
    x_left, x_load = 120, 760
    _common_frame(c, output, x_left, x_load, y_top, y_bot)
    return c.finalize("Temel İletim Hattı", "Yük empedansı gösterimi")


def _draw_shunt_stub(output: AnalyzerOutput, sol: MatchingSolution,
                     length_unit="λ", ohm_unit="Ω") -> go.Figure:
    c = _CircuitCanvas()
    wl = output.basic.wavelength_m
    y_top, y_bot = 280, 200
    x_left, x_load = 120, 760
    total = x_load - x_left

    d_ratio = 0.45
    if sol.d_lambda is not None:
        d_ratio = max(0.18, min(0.82, 1.0 - sol.d_lambda / 0.5))
    x_stub = x_left + total * d_ratio

    _common_frame(c, output, x_left, x_load, y_top, y_bot)
    c.node(x_stub, y_top, "A")
    c.node(x_stub, y_bot, "B")

    sx1, sx2 = x_stub + 16, x_stub + 50
    c.wire(x_stub, y_top, sx1, y_top)
    c.wire(x_stub, y_bot, sx2, y_bot)
    stub_end = 70
    c.wire(sx1, y_top, sx1, stub_end, color=PALETTE.circuit_ink, width=2.8)
    c.wire(sx2, y_bot, sx2, stub_end, color=PALETTE.circuit_ink, width=2.8)
    c.stub_terminal(sx1, sx2, stub_end, sol.stub_type)
    c.label((sx1 + sx2) / 2, stub_end - 36, "Paralel Yan Hat", size=11, bold=True)

    if sol.d_lambda is not None:
        c.dim_h(x_stub, x_load, y_top + 42, f"d = {fmt_length(sol.d_lambda, wl, length_unit)}")
    if sol.stub_length_lambda is not None:
        c.dim_v(sx2 + 34, y_bot, stub_end,
                f"ℓ = {fmt_length(sol.stub_length_lambda, wl, length_unit)}")

    return c.finalize(sol.method, "Paralel bağlantılı yan hat")


def _draw_series_stub(output: AnalyzerOutput, sol: MatchingSolution,
                      length_unit="λ", ohm_unit="Ω") -> go.Figure:
    c = _CircuitCanvas()
    wl = output.basic.wavelength_m
    y_top, y_bot = 210, 140
    x_left, x_load = 120, 760
    total = x_load - x_left
    y_mid = (y_top + y_bot) / 2

    d_ratio = 0.45
    if sol.d_lambda is not None:
        d_ratio = max(0.18, min(0.82, 1.0 - sol.d_lambda / 0.5))
    x_stub = x_left + total * d_ratio

    # Alt ray kesintisiz (dönüş iletkeni)
    c.wire(x_left, y_bot, x_load, y_bot)
    c.label(x_left - 36, y_mid, "Kaynak", size=12, bold=True)
    # Z₀ kaynak tarafına yazılır; d ölçüsü yük tarafında olduğundan üst üste binmez.
    z0_x = max((x_left + x_stub) / 2, x_left + 95)
    c.label(z0_x, y_bot - 20, f"Z₀ = {output.basic.z0:.2f} Ω", size=12, bold=True)

    # Üst ray x_stub'ta KESİLİR; seri yan hat bu kesintiye seri eklenir.
    # İki iletken üst rayın kaynak-tarafı ve yük-tarafına bağlanır (paralelden
    # farkı: her iki iletken de ÜST raydadır, alt rayı köprülemez).
    sx1, sx2 = x_stub - 17, x_stub + 17
    c.wire(x_left, y_top, sx1, y_top)
    c.wire(sx2, y_top, x_load, y_top)
    c.node(sx1, y_top)
    c.node(sx2, y_top)

    # Seri yan hat iletkenleri YUKARI uzanır (alt rayı kesmemek için).
    stub_top = 320
    c.wire(sx1, y_top, sx1, stub_top, color=PALETTE.circuit_ink, width=2.8)
    c.wire(sx2, y_top, sx2, stub_top, color=PALETTE.circuit_ink, width=2.8)
    # Uç etiketi terminalin ÜSTÜNE konur; yukarı stub iletkenlerine binmez.
    c.stub_terminal(sx1, sx2, stub_top, sol.stub_type, label_dy=16)
    c.label((sx1 + sx2) / 2, stub_top + 34, "Seri Yan Hat", size=11, bold=True)

    # Yük
    c.resistor_v(x_load, y_top, y_bot)
    c.label(x_load, y_top + 28, _zl_text(output), size=9, bold=True, anchor="center")

    # Ölçüler: d yük tarafında alt rayın altında, ℓ yan hat boyunca
    if sol.d_lambda is not None:
        c.dim_h(x_stub, x_load, y_bot - 45, f"d = {fmt_length(sol.d_lambda, wl, length_unit)}")
    if sol.stub_length_lambda is not None:
        c.dim_v(sx2 + 34, y_top, stub_top, f"ℓ = {fmt_length(sol.stub_length_lambda, wl, length_unit)}")

    return c.finalize(sol.method, "Seri bağlantılı yan hat")


def _draw_quarter_wave(output: AnalyzerOutput, sol: MatchingSolution,
                       length_unit="λ", ohm_unit="Ω") -> go.Figure:
    c = _CircuitCanvas()
    y_top, y_bot = 260, 180
    x_left, x_load = 120, 760
    y_mid = (y_top + y_bot) / 2
    x_a = x_left + (x_load - x_left) * 0.4
    x_b = x_left + (x_load - x_left) * 0.66

    c.wire(x_left, y_top, x_a, y_top)
    c.wire(x_left, y_bot, x_a, y_bot)
    # λ/4 bölümü (vurgulu kalın renk)
    c.wire(x_a, y_top, x_b, y_top, color=PALETTE.qw_highlight, width=5)
    c.wire(x_a, y_bot, x_b, y_bot, color=PALETTE.qw_highlight, width=5)
    c.wire(x_b, y_top, x_load, y_top)
    c.wire(x_b, y_bot, x_load, y_bot)

    c.label(x_left - 36, y_mid, "Kaynak", size=12, bold=True)
    zt = (f"Z<sub>t</sub> = {fmt_ohm(sol.required_stub_value, ohm_unit)}"
          if sol.required_stub_value is not None else "Z<sub>t</sub>")
    c.label((x_a + x_b) / 2, y_top + 30, zt, color=PALETTE.qw_highlight, size=12, bold=True)
    c.dim_h(x_a, x_b, y_top + 56, "λ / 4")

    c.resistor_v(x_load, y_top, y_bot)
    c.label(x_load, y_top + 28, _zl_text(output), size=9, bold=True, anchor="center")
    return c.finalize("Çeyrek Dalga Transformatör", "λ/4 hat ile empedans uygunlaması")


# ----------------------------------------------------------------------
# Dağıtım (strateji seçimi)
# ----------------------------------------------------------------------
def build_circuit(output: AnalyzerOutput | None, solution_index: int = 0,
                  length_unit: str = "λ", ohm_unit: str = "Ω") -> go.Figure:
    """Seçili çözüme uygun devre şemasını üretir.

    length_unit: d ve ℓ etiketlerinin birimi (λ/cm/m/mm/μm/nm).
    ohm_unit   : çeyrek dalga Z_t etiketinin birimi (Ω/mΩ/μΩ/nΩ).
    """
    if output is None:
        c = _CircuitCanvas()
        c.label(W / 2, H / 2, "Henüz analiz yapılmadı.", size=14, bold=True)
        return c.finalize("Devre Şeması", "")

    solutions = output.matching_solutions
    if not solutions:
        return _draw_basic_line(output, length_unit, ohm_unit)

    sol = solutions[min(solution_index, len(solutions) - 1)]
    method = sol.method.lower()
    if "çeyrek dalga" in method:
        return _draw_quarter_wave(output, sol, length_unit, ohm_unit)
    if "paralel" in method:
        return _draw_shunt_stub(output, sol, length_unit, ohm_unit)
    if "seri" in method:
        return _draw_series_stub(output, sol, length_unit, ohm_unit)
    return _draw_basic_line(output, length_unit, ohm_unit)
