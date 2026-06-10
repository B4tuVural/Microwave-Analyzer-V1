"""
ui/cascade_page.py
==================
🧩 Devre Çözücü sekmesi.

Kullanıcı, farklı εr ve Z₀ değerlerinde **iletim hatları** ile **seri/paralel
stub** ekleyerek kademeli bir devre kurar. Yapı doğrudan yükten başlar (zorunlu
bir yük hattı yoktur); aradaki mesafeler (d, l) iletim hattı elemanlarıyla
verilir, stub'lar düğümlere bağlanır — tıpkı final sorusundaki kaskat yapı gibi.

Uzunluklar λ / m / cm / mm cinsinden girilebilir. Sayfa devrenin özelliklerini,
Smith yörüngesini ve şemasını gösterir; gömülü sekmede giriş empedansı için stub
eşleme çözümleri sunulur (render_matching_solutions yeniden kullanılır).

Tasarım: durum session_state'te ham (birimli) dict listesi olarak tutulur;
çözüm services.cascade (saf motor) ile yapılır; çizim viz/ katmanına devredilir.
st.form KULLANILMAZ — sayı girişlerinde "Press Enter to submit form" uyarısı
çıkmaz ve alanlar türe göre dinamik gösterilir.
"""

from __future__ import annotations

import streamlit as st

from core.models import LoadData
from core.units import frequency_to_hz, C0
from services.cascade import (solve_cascade, CascadeElement, KIND_LABELS,
                              KIND_LINE, KIND_SERIES, KIND_SHUNT)
from services.analyzer import SmithAnalyzer
from viz.cascade_smith import build_cascade_smith
from viz.cascade_circuit import build_cascade_circuit
from ui.circuit_page import render_matching_solutions, _PLOTLY_CONFIG
from unit_format import fmt_ohm, to_electrical_lambda, CASCADE_LENGTH_UNITS

_STATE = "cascade_elements_v2"
_KIND_FROM_LABEL = {v: k for k, v in KIND_LABELS.items()}
_KIND_ICON = {KIND_LINE: "▬", KIND_SERIES: "⊣", KIND_SHUNT: "⊥"}


# ----------------------------------------------------------------------
# Eleman kurucu (form YOK → dinamik alanlar + temiz görünüm)
# ----------------------------------------------------------------------
def _element_builder() -> None:
    st.markdown("##### ➕ Eleman ekle")
    st.caption("Elemanlar **yükten kaynağa** doğru eklenir (ilk eklenen yüke en "
               "yakın). İletim hatları aradaki **d / l mesafelerini** oluşturur; "
               "stub'lar bulundukları düğüme bağlanır.")

    kind_label = st.selectbox("Tür", list(KIND_LABELS.values()), key="cas_b_kind")
    kind = _KIND_FROM_LABEL[kind_label]
    is_stub = kind != KIND_LINE

    c1, c2, c3 = st.columns([1, 1, 1.6])
    z0 = c1.number_input("Z₀ (Ω)", value=50.0, min_value=0.1, step=1.0, key="cas_b_z0")
    eps = c2.number_input("εr", value=1.0, min_value=1.0, step=0.1, key="cas_b_eps")
    len_label = "ℓ (stub boyu)" if is_stub else "Hat uzunluğu (d, l)"
    lcol1, lcol2 = c3.columns([2, 1])
    len_val = lcol1.number_input(len_label, value=0.125 if is_stub else 0.10,
                                 min_value=0.0, step=0.01, key="cas_b_len")
    len_unit = lcol2.selectbox("Birim", CASCADE_LENGTH_UNITS, index=0,
                               key="cas_b_unit", label_visibility="collapsed")

    term = "open"
    if is_stub:
        term_label = st.radio("Stub ucu", ["Açık", "Kısa"], horizontal=True,
                              key="cas_b_term")
        term = "open" if term_label == "Açık" else "short"

    if st.button("➕ Ekle", width="stretch", type="primary", key="cas_b_add"):
        st.session_state.setdefault(_STATE, []).append({
            "kind": kind, "z0": z0, "epsilon_r": eps,
            "len_value": len_val, "len_unit": len_unit, "termination": term,
        })
        st.rerun()


def _element_list() -> None:
    elements = st.session_state.get(_STATE, [])
    st.markdown("##### 📃 Eleman zinciri  ·  yük → kaynak")
    if not elements:
        st.info("Henüz eleman yok. Yukarıdan ekleyin.")
        return

    for i, e in enumerate(elements):
        with st.container(border=True):
            badge, body, action = st.columns([0.6, 6, 1.1])
            badge.markdown(
                f"<div style='font-size:1.5rem;text-align:center'>"
                f"{_KIND_ICON[e['kind']]}</div>"
                f"<div style='text-align:center;color:#8b95a7'>#{i + 1}</div>",
                unsafe_allow_html=True)

            length = f"{e['len_value']:g} {e['len_unit']}"
            if e["kind"] == KIND_LINE:
                detail = f"uzunluk = {length}"
            else:
                uc = "açık" if e["termination"] == "open" else "kısa"
                detail = f"ℓ = {length} · uç: {uc}"
            body.markdown(
                f"**{KIND_LABELS[e['kind']]}**  \n"
                f"<span style='color:#8b95a7'>Z₀ = {e['z0']:.0f} Ω · "
                f"εr = {e['epsilon_r']:g} · {detail}</span>",
                unsafe_allow_html=True)

            if action.button("🗑️ Sil", key=f"cas_rm_{i}", width="stretch"):
                elements.pop(i)
                st.rerun()

    if st.button("Tümünü temizle", key="cas_clear"):
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
        is_line = e.kind == KIND_LINE
        length_l = e.d_lambda if is_line else e.stub_len_lambda
        length_m = e.d_meter if is_line else e.stub_len_meter
        theta = e.theta_d_deg if is_line else e.theta_stub_deg
        stub = "—" if e.stub_reactance is None else fmt_ohm(e.stub_reactance.imag, "Ω")
        rows.append({
            "#": e.index, "Tür": KIND_LABELS[e.kind],
            "Z₀ (Ω)": f"{e.z0:.0f}", "εr": f"{e.epsilon_r:g}",
            "Uzunluk (λ)": f"{length_l:.4f}",
            "Uzunluk (mm)": f"{length_m * 1000:.2f}",
            "θ (°)": f"{theta:.1f}",
            "Uç": "—" if is_line else
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
        "ekleyerek kademeli bir devre kurun. Yapı doğrudan yükten başlar. "
        "Devrenin özellikleri ve Smith yörüngesi çizilir; gömülü sekmede giriş "
        "empedansı için stub eşleme çözümleri önerilir."
    )

    # --- Genel parametreler + yük + frekans --------------------------
    g1, g2, g3, g4 = st.columns([1, 1, 1, 1.4])
    z0_ref = g1.number_input("Referans $Z_0$ (Ω)", value=50.0, min_value=0.1,
                             step=1.0, key="cas_z0ref")
    rl = g2.number_input("Yük $R_L$ (Ω)", value=100.0, step=1.0, key="cas_rl")
    xl = g3.number_input("Yük $X_L$ (Ω)", value=0.0, step=1.0, key="cas_xl")
    fc1, fc2 = g4.columns([2, 1])
    f_val = fc1.number_input("Frekans", value=1.0, min_value=1e-6, step=0.1,
                             key="cas_fval")
    f_unit = fc2.selectbox("Birim", ["Hz", "kHz", "MHz", "GHz"], index=3,
                           key="cas_funit", label_visibility="collapsed")
    freq_hz = frequency_to_hz(f_val, f_unit)
    lambda0 = C0 / freq_hz

    st.divider()
    _element_builder()
    _element_list()
    st.divider()

    # --- eleman zincirini kur (yük hattı YOK) ------------------------
    elements: list[CascadeElement] = []
    for e in st.session_state.get(_STATE, []):
        elec = to_electrical_lambda(e["len_value"], e["len_unit"],
                                    e["epsilon_r"], lambda0)
        if e["kind"] == KIND_LINE:
            elements.append(CascadeElement(
                kind=KIND_LINE, z0=e["z0"], epsilon_r=e["epsilon_r"],
                d_lambda=elec, stub_len_lambda=0.0))
        else:
            elements.append(CascadeElement(
                kind=e["kind"], z0=e["z0"], epsilon_r=e["epsilon_r"],
                d_lambda=0.0, stub_len_lambda=elec, termination=e["termination"]))

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
            f"**{z0_ref:.0f} Ω**'a uydurulacak. Önerilen stub çözümleri:"
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
