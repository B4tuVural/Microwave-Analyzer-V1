"""
ui/settings.py
==============
Görünüm ayarları: ViewSettings veri modeli + ⚙️ ayar sayfası.

Tasarım (veri-güdümlü, IHS'deki ParamSpec kalıbıyla aynı ruhta)
---------------------------------------------------------------
* `ViewSettings`  : tüm görünüm bayrakları tek bir dondurulmuş veri modelinde.
                    viz/ katmanı yalnızca bu modeli okur (Streamlit'i bilmez).
* `_SPECS`        : her ayarın widget tanımı (tip, etiket, seçenekler). Yeni bir
                    ayar eklemek = listeye tek satır; sayfa otomatik genişler,
                    render kodu değişmez (Open/Closed).
* `render_settings_page()` : ⚙️ sekmesini çizer; değerleri session_state'e yazar.
* `read_settings()`        : session_state'ten ViewSettings üretir.

Kullanıcı isteği 6: ayarlar artık giriş/hesapla alanının altında DEĞİL; kendi
⚙️ sekmesinin altında yaşar.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import streamlit as st


# ----------------------------------------------------------------------
# Veri modeli
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ViewSettings:
    # 2B
    show_resistance: bool = True
    show_reactance: bool = True
    show_vswr: bool = True
    show_return_loss: bool = True
    show_labels: bool = True
    show_line_path: bool = True
    show_matching_points: bool = True
    curve_detail_2d: str = "high"
    chart_mode_2d: str = "impedance"
    # 3B
    sphere_detail: str = "high"        # sabit: uygulamadan değiştirilemez
    curve_detail_3d: str = "high"      # sabit: uygulamadan değiştirilemez
    show_back_grid: bool = True
    show_vswr_3d: bool = True
    show_line_path_3d: bool = True
    show_matching_points_3d: bool = True
    marker_size_3d: int = 14


# ----------------------------------------------------------------------
# Widget tanımları (veri-güdümlü)
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class _Spec:
    key: str
    label: str
    kind: str                      # "toggle" | "select"
    options: tuple = ()
    fmt: dict | None = None        # select için görünen ad eşlemesi


_2D_SPECS: tuple[_Spec, ...] = (
    _Spec("chart_mode_2d", "Diyagram modu", "select", ("impedance", "admittance"),
          {"impedance": "Empedans (Z)", "admittance": "Admitans (Y)"}),
    _Spec("show_resistance", "Sabit R / G eğrileri", "toggle"),
    _Spec("show_reactance", "Sabit X / B eğrileri", "toggle"),
    _Spec("show_vswr", "VSWR çemberleri", "toggle"),
    _Spec("show_return_loss", "Geri dönüş kaybı halkaları", "toggle"),
    _Spec("show_labels", "Bölge etiketleri", "toggle"),
    _Spec("show_line_path", "Hat yörüngesi", "toggle"),
    _Spec("show_matching_points", "Uygunlama noktaları", "toggle"),
)

_3D_SPECS: tuple[_Spec, ...] = (
    _Spec("marker_size_3d", "İşaretçi boyutu", "select", (10, 14, 18, 24)),
    _Spec("show_back_grid", "Arka yüzey teli", "toggle"),
    _Spec("show_vswr_3d", "VSWR halkaları", "toggle"),
    _Spec("show_line_path_3d", "Hat yörüngesi", "toggle"),
    _Spec("show_matching_points_3d", "Uygunlama noktaları", "toggle"),
)

_DEFAULTS = {f.name: f.default for f in fields(ViewSettings)}


def _widget_key(key: str) -> str:
    return f"set_{key}"


def _render_spec(spec: _Spec) -> None:
    wkey = _widget_key(spec.key)
    default = _DEFAULTS[spec.key]
    if spec.kind == "toggle":
        st.toggle(spec.label, value=st.session_state.get(wkey, default), key=wkey)
    else:
        opts = list(spec.options)
        current = st.session_state.get(wkey, default)
        index = opts.index(current) if current in opts else 0
        fmt = (lambda v: spec.fmt[v]) if spec.fmt else (lambda v: str(v))
        st.selectbox(spec.label, opts, index=index, key=wkey, format_func=fmt)


# ----------------------------------------------------------------------
# Genel API
# ----------------------------------------------------------------------
def render_settings_page() -> None:
    """⚙️ Ayarlar sekmesini çizer."""
    st.subheader("⚙️ Görünüm Ayarları")
    st.caption(
        "Diyagramların görünümünü buradan yönetin. Değişiklikler anında "
        "Analiz ve Devre Şeması sekmelerine yansır."
    )

    col_2d, col_3d = st.columns(2)
    with col_2d:
        st.markdown("#### 📐 2B Smith Diyagramı")
        for spec in _2D_SPECS:
            _render_spec(spec)
    with col_3d:
        st.markdown("#### 🌐 3B Smith Diyagramı")
        for spec in _3D_SPECS:
            _render_spec(spec)

    st.divider()
    if st.button("↺ Varsayılanlara dön", width="stretch"):
        for spec in (*_2D_SPECS, *_3D_SPECS):
            st.session_state.pop(_widget_key(spec.key), None)
        st.rerun()


def read_settings() -> ViewSettings:
    """session_state'ten geçerli ViewSettings'i üretir."""
    values = {
        name: st.session_state.get(_widget_key(name), default)
        for name, default in _DEFAULTS.items()
    }
    return ViewSettings(**values)
