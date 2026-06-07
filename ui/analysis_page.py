"""
ui/analysis_page.py
===================
📊 Analiz sekmesi: özet metrikler + 2B/3B Smith diyagramları + sayısal sonuçlar.

Bu modül yalnızca düzeni ve Streamlit bileşenlerini bilir; figürleri viz/
katmanından, sayıları ise AnalyzerOutput'tan alır.
"""

from __future__ import annotations

import streamlit as st

from core.models import AnalyzerOutput
from viz.smith_2d import build_smith_2d
from viz.smith_3d import build_smith_3d
from ui.settings import ViewSettings
from ui.format import fmt_complex, fmt_float

_PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d"],
}


def _metrics(basic) -> None:
    rl = basic.return_loss_db
    rl_txt = "∞" if rl == float("inf") else f"{rl:.2f} dB"
    cols = st.columns(5)
    cols[0].metric("Yansıma |Γ|", fmt_float(basic.gamma_mag))
    cols[1].metric("∠Γ", f"{basic.gamma_angle_deg:.1f}°")
    cols[2].metric("VSWR / DDO", fmt_float(basic.vswr, 3))
    cols[3].metric("Geri dönüş kaybı", rl_txt)
    cols[4].metric("Yük tipi", basic.load_type)


def _kv_rows(rows: list[tuple[str, str]]) -> None:
    """İki sütunlu (Büyüklük / Değer) liste.

    Markdown tablo hücrelerinde KaTeX ($...$) render edilmediği için tablo
    yerine st.columns + st.markdown kullanılır; böylece indisler ($Z_L$,
    $\\Gamma_L$ ...) düzgün alt-indis olarak görünür.
    """
    h1, h2 = st.columns([3, 2])
    h1.markdown("**Büyüklük**")
    h2.markdown("**Değer**")
    for label, value in rows:
        c1, c2 = st.columns([3, 2])
        c1.markdown(label)
        c2.markdown(value)


def _detailed_results(output: AnalyzerOutput) -> None:
    basic = output.basic
    with st.expander("📋 Temel analiz (sayısal)", expanded=False):
        _kv_rows([
            (r"Yük empedansı $Z_L$", f"{fmt_complex(basic.z_load, 2)} Ω"),
            (r"Karakteristik empedans $Z_0$", f"{basic.z0:.2f} Ω"),
            (r"Normalize empedans $z_L$", fmt_complex(basic.z_norm)),
            (r"Normalize admitans $y_L$", fmt_complex(basic.y_norm)),
            (r"Yansıma katsayısı $\Gamma_L$", fmt_complex(basic.gamma)),
            (r"Dalga boyu $\lambda$", f"{fmt_float(basic.wavelength_m, 6)} m"),
        ])

    if output.line is not None:
        line = output.line
        direction = ("Yükten kaynağa" if line.direction == "load_to_source"
                     else "Kaynaktan yüke")
        with st.expander("📏 Hat boyunca ilerleme", expanded=False):
            _kv_rows([
                ("İlerleme yönü", direction),
                ("Hat uzunluğu",
                 f"{fmt_float(line.length_lambda)} λ  =  {fmt_float(line.length_m, 6)} m"),
                ("Eşdeğer faz dönüşü", f"{fmt_float(line.electrical_angle_deg, 2)}°"),
                (r"Başlangıç $\Gamma$", fmt_complex(line.gamma_start)),
                (r"İlerlenen $\Gamma$", fmt_complex(line.gamma_end)),
                (r"İlerlenen normalize $z$", fmt_complex(line.z_end_norm)),
                (r"İlerlenen gerçek $Z$", f"{fmt_complex(line.z_end_ohm, 2)} Ω"),
            ])


def render_analysis_page(output: AnalyzerOutput | None, settings: ViewSettings) -> None:
    st.subheader("📊 Smith Diyagramı Analizi")

    if output is None:
        st.info("Soldaki **Giriş Değerleri** panelinden bir yük tanımlayın.")
        return

    _metrics(output.basic)
    st.divider()

    tab_2d, tab_3d = st.tabs(["📐 2B Smith", "🌐 3B Smith"])
    with tab_2d:
        st.plotly_chart(build_smith_2d(output, settings),
                        width="stretch", config=_PLOTLY_CONFIG)
        st.caption("İpucu: Tekerlekle yakınlaştır, sürükleyerek kaydır. Noktaların "
                   "üzerine gelince Z, Y, Γ ve VSWR değerleri görünür.")
    with tab_3d:
        st.plotly_chart(build_smith_3d(output, settings),
                        width="stretch", config=_PLOTLY_CONFIG)
        st.caption("Merkez (tepe) = uyum, kenar (ekvator) = |Γ|=1. Pembe yörünge "
                   "yükün hat boyunca nereye ilerlediğini gösterir.")

    st.divider()
    _detailed_results(output)
