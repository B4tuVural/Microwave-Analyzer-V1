"""
ui/circuit_page.py
==================
🔧 Devre Şeması sekmesi (Monte Carlo sayfası gibi ayrı bir sekme).

İçerik:
* Çözüm seçici (en iyiden en kötüye sıralı)
* Birim kontrolleri (d/ℓ uzunluk birimi, reaktans ohm birimi — tıklayınca kademeli)
* Seçilen çözümün devre şeması (viz.circuit)
* Adım adım çözüm (notlar; x_stub/b_stub LaTeX + ohm karşılığı)
* Tüm çözümlerin karşılaştırma tablosu (sütun birimleri tıklamayla değişir)
"""

from __future__ import annotations

import re

import streamlit as st

from core.models import AnalyzerOutput, MatchingSolution
from viz.circuit import build_circuit
from ui.format import fmt_float
from ui.unit_tools import unit_button
from unit_format import (LENGTH_UNITS, OHM_UNITS, fmt_length, fmt_ohm,
                         stub_reactance_ohm)

_PLOTLY_CONFIG = {"scrollZoom": True, "displaylogo": False,
                  "displayModeBar": "hover",
                  "modeBarButtonsToRemove": ["select2d", "lasso2d"]}


def _total_length(s: MatchingSolution) -> float:
    """Toplam fiziksel uzunluk (d + ℓ) — 'en iyi' ölçütü (kısa = iyi)."""
    return (s.d_lambda or 0.0) + (s.stub_length_lambda or 0.0)


# ----------------------------------------------------------------------
# Metrikler (#1: 'Gerekli stub reaktans değeri' + ohm; d/ℓ seçili birimde)
# ----------------------------------------------------------------------
def _solution_metrics(sol: MatchingSolution, wl: float, z0: float,
                      length_unit: str, ohm_unit: str) -> None:
    cols = st.columns(4)
    cols[0].metric("Yöntem", sol.stub_type)
    if sol.d_lambda is not None:
        cols[1].metric("d (yük→stub)", fmt_length(sol.d_lambda, wl, length_unit))
    if sol.stub_length_lambda is not None:
        cols[2].metric("ℓ (stub boyu)", fmt_length(sol.stub_length_lambda, wl, length_unit))
    if sol.required_stub_value is not None:
        if "çeyrek dalga" in sol.method.lower():
            cols[3].metric(r"Gerekli empedans ($Z_t$)",
                           fmt_ohm(sol.required_stub_value, ohm_unit),
                           help=f"Temel değer: {sol.required_stub_value:.4f} Ω")
        else:
            x_ohm = stub_reactance_ohm(sol.method, sol.required_stub_value, z0)
            cols[3].metric(r"Gerekli stub reaktans değeri ($X_{stub}$)",
                           fmt_ohm(x_ohm, ohm_unit),
                           help=f"Normalize değer: {sol.required_stub_value:.4f}")


# ----------------------------------------------------------------------
# Adım adım çözüm (#2: x_stub/b_stub LaTeX alt-indis + ohm karşılığı)
# ----------------------------------------------------------------------
def _latexify_note(note: str, sol: MatchingSolution, z0: float,
                   ohm_unit: str) -> str:
    s = note
    s = s.replace("reactance", "reaktans").replace("susceptance", "suseptans")
    s = s.replace("z(d)", "$z(d)$").replace("y(d)", "$y(d)$")
    s = s.replace("x_stub", "$x_{stub}$").replace("b_stub", "$b_{stub}$")
    # Stub değeri satırına gerçek reaktansı (Ω) ekle
    if ("$x_{stub}$=" in s or "$b_{stub}$=" in s):
        x_ohm = stub_reactance_ohm(sol.method, sol.required_stub_value, z0)
        if x_ohm is not None:
            s = s.rstrip().rstrip(".")
            s += f"  →  gerçek reaktans $X_{{stub}}$ = {fmt_ohm(x_ohm, ohm_unit)}."
    return s


# ----------------------------------------------------------------------
# Karşılaştırma tablosu (#5: sütun birimleri tıklamayla değişir)
# ----------------------------------------------------------------------
def _summary_table(solutions: list[MatchingSolution], wl: float) -> None:
    st.caption("Birim değiştirmek için aşağıdaki düğmeye tıklayın "
               "(λ → m → cm → mm → μm). d, ℓ ve Toplam birlikte değişir.")
    bcol, _ = st.columns([1, 3])
    with bcol:
        u = unit_button("u_tbl", LENGTH_UNITS, "Birim (d, ℓ, Toplam)")

    rows = []
    for i, s in enumerate(solutions, start=1):
        rows.append({
            "#": i,
            "Yöntem": s.method,
            f"d ({u})": fmt_length(s.d_lambda, wl, u),
            f"ℓ ({u})": fmt_length(s.stub_length_lambda, wl, u),
            f"Toplam ({u})": fmt_length(_total_length(s), wl, u),
        })
    st.dataframe(rows, width="stretch", hide_index=True)


# ----------------------------------------------------------------------
# Sayfa
# ----------------------------------------------------------------------
def render_circuit_page(output: AnalyzerOutput | None) -> None:
    st.subheader("🔧 Uygunlama Devre Şeması")

    if output is None:
        st.info("Soldaki **Giriş Değerleri** panelinden bir yük tanımlayın.")
        return

    wl = output.basic.wavelength_m
    z0 = output.basic.z0
    solutions = output.matching_solutions

    if not solutions:
        st.warning(
            "Seçilen yöntem için uygunlama çözümü bulunamadı. Aşağıda yalnızca "
            "temel iletim hattı gösteriliyor. (Çeyrek dalga transformatör yalnızca "
            "saf dirençli yüklerde doğrudan uygulanır.)"
        )
        st.plotly_chart(build_circuit(output, 0), width="stretch",
                        config=_PLOTLY_CONFIG)
        return

    labels = [f"Çözüm {i + 1} — {s.method}" for i, s in enumerate(solutions)]
    choice = st.radio("Görüntülenecek çözüm", labels, index=0,
                      horizontal=True, key="circuit_choice")
    index = labels.index(choice)
    sol = solutions[index]

    # Birim kontrolleri (devre şeması + metrikler için)
    cc1, cc2, _ = st.columns([1, 1, 2])
    with cc1:
        circ_len = unit_button("u_circ_len", LENGTH_UNITS, "Uzunluk (d, ℓ)")
    with cc2:
        circ_ohm = unit_button("u_circ_ohm", OHM_UNITS, "Reaktans / Z")

    _solution_metrics(sol, wl, z0, circ_len, circ_ohm)
    st.plotly_chart(build_circuit(output, index, circ_len, circ_ohm),
                    width="stretch", config=_PLOTLY_CONFIG)

    if sol.notes:
        st.markdown("#### 🧮 Adım Adım Çözüm")
        for n, note in enumerate(sol.notes, start=1):
            st.markdown(f"**{n}.** {_latexify_note(note, sol, z0, circ_ohm)}")

    st.divider()
    st.markdown("#### 📋 Tüm Çözümlerin Karşılaştırması")
    st.caption("En iyiden en kötüye sıralı (#1 = en kısa toplam fiziksel "
               "uzunluk d + ℓ, genelde tercih edilen). '#' sırası yukarıdaki "
               "'Çözüm N' seçicisiyle aynıdır.")
    _summary_table(solutions, wl)
