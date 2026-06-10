"""
viz/cascade_smith.py
====================
Kademeli devrenin Smith yörüngesi. smith_2d.build_base_smith_2d ile ızgarayı
paylaşır (ızgara kodu tek yerde — anti-spaghetti). Yalnızca yörünge çizgisini ve
düğüm noktalarını ekler.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.smith_2d import build_base_smith_2d
from viz.theme import PALETTE, base_2d_layout


def _node_hover(node, z0_ref: float) -> str:
    z = node.z
    g = node.gamma
    return (
        f"<b>{node.label}</b><br>"
        f"Z = {z.real:.2f} {z.imag:+.2f}j Ω<br>"
        f"Γ = {g.real:.4f} {g.imag:+.4f}j<br>"
        f"|Γ| = {abs(g):.4f}"
        f"<extra></extra>"
    )


def build_cascade_smith(result, settings) -> go.Figure:
    """Kademeli devre yörüngesini referans Z0'a göre Smith üzerinde çizer."""
    fig = build_base_smith_2d(settings)

    traj = result.trajectory
    if len(traj) >= 2:
        fig.add_trace(go.Scatter(
            x=traj.real, y=traj.imag, mode="lines",
            line=dict(color=PALETTE.traveled, width=3),
            name="Kademeli yörünge", hoverinfo="skip",
        ))

    n_last = len(result.nodes) - 1
    for i, node in enumerate(result.nodes):
        if i == 0:
            color, sym, size, name, tpos = (PALETTE.load, "circle", 13,
                                            "Yük", "top center")
        elif i == n_last:
            color, sym, size, name, tpos = (PALETTE.matched, "star", 16,
                                            "Giriş (Z_in)", "top center")
        else:
            color, sym, size, name, tpos = (PALETTE.stub_cycle[(i - 1) % 4],
                                            "diamond", 11, node.label,
                                            "bottom center")
        fig.add_trace(go.Scatter(
            x=[node.gamma.real], y=[node.gamma.imag],
            mode="markers+text", marker=dict(color=color, size=size, symbol=sym,
                                             line=dict(color="white", width=1.2)),
            text=[node.label], textposition=tpos,
            textfont=dict(size=10, color=color),
            name=name, hovertemplate=_node_hover(node, result.z0_ref),
        ))

    fig.update_layout(**base_2d_layout("2B Smith — Kademeli Devre Yörüngesi"))
    return fig
