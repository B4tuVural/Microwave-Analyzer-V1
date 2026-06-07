import numpy as np

from core.models import MatchingSolution
from core.rf_math import (
    normalize_impedance,
    impedance_to_admittance,
    z_to_gamma,
)
from core.transmission_line import (
    input_impedance_normalized,
    input_admittance_normalized,
)
from core.units import lambda_to_meter


# =========================================================
# GENEL YARDIMCILAR
# =========================================================

def _unique_roots(values: list[float], tolerance: float = 1e-4) -> list[float]:
    roots = []

    for value in values:
        value = value % 0.5

        if all(abs(value - old) > tolerance and abs(abs(value - old) - 0.5) > tolerance for old in roots):
            roots.append(value)

    roots.sort()
    return roots


def _find_roots_on_half_lambda(func, samples: int = 6000) -> list[float]:
    d_values = np.linspace(0.0, 0.5, samples, endpoint=False)
    f_values = np.array([func(d) for d in d_values], dtype=float)

    roots = []

    for i in range(len(d_values) - 1):
        f1 = f_values[i]
        f2 = f_values[i + 1]

        if not np.isfinite(f1) or not np.isfinite(f2):
            continue

        if abs(f1) < 1e-5:
            roots.append(d_values[i])
            continue

        if f1 * f2 < 0:
            a = d_values[i]
            b = d_values[i + 1]

            # Bisection
            for _ in range(50):
                m = (a + b) / 2
                fm = func(m)
                fa = func(a)

                if not np.isfinite(fm):
                    break

                if fa * fm <= 0:
                    b = m
                else:
                    a = m

            roots.append((a + b) / 2)

    return _unique_roots(roots, tolerance=1e-4)


def _angle_to_lambda(theta_rad: float) -> float:
    theta_rad = theta_rad % np.pi

    if theta_rad < 0:
        theta_rad += np.pi

    return theta_rad / (2 * np.pi)


def _short_stub_length_for_susceptance(b_stub: float) -> float:
    # -cot(theta) = b_stub
    # cot(theta) = -b_stub
    target_cot = -b_stub

    theta = np.arctan2(1.0, target_cot)

    if theta <= 0:
        theta += np.pi

    return theta / (2 * np.pi)


def _open_stub_length_for_susceptance(b_stub: float) -> float:
    theta = np.arctan(b_stub)

    if theta <= 0:
        theta += np.pi

    return theta / (2 * np.pi)


def _short_stub_length_for_reactance(x_stub: float) -> float:
    theta = np.arctan(x_stub)

    if theta <= 0:
        theta += np.pi

    return theta / (2 * np.pi)


def _open_stub_length_for_reactance(x_stub: float) -> float:
    target_cot = -x_stub

    theta = np.arctan2(1.0, target_cot)

    if theta <= 0:
        theta += np.pi

    return theta / (2 * np.pi)


# =========================================================
# PARALEL STUB UYGUNLAMA
# =========================================================

def solve_shunt_stub(
    z_load: complex,
    z0: float,
    wavelength_m: float,
    stub_type: str = "short"
) -> list[MatchingSolution]:
    z_norm = normalize_impedance(z_load, z0)

    def condition(d_lambda: float) -> float:
        y = input_admittance_normalized(z_norm, d_lambda)
        return y.real - 1.0

    roots = _find_roots_on_half_lambda(condition)

    solutions: list[MatchingSolution] = []

    for idx, d_lambda in enumerate(roots[:2], start=1):
        y_at_d = input_admittance_normalized(z_norm, d_lambda)

        b_at_d = y_at_d.imag
        b_stub = -b_at_d

        if stub_type == "short":
            stub_l_lambda = _short_stub_length_for_susceptance(b_stub)
            method = "Paralel kısa devre yan hat"
            stub_label = "Kısa devre"
        elif stub_type == "open":
            stub_l_lambda = _open_stub_length_for_susceptance(b_stub)
            method = "Paralel açık devre yan hat"
            stub_label = "Açık devre"
        else:
            raise ValueError(f"Geçersiz paralel stub tipi: {stub_type}")

        gamma_at_stub = z_to_gamma(1 / y_at_d)

        sol = MatchingSolution(
            method=method,
            stub_type=stub_label,
            d_lambda=d_lambda,
            stub_length_lambda=stub_l_lambda,
            d_meter=lambda_to_meter(d_lambda, wavelength_m),
            stub_length_meter=lambda_to_meter(stub_l_lambda, wavelength_m),
            wavelength_m=wavelength_m,
            point_value=y_at_d,
            required_stub_value=b_stub,
            gamma_at_stub=gamma_at_stub,
            gamma_matched=0 + 0j,
            notes=[
                f"Yükten kaynak yönüne d={d_lambda:.6f}λ ilerlenir.",
                f"Bu noktada normalize admitans y(d)={y_at_d.real:.6f}{y_at_d.imag:+.6f}j olur.",
                "Paralel bağlantıda admitanslar toplandığı için sanal admitans bileşeni stub ile yok edilir.",
                f"Gerekli stub susceptance değeri b_stub={b_stub:.6f} olur.",
            ]
        )

        solutions.append(sol)

    return solutions


# =========================================================
# SERİ STUB UYGUNLAMA
# =========================================================

def solve_series_stub(
    z_load: complex,
    z0: float,
    wavelength_m: float,
    stub_type: str = "short"
) -> list[MatchingSolution]:
    z_norm = normalize_impedance(z_load, z0)

    def condition(d_lambda: float) -> float:
        z = input_impedance_normalized(z_norm, d_lambda)
        return z.real - 1.0

    roots = _find_roots_on_half_lambda(condition)

    solutions: list[MatchingSolution] = []

    for idx, d_lambda in enumerate(roots[:2], start=1):
        z_at_d = input_impedance_normalized(z_norm, d_lambda)

        x_at_d = z_at_d.imag
        x_stub = -x_at_d

        if stub_type == "short":
            stub_l_lambda = _short_stub_length_for_reactance(x_stub)
            method = "Seri kısa devre yan hat"
            stub_label = "Kısa devre"
        elif stub_type == "open":
            stub_l_lambda = _open_stub_length_for_reactance(x_stub)
            method = "Seri açık devre yan hat"
            stub_label = "Açık devre"
        else:
            raise ValueError(f"Geçersiz seri stub tipi: {stub_type}")

        gamma_at_stub = z_to_gamma(z_at_d)

        sol = MatchingSolution(
            method=method,
            stub_type=stub_label,
            d_lambda=d_lambda,
            stub_length_lambda=stub_l_lambda,
            d_meter=lambda_to_meter(d_lambda, wavelength_m),
            stub_length_meter=lambda_to_meter(stub_l_lambda, wavelength_m),
            wavelength_m=wavelength_m,
            point_value=z_at_d,
            required_stub_value=x_stub,
            gamma_at_stub=gamma_at_stub,
            gamma_matched=0 + 0j,
            notes=[
                f"Yükten kaynak yönüne d={d_lambda:.6f}λ ilerlenir.",
                f"Bu noktada normalize empedans z(d)={z_at_d.real:.6f}{z_at_d.imag:+.6f}j olur.",
                "Seri bağlantıda empedanslar toplandığı için sanal empedans bileşeni stub ile yok edilir.",
                f"Gerekli stub reactance değeri x_stub={x_stub:.6f} olur.",
            ]
        )

        solutions.append(sol)

    return solutions


# =========================================================
# ÇEYREK DALGA TRANSFORMATÖR
# =========================================================

def solve_quarter_wave_transformer(
    z_load: complex,
    z0: float,
    wavelength_m: float
) -> list[MatchingSolution]:
    if abs(z_load.imag) > 1e-9:
        return []

    if z_load.real <= 0:
        return []

    zt = float(np.sqrt(z0 * z_load.real))

    sol = MatchingSolution(
        method="Çeyrek dalga transformatör",
        stub_type="λ/4 trafo",
        d_lambda=0.0,
        stub_length_lambda=0.25,
        d_meter=0.0,
        stub_length_meter=lambda_to_meter(0.25, wavelength_m),
        wavelength_m=wavelength_m,
        point_value=complex(zt, 0),
        required_stub_value=zt,
        gamma_at_stub=z_to_gamma(z_load / z0),
        gamma_matched=0 + 0j,
        notes=[
            "Yük saf dirençli olduğu için çeyrek dalga transformatör uygulanabilir.",
            f"Gerekli transformatör karakteristik empedansı Zt=sqrt(Z0*RL)={zt:.6f} ohm olur.",
            "Transformatör uzunluğu λ/4 seçilir.",
        ]
    )

    return [sol]


# =========================================================
# OTOMATİK UYGUNLAMA
# =========================================================

def solve_all_matching_methods(
    z_load: complex,
    z0: float,
    wavelength_m: float
) -> list[MatchingSolution]:
    solutions: list[MatchingSolution] = []

    solutions.extend(solve_shunt_stub(z_load, z0, wavelength_m, "short"))
    solutions.extend(solve_shunt_stub(z_load, z0, wavelength_m, "open"))
    solutions.extend(solve_series_stub(z_load, z0, wavelength_m, "short"))
    solutions.extend(solve_series_stub(z_load, z0, wavelength_m, "open"))
    solutions.extend(solve_quarter_wave_transformer(z_load, z0, wavelength_m))

    # En kısa toplam fiziksel uzunluğa göre sıralayalım.
    solutions.sort(
        key=lambda s: (
            (s.d_lambda or 0.0) + (s.stub_length_lambda or 0.0)
        )
    )

    return solutions