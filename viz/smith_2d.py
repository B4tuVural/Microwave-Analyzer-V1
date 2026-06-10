"""
viz/smith_2d.py
===============
İnteraktif ve okunabilir 2B Smith diyagramı (Plotly).

Tasarım ilkeleri
----------------
* Saf fonksiyon: girdi (AnalyzerOutput, ViewSettings) -> çıktı (go.Figure).
  Streamlit'e hiç bağımlılığı yoktur, bu yüzden tek başına test edilebilir.
* Okunabilirlik: ağır sayısal detay grafiğe yığılmaz; fareyle üzerine gelince
  (hover) zengin bilgi kutusu çıkar. Grafikte yalnızca kritik noktaların kısa
  etiketleri durur. Böylece eski sürümdeki "üst üste binen okunmaz kutular"
  sorunu ortadan kalkar.
* Etkileşim: Plotly doğal olarak zoom/pan/hover sağlar; nokta üzerine gelmek
  Z, Y, Γ, VSWR değerlerini gösterir.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from core.models import AnalyzerOutput
from core.rf_math import gamma_to_z, gamma_to_y, vswr_from_gamma
from core.smith_curves import (
    constant_resistance_curve, constant_reactance_curve,
    constant_conductance_curve, constant_susceptance_curve,
    gamma_circle, default_resistance_values, default_reactance_values,
    default_vswr_values,
)
from core.transmission_line import rotate_gamma
from viz.theme import PALETTE, FONT_FAMILY, base_2d_layout


# ----------------------------------------------------------------------
# Hover metni: bir Γ noktasının tüm RF büyüklüklerini özetler
# ----------------------------------------------------------------------
def _point_hover(gamma: complex, z0: float, admittance: bool = False) -> str:
    z = gamma_to_z(gamma)
    y = gamma_to_y(gamma)
    vswr = vswr_from_gamma(gamma)
    vswr_txt = "∞" if not np.isfinite(vswr) else f"{vswr:.3f}"
    return (
        f"Γ = {gamma.real:.4f} {gamma.imag:+.4f}j<br>"
        f"|Γ| = {abs(gamma):.4f}  ∠ {np.degrees(np.angle(gamma)):.1f}°<br>"
        f"z = {z.real:.4f} {z.imag:+.4f}j<br>"
        f"Z = {z.real * z0:.2f} {z.imag * z0:+.2f}j Ω<br>"
        f"y = {y.real:.4f} {y.imag:+.4f}j<br>"
        f"VSWR = {vswr_txt}"
    )


def _curve_trace(gamma: np.ndarray, color: str, width: float,
                 dash: str | None = None, opacity: float = 1.0) -> go.Scatter:
    return go.Scatter(
        x=np.real(gamma), y=np.imag(gamma),
        mode="lines",
        line=dict(color=color, width=width, dash=dash),
        opacity=opacity, hoverinfo="skip", showlegend=False,
    )


def _detail_samples(detail: str) -> int:
    return {"low": 2400, "high": 7000}.get(detail, 5000)


# ----------------------------------------------------------------------
# Izgara (sabit R/X ya da G/B eğrileri)
# ----------------------------------------------------------------------
def _add_grid(fig: go.Figure, settings) -> None:
    admittance = settings.chart_mode_2d == "admittance"
    n = _detail_samples(settings.curve_detail_2d)
    major = {0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0}

    r_func = constant_conductance_curve if admittance else constant_resistance_curve
    x_func = constant_susceptance_curve if admittance else constant_reactance_curve

    if settings.show_resistance:
        for v in default_resistance_values(settings.curve_detail_2d):
            is_major = v in major
            fig.add_trace(_curve_trace(
                r_func(v, n=n),
                PALETTE.grid_major if is_major else PALETTE.grid_minor,
                0.9 if is_major else 0.5,
                opacity=0.85 if is_major else 0.55,
            ))

    if settings.show_reactance:
        for v in default_reactance_values(settings.curve_detail_2d):
            is_major = v in major
            color = PALETTE.grid_major if is_major else PALETTE.grid_minor
            w = 0.9 if is_major else 0.5
            op = 0.85 if is_major else 0.55
            fig.add_trace(_curve_trace(x_func(+v, n=n), color, w, opacity=op))
            fig.add_trace(_curve_trace(x_func(-v, n=n), color, w, opacity=op))


def _add_helper_circles(fig: go.Figure, settings) -> None:
    if settings.show_vswr:
        first = True
        for vswr in default_vswr_values(settings.curve_detail_2d):
            radius = (vswr - 1) / (vswr + 1)
            rl = -20 * np.log10(radius) if radius > 0 else np.inf
            rl_txt = "∞" if not np.isfinite(rl) else f"{rl:.1f} dB"
            hover = (
                f"<b>VSWR = {vswr:.2f}</b><br>"
                f"|Γ| = {radius:.4f}<br>"
                f"Geri dönüş kaybı = {rl_txt}"
                f"<extra></extra>"
            )
            t = go.Scatter(
                x=radius * np.cos(np.linspace(0, 2 * np.pi, 400)),
                y=radius * np.sin(np.linspace(0, 2 * np.pi, 400)),
                mode="lines", line=dict(color=PALETTE.vswr, width=1.0, dash="dash"),
                opacity=0.65,
                name="VSWR çemberleri", legendgroup="vswr",
                showlegend=first,
                hovertemplate=hover,
            )
            fig.add_trace(t)
            first = False

    if settings.show_return_loss:
        first = True
        for rl in [3, 6, 10, 15, 20, 30]:
            radius = 10 ** (-rl / 20)
            vswr_val = (1 + radius) / (1 - radius)
            hover = (
                f"<b>Geri dönüş kaybı = {rl:.0f} dB</b><br>"
                f"|Γ| = {radius:.4f}<br>"
                f"VSWR = {vswr_val:.2f}"
                f"<extra></extra>"
            )
            t = go.Scatter(
                x=radius * np.cos(np.linspace(0, 2 * np.pi, 400)),
                y=radius * np.sin(np.linspace(0, 2 * np.pi, 400)),
                mode="lines", line=dict(color=PALETTE.return_loss, width=0.9, dash="dot"),
                opacity=0.6,
                name="Geri dönüş kaybı", legendgroup="rl",
                showlegend=first,
                hovertemplate=hover,
            )
            fig.add_trace(t)
            first = False


def _add_frame(fig: go.Figure) -> None:
    t = np.linspace(0, 2 * np.pi, 800)
    fig.add_trace(go.Scatter(
        x=np.cos(t), y=np.sin(t), mode="lines",
        line=dict(color=PALETTE.unit_circle, width=2.2),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[-1, 1], y=[0, 0], mode="lines",
        line=dict(color=PALETTE.real_axis, width=1.1),
        opacity=0.8, hoverinfo="skip", showlegend=False,
    ))


def _add_region_labels(fig: go.Figure, settings) -> None:
    admittance = settings.chart_mode_2d == "admittance"
    top = "İndüktif (+jX)" if not admittance else "İndüktif (−jB)"
    bot = "Kapasitif (−jX)" if not admittance else "Kapasitif (+jB)"
    right = "Açık devre" if not admittance else "Kısa devre"
    left = "Kısa devre" if not admittance else "Açık devre"
    for text, x, y, color in [
        (top, 0.0, 1.1, PALETTE.inductive),
        (bot, 0.0, -1.1, PALETTE.capacitive),
        (right, 1.12, 0.0, PALETTE.muted),
        (left, -1.12, 0.0, PALETTE.muted),
    ]:
        fig.add_annotation(
            x=x, y=y, text=text, showarrow=False,
            font=dict(size=10.5, color=color, family=FONT_FAMILY),
        )


# ----------------------------------------------------------------------
# Dinamik noktalar
# ----------------------------------------------------------------------
def _add_key_point(fig: go.Figure, gamma: complex, z0: float, *,
                   color: str, name: str, symbol: str, size: int,
                   text_pos: str) -> None:
    fig.add_trace(go.Scatter(
        x=[gamma.real], y=[gamma.imag],
        mode="markers+text",
        marker=dict(color=color, size=size, symbol=symbol,
                    line=dict(color="white", width=1.5)),
        text=[name], textposition=text_pos,
        textfont=dict(size=11, color=color, family=FONT_FAMILY),
        name=name,
        customdata=[_point_hover(gamma, z0)],
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
    ))
    # merkeze referans çizgisi
    fig.add_trace(go.Scatter(
        x=[0, gamma.real], y=[0, gamma.imag], mode="lines",
        line=dict(color=color, width=1, dash="dot"),
        opacity=0.55, hoverinfo="skip", showlegend=False,
    ))


def _add_trajectory(fig: go.Figure, output: AnalyzerOutput) -> None:
    """Hat boyunca yükten ilerlenen noktaya çizilen yörünge (yön oklu)."""
    line = output.line
    if line is None:
        return

    ts = np.linspace(0, line.length_lambda, 240)
    path = np.array(
        [rotate_gamma(line.gamma_start, t, line.direction) for t in ts],
        dtype=complex,
    )
    fig.add_trace(go.Scatter(
        x=np.real(path), y=np.imag(path), mode="lines",
        line=dict(color=PALETTE.traveled, width=2.4),
        name="Hat yörüngesi", hoverinfo="skip",
    ))

    # Yön okları: yörünge boyunca birkaç ara ok
    for frac in (0.25, 0.55, 0.85):
        i = int(frac * (len(path) - 1))
        if i < 1:
            continue
        p0, p1 = path[i - 1], path[i]
        fig.add_annotation(
            x=p1.real, y=p1.imag, ax=p0.real, ay=p0.imag,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowsize=1.4,
            arrowwidth=1.6, arrowcolor=PALETTE.traveled,
        )


def _add_matching_points(fig: go.Figure, output: AnalyzerOutput, z0: float) -> None:
    solutions = output.matching_solutions
    if not solutions:
        return
    for i, sol in enumerate(solutions[:3]):
        if sol.gamma_at_stub is None:
            continue
        color = PALETTE.stub_cycle[i % len(PALETTE.stub_cycle)]
        fig.add_trace(go.Scatter(
            x=[sol.gamma_at_stub.real], y=[sol.gamma_at_stub.imag],
            mode="markers", marker=dict(color=color, size=11, symbol="diamond",
                                        line=dict(color="white", width=1.2)),
            name=f"Çözüm {i + 1}",
            customdata=[_point_hover(sol.gamma_at_stub, z0)],
            hovertemplate=(f"<b>Çözüm {i + 1}: {sol.method}</b><br>"
                           "%{customdata}<extra></extra>"),
        ))

    # Uyum merkezi
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(color=PALETTE.matched, size=16, symbol="star",
                    line=dict(color="#9C7A00", width=1)),
        name="Uyum (Z₀)",
        hovertemplate="<b>Uyum noktası</b><br>Γ = 0  |  VSWR = 1<extra></extra>",
    ))


# ----------------------------------------------------------------------
# Genel kurucu
# ----------------------------------------------------------------------
def build_base_smith_2d(settings, title: str | None = None) -> go.Figure:
    """Yalnızca ızgara + yardımcı çemberler + çerçeve + bölge etiketlerinden
    oluşan TEMEL Smith figürünü kurar. Hem ana 2B diyagram hem de kademeli
    devre yörüngesi bunu paylaşır (ızgara kodu tek yerde — anti-spaghetti).

    title verilirse layout uygulanır; verilmezse çağıran kendi layout'unu kurar.
    """
    fig = go.Figure()
    _add_grid(fig, settings)
    _add_helper_circles(fig, settings)
    _add_frame(fig)
    if settings.show_labels:
        _add_region_labels(fig, settings)
    if title is not None:
        fig.update_layout(**base_2d_layout(title))
    return fig


def build_smith_2d(output: AnalyzerOutput | None, settings) -> go.Figure:
    """2B Smith diyagramı figürünü kurar."""
    fig = build_base_smith_2d(settings)

    if output is not None:
        z0 = output.basic.z0
        _add_key_point(fig, output.basic.gamma, z0, color=PALETTE.load,
                       name="Yük", symbol="circle", size=13, text_pos="top center")

        if output.line is not None:
            if settings.show_line_path:
                _add_trajectory(fig, output)
            _add_key_point(fig, output.line.gamma_end, z0, color=PALETTE.traveled,
                           name="İlerlenen nokta", symbol="square", size=12,
                           text_pos="bottom center")

        if settings.show_matching_points:
            _add_matching_points(fig, output, z0)

    mode = "Admitans (Y)" if settings.chart_mode_2d == "admittance" else "Empedans (Z)"
    fig.update_layout(**base_2d_layout(f"2B Smith Diyagramı — {mode} Görünümü"))
    return fig
