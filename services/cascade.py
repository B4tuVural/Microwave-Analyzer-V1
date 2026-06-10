"""
services/cascade.py
===================
Kademeli (cascade) devre çözücü motoru.

Yüke doğru tanımlanmış bir eleman zincirini (iletim hattı, seri stub, paralel
stub) **yükten kaynağa** doğru çözer. Her eleman:
  * önce kendi **d** besleme hattından (elektriksel uzunluk, ortam λ) geçer,
  * sonra (stub ise) kendi **ℓ** uzunluğundaki stub etkisini uygular.
Böylece "yükten d kadar uzakta bir stub" doğrudan tanımlanabilir.

Tasarım
-------
* Saf modül — Streamlit'e bağımlı değildir, tek başına test edilebilir.
* Çekirdek (core/) DEĞİŞTİRİLMEZ; yalnızca temel RF ilişkileri bestelenir.
* Elektriksel uzunluklar (λ) doğrudan alınır; fiziksel↔elektriksel çevrim UI'de
  yapılır (λ girilirse aynen; m/cm/mm girilirse εr ve frekansla). λ0 yalnızca
  fiziksel uzunluk RAPORLAMAK için kullanılır.

Fiziksel model
--------------
* θ = βℓ = 2π · (elektriksel uzunluk, λ)
* İletim hattı : Z_in = Z0·(Z + jZ0·tanθ)/(Z0 + jZ·tanθ)
* Açık uçlu stub : Z = −j·Z0·cot(θ)
* Kısa devre stub: Z = +j·Z0·tan(θ)
* Seri stub  : Z_yeni = Z + Z_stub
* Paralel stub: Y_yeni = Y + 1/Z_stub
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from core.units import C0

KIND_LINE = "line"
KIND_SERIES = "series_stub"
KIND_SHUNT = "shunt_stub"

KIND_LABELS = {
    KIND_LINE: "İletim hattı",
    KIND_SERIES: "Seri stub",
    KIND_SHUNT: "Paralel stub",
}


# ----------------------------------------------------------------------
# Veri modelleri
# ----------------------------------------------------------------------
@dataclass
class CascadeElement:
    """Tek bir kademeli devre elemanı (elektriksel uzunluklar λ cinsinden)."""
    kind: str                       # KIND_LINE | KIND_SERIES | KIND_SHUNT
    z0: float                       # Ω
    epsilon_r: float = 1.0          # bağıl dielektrik sabiti
    d_lambda: float = 0.0           # besleme/hat elektriksel uzunluğu (ortam λ)
    stub_len_lambda: float = 0.0    # stub'ın kendi elektriksel uzunluğu (ortam λ)
    termination: str = "open"       # stub: "open" | "short"
    is_load_line: bool = False      # yük besleme hattı mı (etiketleme için)


@dataclass
class ElementInfo:
    index: int
    kind: str
    z0: float
    epsilon_r: float
    d_lambda: float
    stub_len_lambda: float
    d_meter: float
    stub_len_meter: float
    theta_d_deg: float
    theta_stub_deg: float
    termination: str
    z_after: complex
    stub_reactance: Optional[complex] = None
    is_load_line: bool = False


@dataclass
class CascadeNode:
    label: str
    z: complex
    gamma: complex


@dataclass
class CascadeResult:
    z0_ref: float
    frequency_hz: float
    lambda0_m: float
    start_load: complex
    trajectory: np.ndarray
    nodes: List[CascadeNode]
    elements: List[ElementInfo]
    z_in: complex
    gamma_in: complex
    vswr: float
    return_loss_db: float


# ----------------------------------------------------------------------
# Yardımcılar
# ----------------------------------------------------------------------
def _gamma_ref(z: complex, z0_ref: float) -> complex:
    return (z - z0_ref) / (z + z0_ref)


def _stub_input_impedance(z0: float, theta: float, termination: str) -> complex:
    t = np.tan(theta)
    if termination == "short":
        return complex(0, z0 * t)
    if abs(t) < 1e-12:
        return complex(0, -z0 * 1e12)
    return complex(0, -z0 / t)


def _line_transform(z: complex, z0: float, theta: float) -> complex:
    t = np.tan(theta)
    return z0 * (z + 1j * z0 * t) / (z0 + 1j * z * t)


def _metrics(gamma: complex):
    mag = abs(gamma)
    vswr = float("inf") if mag >= 1 else (1 + mag) / (1 - mag)
    rl = float("inf") if mag == 0 else float(-20 * np.log10(mag))
    return vswr, rl


# ----------------------------------------------------------------------
# Çözücü
# ----------------------------------------------------------------------
def solve_cascade(load: complex, z0_ref: float, frequency_hz: float,
                  elements: List[CascadeElement],
                  samples_per_line: int = 50) -> CascadeResult:
    """Eleman zincirini yükten kaynağa çözer (ilk eleman yüke en yakın)."""
    if frequency_hz <= 0:
        raise ValueError("Frekans sıfırdan büyük olmalıdır.")

    lambda0 = C0 / frequency_hz
    z = complex(load)
    traj: list[complex] = [_gamma_ref(z, z0_ref)]
    nodes: list[CascadeNode] = [CascadeNode("Yük", z, _gamma_ref(z, z0_ref))]
    infos: list[ElementInfo] = []

    for idx, el in enumerate(elements, start=1):
        lam_med = lambda0 / np.sqrt(max(el.epsilon_r, 1e-9))
        stub_reactance: Optional[complex] = None

        # 1) besleme hattı (d_lambda) — bu elemanın z0/εr'siyle
        if el.d_lambda > 1e-12:
            for s in np.linspace(0.0, el.d_lambda, samples_per_line)[1:]:
                traj.append(_gamma_ref(_line_transform(z, el.z0, 2 * np.pi * s), z0_ref))
            z = _line_transform(z, el.z0, 2 * np.pi * el.d_lambda)

        # 2) stub etkisi
        if el.kind == KIND_SERIES:
            stub_reactance = _stub_input_impedance(el.z0, 2 * np.pi * el.stub_len_lambda,
                                                   el.termination)
            z_new = z + stub_reactance
            for frac in np.linspace(0.0, 1.0, 20)[1:]:
                traj.append(_gamma_ref(complex(z.real, z.imag + frac * stub_reactance.imag),
                                       z0_ref))
            z = z_new

        elif el.kind == KIND_SHUNT:
            stub_reactance = _stub_input_impedance(el.z0, 2 * np.pi * el.stub_len_lambda,
                                                   el.termination)
            y = 1 / z
            y_stub = 1 / stub_reactance
            for frac in np.linspace(0.0, 1.0, 20)[1:]:
                traj.append(_gamma_ref(1 / complex(y.real, y.imag + frac * y_stub.imag),
                                       z0_ref))
            z = 1 / (y + y_stub)

        infos.append(ElementInfo(
            index=idx, kind=el.kind, z0=el.z0, epsilon_r=el.epsilon_r,
            d_lambda=el.d_lambda, stub_len_lambda=el.stub_len_lambda,
            d_meter=el.d_lambda * lam_med, stub_len_meter=el.stub_len_lambda * lam_med,
            theta_d_deg=float(np.degrees(2 * np.pi * el.d_lambda) % 360.0),
            theta_stub_deg=float(np.degrees(2 * np.pi * el.stub_len_lambda) % 360.0),
            termination=el.termination, z_after=z, stub_reactance=stub_reactance,
            is_load_line=el.is_load_line,
        ))
        nodes.append(CascadeNode(f"Düğüm {idx}", z, _gamma_ref(z, z0_ref)))

    gamma_in = _gamma_ref(z, z0_ref)
    vswr, rl = _metrics(gamma_in)
    return CascadeResult(
        z0_ref=z0_ref, frequency_hz=frequency_hz, lambda0_m=lambda0,
        start_load=complex(load), trajectory=np.array(traj),
        nodes=nodes, elements=infos, z_in=z, gamma_in=gamma_in,
        vswr=vswr, return_loss_db=rl,
    )
