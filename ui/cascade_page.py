"""
ui/cascade_page.py
==================
🧩 Devre Çözücü sekmesi.

Kullanıcı, farklı εr ve Z₀ değerlerinde iletim hatları, seri stub ve paralel
stub ekleyerek bir kademeli devre kurar. Sayfa:
  * Devrenin özelliklerini (Z_in, Γ, VSWR, geri dönüş kaybı) ve eleman tablosunu,
  * Smith diyagramı üzerinde sürekli yörüngeyi,
  * Kademeli devre şemasını
gösterir. Gömülü "Stub Eşleme Önerileri" alt-sekmesinde, oluşan giriş empedansını
(Z_in) referans Z₀'a uydurmak için stub çözümleri — Devre Şeması sayfasındaki
gibi — sunulur (render_matching_solutions yeniden kullanılır).

Mimari: durum session_state'te basit dict listesi olarak tutulur; çözüm
services.cascade (saf motor) ile yapılır; çizim viz/ katmanına devredilir.
"""

from __future__ import annotations

import streamlit as st

from core.models import LoadData
from core.units import frequency_to_hz
from services.cascade import (solve_cascade, CascadeElement, KIND_LABELS,
                              KIND_LINE, KIND_SERIES, KIND_SHUNT)
from services.analyzer import SmithAnalyzer
from viz.cascade_smith import build_cascade_smith
from viz.cascade_circuit import build_cascade_circuit
from ui.circuit_page import render_matching_solutions, _PLOTLY_CONFIG
from unit_format import fmt_ohm

_STATE = "cascade_elements"
_LEN_FACTOR = {"mm": 1e-3, "cm": 1e-2, "m": 1.0}
_KIND_FROM_LABEL = {v: k for k, v in KIND_LABELS.items()}


# ----------------------------------------------------------------------
# Eleman kurucu (durum: session_state listesi)
# ----------------------------------------------------------------------
def _element_builder() -> None:
    st.markdown("##### ➕ Eleman ekle")
    st.caption("Elemanlar **yükten kaynağa** doğru sırayla eklenir "
               "(ilk eklenen yüke en yakın).")

    with st.form("cascade_add", clear_on_submit=False):
        c1, c2, c3, c4, c5 = st.columns([1.4, 1, 1, 1.2, 1])
        kind_label = c1.selectbox("Tür", list(KIND_LABELS.values()))
        z0 = c2.number_input("Z₀ (Ω)", value=50.0, min_value=0.1, step=1.0)
        eps = c3.number_input("εr", value=1.0, min_value=1.0, step=0.1)
        lc1, lc2 = c4.columns([2, 1])
        length = lc1.number_input("Uzunluk", value=10.0, min_value=0.0, step=1.0)
        length_unit = lc2.selectbox("Birim", ["mm", "cm", "m"], index=0,
                                    label_visibility="collapsed")
        term_label = c5.selectbox("Uç", ["Açık", "Kısa"])

        if st.form_submit_button("Ekle", width="stretch"):
            st.session_state.setdefault(_STATE, []).append({
                "kind": _KIND_FROM_LABEL[kind_label],
                "z0": z0, "epsilon_r": eps,
                "length_m": length * _LEN_FACTOR[length_unit],
                "termination": "open" if term_label == "Açık" else "short",
            })
            st.rerun()


def _element_list() -> None:
    elements = st.session_state.get(_STATE, [])
    if not elements:
        st.info("Henüz eleman yok. Yukarıdan ekleyin.")
        return

    st.markdown("##### 📃 Eleman zinciri (yük → kaynak)")
    for i, e in enumerate(elements):
        col, btn = st.columns([6, 1])
        term = "" if e["kind"] == KIND_LINE else \
            f" · uç: {'açık' if e['termination'] == 'open' else 'kısa'}"
        col.markdown(
            f"**{i + 1}. {KIND_LABELS[e['kind']]}** — "
            f"Z₀ = {e['z0']:.0f} Ω · εr = {e['epsilon_r']:g} · "
            f"ℓ = {e['length_m'] * 1000:.2f} mm{term}"
        )
        if btn.button("Sil", key=f"cas_rm_{i}", width="stretch"):
            elements.pop(i)
            st.rerun()

    if st.button("🗑️ Tümünü temizle", key="cas_clear"):
        st.session_state[_STATE] = []
        st.rerun()


# ----------------------------------------------------------------------
# Özellikler ve eleman tablosu
# ----------------------------------------------------------------------
def _properties(result) -> None:
    z = result.z_in
    cols = st.columns(4)
    cols[0].metric("Giriş empedansı $Z_{in}$", f"{z.real:.2f} {z.imag:+.2f}j Ω")
    cols[1].metric("Yansıma |Γ|", f"{abs(result.gamma_in):.4f}")
    cols[2].metric("VSWR",
                   "∞" if result.vswr == float("inf") else f"{result.vswr:.3f}")
    cols[3].metric("Geri dönüş kaybı",
                   "∞" if result.return_loss_db == float("inf")
                   else f"{result.return_loss_db:.2f} dB")

    rows = []
    for e in result.elements:
        stub = "—"
        if e.stub_reactance is not None:
            stub = fmt_ohm(e.stub_reactance.imag, "Ω")
        rows.append({
            "#": e.index,
            "Tür": KIND_LABELS[e.kind],
            "Z₀ (Ω)": f"{e.z0:.0f}",
            "εr": f"{e.epsilon_r:g}",
            "ℓ (mm)": f"{e.length_m * 1000:.2f}",
            "θ (°)": f"{e.theta_deg:.1f}",
            "ℓ (λ)": f"{e.length_lambda:.4f}",
            "Uç": "—" if e.kind == KIND_LINE else
                  ("açık" if e.termination == "open" else "kısa"),
            "Stub X (Ω)": stub,
            "Z sonra (Ω)": f"{e.z_after.real:.1f}{e.z_after.imag:+.1f}j",
        })
    st.dataframe(rows, width="stretch", hide_index=True)


# ----------------------------------------------------------------------
# Sayfa
# ----------------------------------------------------------------------
def render_cascade_page(settings) -> None:
    st.subheader("🧩 Devre Çözücü (Kademeli Ağ)")
    st.caption(
        "Farklı εr ve Z₀ değerlerinde iletim hatları ile seri/paralel stub'lar "
        "ekleyerek kademeli bir devre kurun. Devrenin özellikleri ve Smith "
        "yörüngesi çizilir; gömülü sekmede giriş empedansı için stub eşleme "
        "çözümleri önerilir."
    )

    # Genel parametreler
    g1, g2, g3, g4 = st.columns([1, 1, 1, 1.3])
    z0_ref = g1.number_input("Referans $Z_0$ (Ω)", value=50.0, min_value=0.1,
                             step=1.0, key="cas_z0ref")
    rl = g2.number_input("Yük $R_L$ (Ω)", value=100.0, step=1.0, key="cas_rl")
    xl = g3.number_input("Yük $X_L$ (Ω)", value=0.0, step=1.0, key="cas_xl")
    fc1, fc2 = g4.columns([1, 1])
    f_val = fc1.number_input("Frekans", value=1.0, min_value=1e-6, step=0.1,
                             key="cas_fval")
    f_unit = fc2.selectbox("Birim", ["Hz", "kHz", "MHz", "GHz"], index=3,
                           key="cas_funit")
    freq_hz = frequency_to_hz(f_val, f_unit)

    st.divider()
    _element_builder()
    _element_list()
    st.divider()

    elements = [CascadeElement(**e) for e in st.session_state.get(_STATE, [])]
    try:
        result = solve_cascade(complex(rl, xl), z0_ref, freq_hz, elements)
    except Exception as exc:  # noqa: BLE001 — kullanıcıya nazik hata
        st.error(f"Çözüm hatası: {exc}")
        return

    devre_tab, esleme_tab = st.tabs(
        ["📐 Devre & Smith", "🎯 Stub Eşleme Önerileri"]
    )

    with devre_tab:
        _properties(result)
        st.plotly_chart(build_cascade_circuit(result), width="stretch",
                        config=_PLOTLY_CONFIG, key="cas_circuit")
        st.plotly_chart(build_cascade_smith(result, settings), width="stretch",
                        config=_PLOTLY_CONFIG, key="cas_smith")

    with esleme_tab:
        st.markdown(
            f"Kademeli devrenin giriş empedansı **$Z_{{in}}$ = "
            f"{result.z_in.real:.2f} {result.z_in.imag:+.2f}j Ω** referans "
            f"**{z0_ref:.0f} Ω**'a uydurulacak. Aşağıda önerilen stub çözümleri:"
        )
        if result.z_in.real <= 0:
            st.warning("Giriş empedansının reel kısmı ≤ 0; stub eşleme "
                       "uygulanamıyor. Eleman değerlerini gözden geçirin.")
            return
        match_load = LoadData(r_ohm=result.z_in.real, x_ohm=result.z_in.imag,
                              z0_ohm=z0_ref, frequency_hz=freq_hz,
                              velocity_factor=1.0)
        match_output = SmithAnalyzer().analyze_all(
            load=match_load, matching_method="auto")
        render_matching_solutions(match_output, key_prefix="cascade_match")
