import numpy as np

from core.rf_math import (
    z_to_gamma,
    gamma_to_z,
    impedance_to_admittance,
    denormalize_impedance,
)
from core.units import lambda_to_meter


def electrical_angle_deg(length_lambda: float) -> float:
    return 720.0 * length_lambda


def rotate_gamma(
    gamma: complex,
    length_lambda: float,
    direction: str = "load_to_source"
) -> complex:
    theta = np.radians(electrical_angle_deg(length_lambda))

    if direction == "load_to_source":
        return gamma * np.exp(-1j * theta)

    if direction == "source_to_load":
        return gamma * np.exp(+1j * theta)

    raise ValueError(f"Geçersiz ilerleme yönü: {direction}")


def input_impedance_normalized(
    z_load_norm: complex,
    length_lambda: float
) -> complex:
    beta_l = 2 * np.pi * length_lambda
    t = np.tan(beta_l)

    return (z_load_norm + 1j * t) / (1 + 1j * z_load_norm * t)


def input_admittance_normalized(
    z_load_norm: complex,
    length_lambda: float
) -> complex:
    z_in = input_impedance_normalized(z_load_norm, length_lambda)
    return impedance_to_admittance(z_in)


def transform_along_line(
    z_load: complex,
    z0: float,
    length_lambda: float,
    wavelength_m: float,
    direction: str = "load_to_source"
):
    z_start_norm = z_load / z0
    gamma_start = z_to_gamma(z_start_norm)

    gamma_end = rotate_gamma(
        gamma=gamma_start,
        length_lambda=length_lambda,
        direction=direction
    )

    z_end_norm = gamma_to_z(gamma_end)
    z_end_ohm = denormalize_impedance(z_end_norm, z0)
    y_end_norm = impedance_to_admittance(z_end_norm)

    return {
        "length_lambda": length_lambda,
        "length_m": lambda_to_meter(length_lambda, wavelength_m),
        "direction": direction,
        "gamma_start": gamma_start,
        "gamma_end": gamma_end,
        "z_start_norm": z_start_norm,
        "z_end_norm": z_end_norm,
        "z_start_ohm": z_load,
        "z_end_ohm": z_end_ohm,
        "y_end_norm": y_end_norm,
        "electrical_angle_deg": electrical_angle_deg(length_lambda),
    }