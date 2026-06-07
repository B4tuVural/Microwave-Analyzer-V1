C0 = 299_792_458.0


def frequency_to_hz(value: float, unit: str) -> float:
    unit = unit.strip().lower()

    if unit == "hz":
        return value
    if unit == "khz":
        return value * 1e3
    if unit == "mhz":
        return value * 1e6
    if unit == "ghz":
        return value * 1e9

    raise ValueError(f"Geçersiz frekans birimi: {unit}")


def wavelength_from_frequency(frequency_hz: float, velocity_factor: float = 1.0) -> float:
    if frequency_hz <= 0:
        raise ValueError("Frekans sıfırdan büyük olmalıdır.")

    if velocity_factor <= 0:
        raise ValueError("Faz hızı oranı sıfırdan büyük olmalıdır.")

    phase_velocity = velocity_factor * C0
    return phase_velocity / frequency_hz


def lambda_to_meter(length_lambda: float, wavelength_m: float) -> float:
    return length_lambda * wavelength_m


def meter_to_lambda(length_m: float, wavelength_m: float) -> float:
    if wavelength_m <= 0:
        raise ValueError("Dalga boyu sıfırdan büyük olmalıdır.")

    return length_m / wavelength_m


def normalize_lambda(value: float) -> float:
    return value % 0.5