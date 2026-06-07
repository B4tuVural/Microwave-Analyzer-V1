"""
ui/unit_tools.py
================
Birim döngüsü için Streamlit düğmesi. Tıklandıkça birimi sıradaki değere
geçirir (session_state'te tutar) ve geçerli birimi döndürür.
"""

from __future__ import annotations

import streamlit as st


def current_unit(key: str, units: tuple[str, ...]) -> str:
    return units[st.session_state.get(key, 0) % len(units)]


def unit_button(key: str, units: tuple[str, ...], prefix: str) -> str:
    """Birim döngü düğmesi çizer; geçerli birimi döndürür.

    Tıklayınca bir sonraki birime geçer (kademeli). Etiket: '<prefix>: <birim> ⟳'.
    """
    unit = current_unit(key, units)
    if st.button(f"{prefix}: {unit}  ⟳", key=f"ub_{key}",
                 help="Birimi değiştirmek için tıklayın", width="stretch"):
        st.session_state[key] = (st.session_state.get(key, 0) + 1) % len(units)
        st.rerun()
    return unit
