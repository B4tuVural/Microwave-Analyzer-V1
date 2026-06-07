import numpy as np


def normalize_impedance(z_load: complex, z0: float) -> complex:
    if z0 == 0:
        raise ValueError("Z0 sıfır olamaz.")

    return z_load / z0


def denormalize_impedance(z_norm: complex, z0: float) -> complex:
    return z_norm * z0


def impedance_to_admittance(z: complex) -> complex:
    if abs(z) == 0:
        raise ValueError("Sıfır empedans admitansa çevrilemez.")

    return 1 / z


def admittance_to_impedance(y: complex) -> complex:
    if abs(y) == 0:
        raise ValueError("Sıfır admitans empedansa çevrilemez.")

    return 1 / y


def z_to_gamma(z_norm: complex | np.ndarray) -> complex | np.ndarray:
    return (z_norm - 1) / (z_norm + 1)


def gamma_to_z(gamma: complex | np.ndarray) -> complex | np.ndarray:
    return (1 + gamma) / (1 - gamma)


def y_to_gamma(y_norm: complex | np.ndarray) -> complex | np.ndarray:
    return (1 - y_norm) / (1 + y_norm)


def gamma_to_y(gamma: complex | np.ndarray) -> complex | np.ndarray:
    return (1 - gamma) / (1 + gamma)


def vswr_from_gamma(gamma: complex) -> float:
    mag = abs(gamma)

    if mag >= 1:
        return float("inf")

    return (1 + mag) / (1 - mag)


def return_loss_from_gamma(gamma: complex) -> float:
    mag = abs(gamma)

    if mag == 0:
        return float("inf")

    return -20 * np.log10(mag)


def gamma_angle_deg(gamma: complex) -> float:
    return float(np.degrees(np.angle(gamma)))


def load_type_from_reactance(x_ohm: float) -> str:
    eps = 1e-12

    if x_ohm > eps:
        return "İndüktif (+jX)"

    if x_ohm < -eps:
        return "Kapasitif (-jX)"

    return "Saf dirençli"


def basic_analysis(z_load: complex, z0: float, wavelength_m: float):
    z_norm = normalize_impedance(z_load, z0)
    y_norm = impedance_to_admittance(z_norm)
    gamma = z_to_gamma(z_norm)

    return {
        "z_load": z_load,
        "z0": z0,
        "z_norm": z_norm,
        "y_norm": y_norm,
        "gamma": gamma,
        "gamma_mag": abs(gamma),
        "gamma_angle_deg": gamma_angle_deg(gamma),
        "vswr": vswr_from_gamma(gamma),
        "return_loss_db": return_loss_from_gamma(gamma),
        "load_type": load_type_from_reactance(z_load.imag),
        "wavelength_m": wavelength_m,
    }