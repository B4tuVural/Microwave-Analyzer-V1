import numpy as np

from core.rf_math import z_to_gamma, y_to_gamma


def constant_resistance_curve(r: float, n: int = 4000) -> np.ndarray:
    """
    Empedans Smith diyagramında sabit normalize direnç eğrisini üretir.

    z = r + jx
    """
    x = np.linspace(-400, 400, n)
    z = r + 1j * x

    gamma = z_to_gamma(z)

    return gamma[np.abs(gamma) <= 1.000001]


def constant_reactance_curve(x: float, n: int = 4000) -> np.ndarray:
    """
    Empedans Smith diyagramında sabit normalize reaktans eğrisini üretir.

    z = r + jx
    """
    r = np.linspace(0, 400, n)
    z = r + 1j * x

    gamma = z_to_gamma(z)

    return gamma[np.abs(gamma) <= 1.000001]


def constant_conductance_curve(g: float, n: int = 4000) -> np.ndarray:
    """
    Admitans Smith diyagramında sabit normalize iletkenlik eğrisini üretir.

    y = g + jb
    """
    b = np.linspace(-400, 400, n)
    y = g + 1j * b

    gamma = y_to_gamma(y)

    return gamma[np.abs(gamma) <= 1.000001]


def constant_susceptance_curve(b: float, n: int = 4000) -> np.ndarray:
    """
    Admitans Smith diyagramında sabit normalize süseptans eğrisini üretir.

    y = g + jb
    """
    g = np.linspace(0, 400, n)
    y = g + 1j * b

    gamma = y_to_gamma(y)

    return gamma[np.abs(gamma) <= 1.000001]


def gamma_circle(radius: float, n: int = 1600) -> np.ndarray:
    """
    Gamma düzleminde merkezde olan çember üretir.
    VSWR ve geri dönüş kaybı çemberleri için kullanılır.
    """
    t = np.linspace(0, 2 * np.pi, n)
    return radius * (np.cos(t) + 1j * np.sin(t))


def gamma_to_hemisphere(gamma: np.ndarray):
    """
    Gamma düzlemindeki noktaları 3B kürenin üst yarısına taşır.

    Gamma = u + jv

    x = u
    y = v
    z = sqrt(1 - u^2 - v^2)
    """
    gamma = np.asarray(gamma, dtype=complex)

    x = np.real(gamma)
    y = np.imag(gamma)

    r2 = x**2 + y**2

    z = np.full_like(x, np.nan, dtype=float)
    valid = r2 <= 1.0 + 1e-12

    z[valid] = np.sqrt(np.maximum(0.0, 1.0 - r2[valid]))

    return x, y, z


def default_resistance_values(detail: str = "medium") -> list[float]:
    """
    Çizilecek normalize direnç / iletkenlik değerlerini verir.
    Empedans görünümünde r, admitans görünümünde g için kullanılır.
    """
    detail = detail.lower()

    if detail == "low":
        return [0, 0.2, 0.5, 1, 2, 5]

    if detail == "high":
        return [
            0.01, 0.02, 0.03, 0.05, 0.07,
            0.1, 0.15, 0.2, 0.3, 0.4,
            0.5, 0.7, 1.0, 1.2, 1.5,
            2.0, 3.0, 4.0, 5.0, 7.0,
            10.0, 15.0
        ]

    return [
        0.02, 0.05, 0.1, 0.15, 0.2,
        0.3, 0.5, 0.7, 1.0, 1.5,
        2.0, 3.0, 5.0, 10.0
    ]


def default_reactance_values(detail: str = "medium") -> list[float]:
    """
    Çizilecek normalize reaktans / süseptans değerlerini verir.
    Empedans görünümünde x, admitans görünümünde b için kullanılır.
    """
    detail = detail.lower()

    if detail == "low":
        return [0.2, 0.5, 1, 2, 5]

    if detail == "high":
        return [
            0.01, 0.02, 0.03, 0.05, 0.07,
            0.1, 0.15, 0.2, 0.3, 0.4,
            0.5, 0.7, 1.0, 1.2, 1.5,
            2.0, 3.0, 4.0, 5.0, 7.0,
            10.0, 15.0
        ]

    return [
        0.02, 0.05, 0.1, 0.15, 0.2,
        0.3, 0.5, 0.7, 1.0, 1.5,
        2.0, 3.0, 5.0, 10.0
    ]


def default_vswr_values(detail: str = "medium") -> list[float]:
    """
    Çizilecek DDO / VSWR çemberlerini verir.
    """
    detail = detail.lower()

    if detail == "low":
        return [1.5, 2, 3, 5]

    if detail == "high":
        return [1.05, 1.1, 1.2, 1.3, 1.5, 2, 2.5, 3, 4, 5, 7, 10]

    return [1.1, 1.2, 1.3, 1.5, 2, 3, 5, 10]