"""
app.py
======
Mikrodalga Smith Diyagramı Analizörü — Streamlit arayüzü.

Mimari (Separation of Concerns + SOLID)
---------------------------------------
* core/      : saf RF matematiği (değiştirilmedi — orijinal temiz çekirdek).
* services/  : SmithAnalyzer facade'ı (tek çağrıyla tüm analiz).
* viz/       : saf Plotly figür üreticileri (Streamlit'ten bağımsız, test edilebilir).
* ui/        : Streamlit katmanı (girdiler, ayarlar, sayfalar).
* app.py     : yalnızca orkestrasyon — kenar çubuğu girdileri + 3 sekme.

Sekmeler: 📊 Analiz · 🔧 Devre Şeması · ⚙️ Ayarlar
"""

from __future__ import annotations

import streamlit as st

from ui.inputs import render_inputs, compute
from ui.settings import render_settings_page, read_settings
from ui.analysis_page import render_analysis_page
from ui.circuit_page import render_circuit_page

_STYLE = """
<style>
/* Tema config.toml'dan gelir; burada yalnızca nötr ince ayarlar var. */
.block-container { padding-top: 2rem; }
[data-testid="stMetricValue"] { font-size: 1.25rem; }
</style>
"""


def main() -> None:
    st.set_page_config(
        page_title="Smith Diyagramı Analizörü",
        page_icon="📡", layout="wide",
    )
    st.markdown(_STYLE, unsafe_allow_html=True)

    st.title("📡 Mikrodalga Smith Diyagramı Analizörü")
    st.caption(
        "İletim hattı analizi, empedans uygunlama ve interaktif 2B/3B Smith "
        "diyagramları. Girdileri soldan, görünüm ayarlarını ⚙️ sekmesinden yönetin."
    )

    # Girdiler kenar çubuğunda (tüm sekmeler paylaşır)
    request = render_inputs()
    output, error = compute(request)
    settings = read_settings()

    if error:
        st.error(f"Giriş hatası: {error}")

    analysis_tab, circuit_tab, settings_tab = st.tabs(
        ["📊 Analiz", "🔧 Devre Şeması", "⚙️ Ayarlar"]
    )
    with analysis_tab:
        render_analysis_page(output, settings)
    with circuit_tab:
        render_circuit_page(output)
    with settings_tab:
        render_settings_page()


if __name__ == "__main__":
    main()
