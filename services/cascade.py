"""
services/cascade.py
===================
Kademeli (cascade) devre çözücü motoru.

Yüke doğru tanımlanmış bir eleman zincirini (iletim hattı, seri stub, paralel
stub) **yükten kaynağa** doğru çözer; her düğümdeki empedansı, sürekli Smith
yörüngesini ve giriş empedansını (Z_in) hesaplar.

Tasarım
-------
* Saf modül — Streamlit'e bağımlı değildir, tek başına test edilebilir.
* Çekirdek (core/) DEĞİŞTİRİLMEZ; bu modül yalnızca temel RF ilişkilerini
  besteler (composition). Smith çizimi için her düğüm, referans empedansa
  (Z0_ref) göre Γ'ya dönüştürülür.

Fiziksel model
--------------
* Serbest uzay dalga boyu : λ0 = c / f
* Eleman ortamı dalga boyu : λ = λ0 / √εr      (faz hızı vp = c/√εr)
* Elektriksel uzunluk      : θ = βℓ = 2π · (ℓ_fiz / λ)
* İletim hattı dönüşümü    : Z_in = Z0·(Z_L + jZ0·tanθ)/(Z0 + jZ_L·tanθ)
* Açık uçlu stub           : Z = −j·Z0·cot(θ)
* Kısa devre stub          : Z = +j·Z0·tan(θ)
* Seri stub                : Z_yeni = Z + Z_stub
* Paralel stub             : Y_yeni = Y + 1/Z_stub
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
    """Kullanıcının eklediği tek bir kademeli devre elemanı."""
    kind: str                       # KIND_LINE | KIND_SERIES | KIND_SHUNT
    z0: float                       # Ω (hat veya stub karakteristik empedansı)
    epsilon_r: float = 1.0          # bağıl dielektrik sabiti
    length_m: float = 0.0           # fiziksel uzunluk (m)
    termination: str = "open"       # stub için: "open" | "short"


@dataclass
class ElementInfo:
    """Bir elemanın çözüm sonrası hesaplanan özellikleri."""
    index: int
    kind: str
    z0: float
    epsilon_r: float
    length_m: float
    lambda_med_m: float
    length_lambda: float            # ortam λ cinsinden elektriksel uzunluk
    theta_deg: float                # βℓ (derece)
    termination: str
    z_after: complex                # bu elemandan sonra (kaynağa doğru) görülen Z
    stub_reactance: Optional[complex] = None  # stub giriş empedansı (jX)


@dataclass
class CascadeNode:
    label: str
    z: complex
    gamma: complex                  # Z0_ref'e göre


@dataclass
class CascadeResult:
    z0_ref: float
    frequency_hz: float
    lambda0_m: float
    start_load: complex
    trajectory: np.ndarray          # sürekli Γ_ref yörüngesi
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
    """Açık/kısa devre sonlu bir hat parçasının giriş empedansı (saf reaktans)."""
    t = np.tan(theta)
    if termination == "short":
        return 1j * z0 * t
    # açık devre: Z = -j Z0 cot(θ) = -j Z0 / tan(θ)
    if abs(t) < 1e-12:
        return complex(0, -z0 * 1e12)   # cot(0) -> ∞
    return complex(0, -z0 / t)


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
                  samples_per_line: int = 60) -> CascadeResult:
    """Eleman zincirini yükten kaynağa çözer ve CascadeResult döndürür.

    `elements` sırası YÜKTEN KAYNAĞA doğrudur (ilk eleman yüke en yakın).
    """
    if frequency_hz <= 0:
        raise ValueError("Frekans sıfırdan büyük olmalıdır.")

    lambda0 = C0 / frequency_hz
    z = complex(load)
    traj: list[complex] = [_gamma_ref(z, z0_ref)]
    nodes: list[CascadeNode] = [CascadeNode("Yük", z, _gamma_ref(z, z0_ref))]
    infos: list[ElementInfo] = []

    for idx, el in enumerate(elements, start=1):
        lam_med = lambda0 / np.sqrt(max(el.epsilon_r, 1e-9))
        length_lambda = el.length_m / lam_med if lam_med > 0 else 0.0
        theta = 2 * np.pi * length_lambda
        stub_reactance: Optional[complex] = None

        if el.kind == KIND_LINE:
            for s in np.linspace(0.0, length_lambda, samples_per_line)[1:]:
                th = 2 * np.pi * s
                t = np.tan(th)
                z_s = el.z0 * (z + 1j * el.z0 * t) / (el.z0 + 1j * z * t)
                traj.append(_gamma_ref(z_s, z0_ref))
            t = np.tan(theta)
            z = el.z0 * (z + 1j * el.z0 * t) / (el.z0 + 1j * z * t)

        elif el.kind == KIND_SERIES:
            stub_reactance = _stub_input_impedance(el.z0, theta, el.termination)
            z_new = z + stub_reactance
            for frac in np.linspace(0.0, 1.0, 24)[1:]:
                z_mid = complex(z.real, z.imag + frac * stub_reactance.imag)
                traj.append(_gamma_ref(z_mid, z0_ref))
            z = z_new

        elif el.kind == KIND_SHUNT:
            stub_reactance = _stub_input_impedance(el.z0, theta, el.termination)
            y = 1 / z
            y_stub = 1 / stub_reactance
            y_new = y + y_stub
            for frac in np.linspace(0.0, 1.0, 24)[1:]:
                y_mid = complex(y.real, y.imag + frac * y_stub.imag)
                traj.append(_gamma_ref(1 / y_mid, z0_ref))
            z = 1 / y_new

        else:
            raise ValueError(f"Bilinmeyen eleman türü: {el.kind}")

        infos.append(ElementInfo(
            index=idx, kind=el.kind, z0=el.z0, epsilon_r=el.epsilon_r,
            length_m=el.length_m, lambda_med_m=lam_med,
            length_lambda=length_lambda, theta_deg=float(np.degrees(theta) % 360.0),
            termination=el.termination, z_after=z, stub_reactance=stub_reactance,
        ))
        nodes.append(CascadeNode(f"Düğüm {idx}", z, _gamma_ref(z, z0_ref)))

    gamma_in = _gamma_ref(z, z0_ref)
    vswr, rl = _metrics(gamma_in)

    return CascadeResult(
        z0_ref=z0_ref, frequency_hz=frequency_hz, lambda0_m=lambda0,
        start_load=complex(load), trajectory=np.array(traj),
        nodes=nodes, elements=infos,
        z_in=z, gamma_in=gamma_in, vswr=vswr, return_loss_db=rl,
    )
