"""ui/format.py — sayı biçimlendirme yardımcıları (sunum katmanı)."""

from __future__ import annotations

import math


def fmt_complex(value: complex, digits: int = 4) -> str:
    return f"{value.real:.{digits}f} {value.imag:+.{digits}f}j"


def fmt_float(value, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and math.isinf(value):
        return "∞"
    return f"{value:.{digits}f}"
