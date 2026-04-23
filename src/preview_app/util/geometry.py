from __future__ import annotations


def pt_to_px(pt: float, dpi: int) -> float:
    return pt * dpi / 72.0


def px_to_pt(px: float, dpi: int) -> float:
    return px * 72.0 / dpi


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
