"""
viz/smith_3d.py
===============
Okunabilir 3B Smith diyagramı (Plotly, yarım küre projeksiyonu).

Eski sürümdeki sorunlar ve çözümleri
------------------------------------
* "Noktalar ne ifade ediyor?"  -> Her nokta metin etiketi + hover bilgisi taşır
  (Yük / İlerlenen / Uyum) ve açık bir gösterge (legend) vardır.
* "Yük nereden nereye ilerledi?" -> Gerçek Γ dönüşü boyunca kalın renkli bir
  yörünge çizgisi + yön gösteren koni okları + 'Başlangıç/Bitiş' işaretleri.
* "Anlaşılabilirlik kötü" -> Yarı saydam yarım küre yüzeyi derinlik hissi verir;
  meridyen/paralel teli sade tutulur; eksenler etiketlenir.

Γ -> yarım küre dönüşümü core.smith_curves.gamma_to_hemisphere ile yapılır:
    x = Re(Γ), y = Im(Γ), z = sqrt(1 - |Γ|²)
Yani diyagramın merkezi (uyum) kürenin tepesidir; kenar (|Γ|=1) ekvatordur.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from core.models import AnalyzerOutput
from core.rf_math import gamma_to_z, vswr_from_gamma
from core.smith_curves import (
    gamma_to_hemisphere, constant_resistance_curve, constant_reactance_curve,
    gamma_circle, default_resistance_values, default_reactance_values,
    default_vswr_values,
)
from core.transmission_line import rotate_gamma
from viz.theme import PALETTE, FONT_FAMILY, base_3d_layout


def _hemisphere_xyz(gamma: np.ndarray):
    x, y, z = gamma_to_hemisphere(gamma)
    valid = ~np.isnan(z)
    return x[valid], y[valid], z[valid]


def _point_hover(gamma: complex, z0: float, title: str) -> str:
    z = gamma_to_z(gamma)
    vswr = vswr_from_gamma(gamma)
    vswr_txt = "∞" if not np.isfinite(vswr) else f"{vswr:.3f}"
    return (
        f"<b>{title}</b><br>"
        f"Γ = {gamma.real:.4f} {gamma.imag:+.4f}j<br>"
        f"Z = {z.real * z0:.2f} {z.imag * z0:+.2f}j Ω<br>"
        f"VSWR = {vswr_txt}<extra></extra>"
    )


def _curve_n(detail: str) -> int:
    return {"low": 1600, "high": 2600}.get(detail, 2000)


# ----------------------------------------------------------------------
# Sahne parçaları
# ----------------------------------------------------------------------
def _add_hemisphere_surface(fig: go.Figure) -> None:
    """Yarı saydam yarım küre yüzeyi (derinlik algısı için)."""
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi / 2, 30)
    uu, vv = np.meshgrid(u, v)
    x = np.cos(uu) * np.sin(vv)
    y = np.sin(uu) * np.sin(vv)
    z = np.cos(vv)
    fig.add_trace(go.Surface(
        x=x, y=y, z=z, showscale=False, opacity=0.30,
        colorscale=[[0, PALETTE.hemisphere_lo], [1, PALETTE.hemisphere_hi]],
        hoverinfo="skip", contours=dict(
            x=dict(highlight=False), y=dict(highlight=False),
            z=dict(highlight=False)),
        lighting=dict(ambient=0.85, diffuse=0.4), showlegend=False,
    ))


def _add_wireframe(fig: go.Figure, settings) -> None:
    if not settings.show_back_grid:
        return
    detail = {"low": (16, 6), "high": (32, 12)}.get(settings.sphere_detail, (24, 9))
    n_mer, n_par = detail

    for phi in np.linspace(0, 2 * np.pi, n_mer, endpoint=False):
        th = np.linspace(0, np.pi / 2, 60)
        fig.add_trace(go.Scatter3d(
            x=np.cos(phi) * np.sin(th), y=np.sin(phi) * np.sin(th), z=np.cos(th),
            mode="lines", line=dict(color=PALETTE.meridian, width=1),
            opacity=0.35, hoverinfo="skip", showlegend=False,
        ))
    for th in np.linspace(0.1, np.pi / 2 - 0.05, n_par):
        ph = np.linspace(0, 2 * np.pi, 80)
        fig.add_trace(go.Scatter3d(
            x=np.cos(ph) * np.sin(th), y=np.sin(ph) * np.sin(th),
            z=np.full_like(ph, np.cos(th)),
            mode="lines", line=dict(color=PALETTE.parallel, width=1),
            opacity=0.3, hoverinfo="skip", showlegend=False,
        ))


def _add_equator_and_axes(fig: go.Figure) -> None:
    ph = np.linspace(0, 2 * np.pi, 200)
    fig.add_trace(go.Scatter3d(
        x=np.cos(ph), y=np.sin(ph), z=np.zeros_like(ph),
        mode="lines", line=dict(color=PALETTE.unit_circle, width=4),
        name="Ekvator (|Γ|=1)", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[-1.1, 1.1], y=[0, 0], z=[0, 0], mode="lines",
        line=dict(color=PALETTE.real_axis, width=3),
        hoverinfo="skip", showlegend=False,
    ))


def _add_smith_curves(fig: go.Figure, settings) -> None:
    n = _curve_n(settings.curve_detail_3d)
    major = {0.1, 0.2, 0.5, 1.0, 2.0, 5.0}

    for r in default_resistance_values(settings.curve_detail_3d):
        x, y, z = _hemisphere_xyz(constant_resistance_curve(r, n=n))
        if len(x) < 2:
            continue
        is_major = r in major
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="lines",
            line=dict(color=PALETTE.curve_r_3d, width=2.4 if is_major else 1.1),
            opacity=0.9 if is_major else 0.4, hoverinfo="skip", showlegend=False,
        ))
    for xv in default_reactance_values(settings.curve_detail_3d):
        for sign in (+1, -1):
            x, y, z = _hemisphere_xyz(constant_reactance_curve(sign * xv, n=n))
            if len(x) < 2:
                continue
            is_major = xv in major
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z, mode="lines",
                line=dict(color=PALETTE.curve_x_3d, width=2.0 if is_major else 1.0),
                opacity=0.85 if is_major else 0.35, hoverinfo="skip",
                showlegend=False,
            ))

    if settings.show_vswr_3d:
        first = True
        for vswr in default_vswr_values(settings.curve_detail_3d):
            radius = (vswr - 1) / (vswr + 1)
            x, y, z = _hemisphere_xyz(gamma_circle(radius, n=800))
            if len(x) < 2:
                continue
            rl = -20 * np.log10(radius) if radius > 0 else np.inf
            rl_txt = "∞" if not np.isfinite(rl) else f"{rl:.1f} dB"
            hover = (
                f"<b>VSWR = {vswr:.2f}</b><br>"
                f"|Γ| = {radius:.4f}<br>"
                f"Geri dönüş kaybı = {rl_txt}"
                f"<extra></extra>"
            )
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z, mode="lines",
                line=dict(color=PALETTE.vswr, width=1.8),
                opacity=0.65,
                name="VSWR çemberleri", legendgroup="vswr3d",
                showlegend=first,
                hovertemplate=hover,
            ))
            first = False


def _marker3d(fig, gamma, *, color, name, size, z0):
    x, y, z = _hemisphere_xyz(np.array([gamma]))
    if len(x) == 0:
        return
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode="markers+text",
        marker=dict(color=color, size=size, line=dict(color="white", width=1)),
        text=[name], textposition="top center",
        textfont=dict(size=12, color=color, family=FONT_FAMILY),
        name=name, hovertemplate=_point_hover(gamma, z0, name),
    ))
    # tepe noktasına (uyum) referans için dikine ince çizgi
    fig.add_trace(go.Scatter3d(
        x=[x[0], x[0]], y=[y[0], y[0]], z=[0, z[0]], mode="lines",
        line=dict(color=color, width=2, dash="dot"),
        opacity=0.5, hoverinfo="skip", showlegend=False,
    ))


def _add_trajectory(fig: go.Figure, output: AnalyzerOutput) -> None:
    line = output.line
    if line is None:
        return
    ts = np.linspace(0, line.length_lambda, 160)
    path = np.array(
        [rotate_gamma(line.gamma_start, t, line.direction) for t in ts],
        dtype=complex,
    )
    x, y, z = _hemisphere_xyz(path)
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z, mode="lines",
        line=dict(color=PALETTE.traveled, width=6),
        name="Hat yörüngesi", hoverinfo="skip",
    ))
    # İlerleme yönünü gösteren kademeli noktalar (açık→koyu = yük→ilerlenen).
    # Cone yerine bu kullanılır; sağlam ve okunabilir.
    if len(x) > 8:
        step = max(1, (len(x) - 1) // 7)
        idx = list(range(0, len(x), step))
        progress = [i / (len(x) - 1) for i in idx]
        fig.add_trace(go.Scatter3d(
            x=x[idx], y=y[idx], z=z[idx], mode="markers",
            marker=dict(size=4, color=progress,
                        colorscale=[[0, "#7A3B5C"], [1, PALETTE.traveled]],
                        showscale=False),
            name="İlerleme yönü", hoverinfo="skip",
        ))


def _add_matching_points(fig: go.Figure, output: AnalyzerOutput, z0: float) -> None:
    for i, sol in enumerate(output.matching_solutions[:3]):
        if sol.gamma_at_stub is None:
            continue
        color = PALETTE.stub_cycle[i % len(PALETTE.stub_cycle)]
        x, y, z = _hemisphere_xyz(np.array([sol.gamma_at_stub]))
        if len(x) == 0:
            continue
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode="markers",
            marker=dict(color=color, size=6, symbol="diamond"),
            name=f"Çözüm {i + 1}",
            hovertemplate=_point_hover(sol.gamma_at_stub, z0, f"Çözüm {i + 1}: {sol.method}"),
        ))


# ----------------------------------------------------------------------
# Genel kurucu
# ----------------------------------------------------------------------
def build_smith_3d(output: AnalyzerOutput | None, settings) -> go.Figure:
    fig = go.Figure()

    _add_hemisphere_surface(fig)
    _add_wireframe(fig, settings)
    _add_equator_and_axes(fig)
    _add_smith_curves(fig, settings)

    # Tepe (uyum) noktası daima görünür ve açıklanır
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[1], mode="markers+text",
        marker=dict(color=PALETTE.matched, size=7, symbol="diamond",
                    line=dict(color="#9C7A00", width=1)),
        text=["Uyum (Z₀)"], textposition="top center",
        textfont=dict(size=12, color="#9C7A00", family=FONT_FAMILY),
        name="Uyum (tepe)",
        hovertemplate="<b>Uyum noktası</b><br>Γ = 0  |  VSWR = 1<extra></extra>",
    ))

    if output is not None:
        z0 = output.basic.z0
        if output.line is not None and settings.show_line_path_3d:
            _add_trajectory(fig, output)

        _marker3d(fig, output.basic.gamma, color=PALETTE.load,
                  name="Yük", size=9, z0=z0)

        if output.line is not None:
            _marker3d(fig, output.line.gamma_end, color=PALETTE.traveled,
                      name="İlerlenen nokta", size=8, z0=z0)

        if settings.show_matching_points_3d:
            _add_matching_points(fig, output, z0)

    fig.update_layout(**base_3d_layout(
        "3B Smith Diyagramı — Yarım Küre Projeksiyonu"))
    return fig
