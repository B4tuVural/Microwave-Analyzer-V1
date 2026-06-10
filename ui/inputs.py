"""
ui/inputs.py
============
Kenar çubuğundaki giriş formu ve analiz koşturma.

Girdiler kenar çubuğunda yaşar; böylece tüm sekmeler (Analiz, Devre Şeması)
aynı kalıcı girdileri paylaşır. Form yalnızca veri toplar ve doğrular; hesabı
çekirdek `SmithAnalyzer` yapar (UI hesaptan ayrıdır).
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from core.models import LoadData, AnalyzerOutput
from core.units import frequency_to_hz, meter_to_lambda, wavelength_from_frequency
from services.analyzer import SmithAnalyzer

# Yöntem adı -> çekirdek anahtarı (MatchingPanel.METHOD_MAP'in karşılığı)
MATCHING_METHODS: dict[str, str | None] = {
    "Sadece temel analiz": None,
    "Paralel kısa devre yan hat": "shunt_short",
    "Paralel açık devre yan hat": "shunt_open",
    "Seri kısa devre yan hat": "series_short",
    "Seri açık devre yan hat": "series_open",
    "Çeyrek dalga transformatör": "quarter_wave",
    "Otomatik uygunlama önerisi": "auto",
}

_DIRECTIONS = {"Yük → Kaynak": "load_to_source", "Kaynak → Yük": "source_to_load"}


@dataclass(frozen=True)
class AnalysisRequest:
    r_ohm: float
    x_ohm: float
    z0_ohm: float
    frequency_value: float
    frequency_unit: str
    velocity_factor: float
    length_value: float
    length_unit: str
    direction: str
    matching_method: str | None


# ----------------------------------------------------------------------
# Çekirdek çağrısı (önbellekli — saf girdilere bağlı)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _run(r, x, z0, freq_hz, vf, length_lambda, direction, method) -> AnalyzerOutput:
    load = LoadData(r_ohm=r, x_ohm=x, z0_ohm=z0,
                    frequency_hz=freq_hz, velocity_factor=vf)
    return SmithAnalyzer().analyze_all(
        load=load, length_lambda=length_lambda,
        direction=direction, matching_method=method,
    )


def _to_length_lambda(req: AnalysisRequest, freq_hz: float) -> float:
    if req.length_unit == "λ":
        return req.length_value
    wl = wavelength_from_frequency(freq_hz, req.velocity_factor)
    return meter_to_lambda(req.length_value, wl)


def compute(req: AnalysisRequest) -> tuple[AnalyzerOutput | None, str | None]:
    """İsteği çalıştırır; (çıktı, hata) döndürür."""
    try:
        if req.z0_ohm == 0:
            raise ValueError("Z₀ sıfır olamaz.")
        freq_hz = frequency_to_hz(req.frequency_value, req.frequency_unit)
        if freq_hz <= 0:
            raise ValueError("Frekans sıfırdan büyük olmalıdır.")
        if req.velocity_factor <= 0:
            raise ValueError("Faz hızı oranı sıfırdan büyük olmalıdır.")
        length_lambda = _to_length_lambda(req, freq_hz)
        out = _run(req.r_ohm, req.x_ohm, req.z0_ohm, freq_hz, req.velocity_factor,
                   length_lambda, req.direction, req.matching_method)
        return out, None
    except Exception as exc:  # kullanıcıya temiz mesaj
        return None, str(exc)


# ----------------------------------------------------------------------
# Kenar çubuğu formu
# ----------------------------------------------------------------------
def render_inputs() -> AnalysisRequest:
    with st.sidebar:
        st.header("📥 Giriş Değerleri")

        direction_label = st.selectbox("Bakış yönü", list(_DIRECTIONS), key="in_dir")
        is_load = _DIRECTIONS[direction_label] == "load_to_source"
        r_label = r"$R_L$ (Ω)" if is_load else r"$R_{in}$ (Ω)"
        x_label = r"$X_L$ (Ω)" if is_load else r"$X_{in}$ (Ω)"

        c1, c2 = st.columns(2)
        r = c1.number_input(r_label, value=100.0, step=1.0, key="in_r")
        x = c2.number_input(x_label, value=100.0, step=1.0, key="in_x")
        z0 = st.number_input(r"Karakteristik empedans $Z_0$ (Ω)",
                             value=50.0, min_value=0.0001, step=1.0, key="in_z0")

        st.markdown("**Frekans (Hz)**")
        fc1, fc2 = st.columns([1, 1])
        freq = fc1.number_input("Değer", value=10.0, min_value=0.0001,
                                step=0.1, key="in_freq", label_visibility="collapsed")
        freq_unit = fc2.selectbox("Birim", ["Hz", "kHz", "MHz", "GHz"], index=2,
                                  key="in_funit", label_visibility="collapsed")

        # Faz hızı tanımı: v/c oranı VEYA dielektrik εr (geçiş)
        vf_mode = st.radio("Faz hızı tanımı", ["v/c oranı", "Dielektrik εr"],
                           horizontal=True, key="in_vfmode")
        if vf_mode == "Dielektrik εr":
            eps_r = st.number_input("Dielektrik sabiti εr", value=2.25,
                                    min_value=1.0, step=0.05, key="in_epsr")
            vf = 1.0 / (eps_r ** 0.5)
            st.caption(f"v/c = 1/√εr = **{vf:.4f}**")
        else:
            vf = st.number_input("Faz hızı oranı v/c", value=0.6667,
                                 min_value=0.0001, max_value=1.0, step=0.01,
                                 key="in_vf")

        st.markdown("**Hat uzunluğu (m)**")
        lc1, lc2 = st.columns([2, 1])
        length = lc1.number_input("Uzunluk", value=0.125, step=0.001,
                                  format="%.4f", key="in_len",
                                  label_visibility="collapsed")
        length_unit = lc2.selectbox("Birim ", ["λ", "m"], key="in_lunit",
                                    label_visibility="collapsed")

        st.divider()
        method_label = st.selectbox("Uygunlama yöntemi", list(MATCHING_METHODS),
                                    index=len(MATCHING_METHODS) - 1, key="in_method")

    return AnalysisRequest(
        r_ohm=r, x_ohm=x, z0_ohm=z0,
        frequency_value=freq, frequency_unit=freq_unit, velocity_factor=vf,
        length_value=length, length_unit=length_unit,
        direction=_DIRECTIONS[direction_label],
        matching_method=MATCHING_METHODS[method_label],
    )
