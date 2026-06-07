from core.models import (
    LoadData,
    BasicAnalysisResult,
    LineTransformResult,
    AnalyzerOutput,
    MatchingSolution,
)
from core.units import wavelength_from_frequency, lambda_to_meter
from core.rf_math import basic_analysis
from core.transmission_line import transform_along_line
from core.matching import (
    solve_shunt_stub,
    solve_series_stub,
    solve_quarter_wave_transformer,
    solve_all_matching_methods,
)


class SmithAnalyzer:
    def analyze_basic(self, load: LoadData) -> BasicAnalysisResult:
        wavelength_m = wavelength_from_frequency(
            frequency_hz=load.frequency_hz,
            velocity_factor=load.velocity_factor
        )

        data = basic_analysis(
            z_load=load.z_load,
            z0=load.z0_ohm,
            wavelength_m=wavelength_m
        )

        return BasicAnalysisResult(
            z_load=data["z_load"],
            z0=data["z0"],
            z_norm=data["z_norm"],
            y_norm=data["y_norm"],
            gamma=data["gamma"],
            gamma_mag=data["gamma_mag"],
            gamma_angle_deg=data["gamma_angle_deg"],
            vswr=data["vswr"],
            return_loss_db=data["return_loss_db"],
            load_type=data["load_type"],
            wavelength_m=data["wavelength_m"],
        )

    def analyze_line(
        self,
        load: LoadData,
        length_lambda: float,
        direction: str = "load_to_source"
    ) -> LineTransformResult:
        basic = self.analyze_basic(load)

        data = transform_along_line(
            z_load=load.z_load,
            z0=load.z0_ohm,
            length_lambda=length_lambda,
            wavelength_m=basic.wavelength_m,
            direction=direction
        )

        return LineTransformResult(
            length_lambda=data["length_lambda"],
            length_m=data["length_m"],
            direction=data["direction"],
            gamma_start=data["gamma_start"],
            gamma_end=data["gamma_end"],
            z_start_norm=data["z_start_norm"],
            z_end_norm=data["z_end_norm"],
            z_start_ohm=data["z_start_ohm"],
            z_end_ohm=data["z_end_ohm"],
            y_end_norm=data["y_end_norm"],
            electrical_angle_deg=data["electrical_angle_deg"],
        )

    def solve_matching(
        self,
        load: LoadData,
        method: str
    ) -> list[MatchingSolution]:
        basic = self.analyze_basic(load)
        wavelength_m = basic.wavelength_m

        if method == "shunt_short":
            return solve_shunt_stub(load.z_load, load.z0_ohm, wavelength_m, "short")

        if method == "shunt_open":
            return solve_shunt_stub(load.z_load, load.z0_ohm, wavelength_m, "open")

        if method == "series_short":
            return solve_series_stub(load.z_load, load.z0_ohm, wavelength_m, "short")

        if method == "series_open":
            return solve_series_stub(load.z_load, load.z0_ohm, wavelength_m, "open")

        if method == "quarter_wave":
            return solve_quarter_wave_transformer(load.z_load, load.z0_ohm, wavelength_m)

        if method == "auto":
            return solve_all_matching_methods(load.z_load, load.z0_ohm, wavelength_m)

        return []

    def analyze_all(
        self,
        load: LoadData,
        length_lambda: float | None = None,
        direction: str = "load_to_source",
        matching_method: str | None = None
    ) -> AnalyzerOutput:
        """
        UI'nin tek çağrıyla kullanabileceği genel analiz fonksiyonu.
        """
        basic = self.analyze_basic(load)

        line = None
        if length_lambda is not None:
            line = self.analyze_line(
                load=load,
                length_lambda=length_lambda,
                direction=direction
            )

        matching_solutions = []
        if matching_method:
            matching_solutions = self.solve_matching(
                load=load,
                method=matching_method
            )
            # Çözümler en iyiden en kötüye sıralanır. Ölçüt: en kısa toplam
            # fiziksel uzunluk (d + ℓ). Tek kaynak burası olduğu için tablo,
            # çözüm seçici ve 2B/3B grafikler hep aynı sırayı görür; "Çözüm 1"
            # daima en iyi çözümdür.
            matching_solutions = sorted(
                matching_solutions,
                key=lambda s: (s.d_lambda or 0.0) + (s.stub_length_lambda or 0.0),
            )

        return AnalyzerOutput(
            basic=basic,
            line=line,
            matching_solutions=matching_solutions
        )