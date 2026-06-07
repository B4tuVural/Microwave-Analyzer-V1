from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class LoadData:
    r_ohm: float
    x_ohm: float
    z0_ohm: float
    frequency_hz: float
    velocity_factor: float = 1.0

    @property
    def z_load(self) -> complex:
        return complex(self.r_ohm, self.x_ohm)


@dataclass
class BasicAnalysisResult:
    z_load: complex
    z0: float
    z_norm: complex
    y_norm: complex
    gamma: complex
    gamma_mag: float
    gamma_angle_deg: float
    vswr: float
    return_loss_db: float
    load_type: str
    wavelength_m: float


@dataclass
class LineTransformResult:
    length_lambda: float
    length_m: float
    direction: str

    gamma_start: complex
    gamma_end: complex

    z_start_norm: complex
    z_end_norm: complex

    z_start_ohm: complex
    z_end_ohm: complex

    y_end_norm: complex
    electrical_angle_deg: float


@dataclass
class MatchingSolution:
    method: str
    stub_type: str

    d_lambda: Optional[float] = None
    stub_length_lambda: Optional[float] = None

    d_meter: Optional[float] = None
    stub_length_meter: Optional[float] = None

    wavelength_m: Optional[float] = None

    point_value: Optional[complex] = None
    required_stub_value: Optional[float] = None

    gamma_at_stub: Optional[complex] = None
    gamma_matched: complex = 0 + 0j

    notes: List[str] = field(default_factory=list)


@dataclass
class AnalyzerOutput:
    basic: BasicAnalysisResult
    line: Optional[LineTransformResult] = None
    matching_solutions: List[MatchingSolution] = field(default_factory=list)