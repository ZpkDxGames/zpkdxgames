"""Honest chart transforms and fixed intensity thresholds."""

import math
from .tokens import HEAT_BINS


def sqrt_fraction(value, maximum):
    if value < 0 or maximum < 0:
        raise ValueError("Counts cannot be negative")
    return math.sqrt(value / maximum) if maximum else 0.0


def sqrt_ticks(maximum):
    """Round raw-count ticks; preserve the maximum without capping any value."""
    candidates = [0, 1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
    while candidates[-1] < maximum:
        candidates.append(candidates[-1] * 2)
    if maximum <= 10:
        return [0, 1, 5, max(10, maximum)]
    top = next(v for v in candidates if v >= maximum)
    # Low counts and the September peak both remain visible.
    selected = [v for v in candidates if v <= top and v in (0, 10, 50, 100, 250, 500)]
    if top not in selected:
        selected.append(top)
    if len(selected) > 6:
        selected = [selected[0], selected[1], selected[2], *selected[-3:]]
    return selected


def rolling_average(values, days=7):
    if days < 1:
        raise ValueError("Rolling window must be positive")
    return [sum(values[max(0, i-days+1):i+1]) / min(days, i+1)
            for i in range(len(values))]


def heat_level(value):
    if value < 0:
        raise ValueError("Counts cannot be negative")
    return next(i for i, (upper, _) in enumerate(HEAT_BINS) if value <= upper)

