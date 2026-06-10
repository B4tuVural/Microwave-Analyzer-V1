"""
unit_format.py
==============
Saf (Streamlit'siz) birim dönüştürme ve biçimlendirme yardımcıları.

Hem viz/ (figür etiketleri) hem ui/ (tablo, metrik) tarafından kullanılır.
Streamlit'e bağımlılığı yoktur; bu yüzden import döngüsü oluşturmaz ve tek
başına test edilebilir.

Uzunluk birim döngüsü : λ → m → cm → mm → μm  (tıklamayla kademeli; en küçük μm)
Direnç/reaktans döngüsü: Ω → mΩ  (en küçük mΩ)
"""

from __future__ import annotations

import math

LENGTH_UNITS: tuple[str, ...] = ("λ", "m", "cm", "mm", "μm")
OHM_UNITS: tuple[str, ...] = ("Ω", "mΩ")

# 1 metre kaç birim eder (λ hariç)
_LEN_TO = {"m": 1.0, "cm": 1e2, "mm": 1e3, "μm": 1e6}
# 1 ohm kaç birim eder
_OHM_TO = {"Ω": 1.0, "mΩ": 1e3}


def fmt_length(value_lambda: float | None, wavelength_m: float | None,
               unit: str) -> str:
    """λ cinsinden bir uzunluğu seçilen birimde biçimlendirir."""
    if value_lambda is None:
        return "—"
    if unit == "λ":
        return f"{value_lambda:.4f} λ"
    meters = value_lambda * (wavelength_m or 0.0)
    return f"{meters * _LEN_TO[unit]:.4g} {unit}"


def fmt_ohm(value_ohm: float | None, unit: str) -> str:
    """Ohm cinsinden bir değeri seçilen birimde biçimlendirir."""
    if value_ohm is None:
        return "—"
    if math.isinf(value_ohm):
        return "∞"
    return f"{value_ohm * _OHM_TO[unit]:.4g} {unit}"


def stub_reactance_ohm(method: str, required_value: float | None,
                       z0: float) -> float | None:
    """Stub'ın gerçek giriş reaktansını (Ω) verir.

    * Seri stub  : X = x_stub · Z₀
    * Paralel stub: stub suseptans B sağlar; giriş reaktansı X = −Z₀ / b_stub
    * Çeyrek dalga: değer zaten Z_t (Ω) karakteristik empedanstır, aynen döner.
    """
    if required_value is None:
        return None
    m = method.lower()
    if "çeyrek dalga" in m:
        return required_value
    if "paralel" in m:
        if required_value == 0:
            return float("inf")
        return -z0 / required_value
    return required_value * z0


# ----------------------------------------------------------------------
# Kademeli devre uzunluk girişleri: λ veya fiziksel (m/cm/mm)
# ----------------------------------------------------------------------
CASCADE_LENGTH_UNITS: tuple[str, ...] = ("λ", "m", "cm", "mm")
_PHYS_TO_M = {"m": 1.0, "cm": 1e-2, "mm": 1e-3}


def to_electrical_lambda(value: float, unit: str, epsilon_r: float,
                         lambda0_m: float) -> float:
    """Bir uzunluk girişini ORTAM elektriksel uzunluğuna (λ) çevirir.

    * unit == "λ"  : değer doğrudan elektriksel uzunluktur (εr etkisizdir).
    * fiziksel (m/cm/mm): ℓ_elek = ℓ_fiz / λ_ortam = ℓ_fiz·√εr / λ0
    """
    if unit == "λ":
        return value
    if lambda0_m <= 0:
        return 0.0
    meters = value * _PHYS_TO_M[unit]
    lam_med = lambda0_m / (max(epsilon_r, 1e-9) ** 0.5)
    return meters / lam_med
