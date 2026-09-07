"""Generate reproducible proof-of-concept UCO station data for Klang Valley."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data" / "simulated_stations.csv"
DEFAULT_SEED = 42
DISCLAIMER = "Proof-of-concept simulation under stated assumptions."

# Approximate area centroids used only to create simulated station locations.
AREAS = [
    ("Kuala Lumpur City Centre", 3.1579, 101.7123),
    ("Bangsar", 3.1291, 101.6787),
    ("Cheras", 3.1073, 101.7254),
    ("Setapak", 3.1880, 101.7100),
    ("Kepong", 3.2140, 101.6350),
    ("Petaling Jaya", 3.1073, 101.6067),
    ("Subang Jaya", 3.0567, 101.5851),
    ("Shah Alam", 3.0738, 101.5183),
    ("Klang", 3.0449, 101.4456),
    ("Puchong", 3.0327, 101.6188),
    ("Seri Kembangan", 3.0278, 101.7065),
    ("Ampang", 3.1503, 101.7600),
    ("Gombak", 3.2520, 101.7030),
    ("Damansara", 3.1430, 101.6150),
    ("Mont Kiara", 3.1700, 101.6520),
    ("Bukit Jalil", 3.0580, 101.6910),
    ("Sunway", 3.0733, 101.6072),
    ("Kota Damansara", 3.1517, 101.5795),
    ("Cyberjaya", 2.9213, 101.6559),
    ("Putrajaya", 2.9264, 101.6964),
]


def _status(fill_rate_pct: float, days_to_full: float) -> str:
    if fill_rate_pct >= 90 or days_to_full <= 1:
        return "CRITICAL"
    if fill_rate_pct >= 80 or days_to_full <= 3:
        return "HIGH"
    if fill_rate_pct >= 65 or days_to_full <= 7:
        return "MEDIUM"
    return "LOW"


def generate_station_data(seed: int = DEFAULT_SEED, save: bool = True) -> pd.DataFrame:
    """Return 20 simulated stations and optionally save them to CSV.

    Priority score = 70% fill rate + 30% urgency, where urgency declines
    linearly from 100 at zero days remaining to 0 at eight days remaining.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    for index, (area, base_lat, base_lon) in enumerate(AREAS, start=1):
        capacity = int(rng.integers(300, 801))
        target_fill = float(rng.uniform(0.30, 0.981))
        current = round(capacity * target_fill, 1)
        daily_inflow = round(float(rng.uniform(5, 30)), 1)
        remaining = round(capacity - current, 1)
        fill_rate = current / capacity * 100
        days_to_full = remaining / daily_inflow
        urgency_score = float(np.clip(100 - 12.5 * days_to_full, 0, 100))
        priority_score = float(np.clip(0.7 * fill_rate + 0.3 * urgency_score, 0, 100))
        status = _status(fill_rate, days_to_full)

        rows.append(
            {
                "station_id": index,
                "station_name": f"{area} UCO Hub",
                "latitude": round(base_lat + float(rng.normal(0, 0.004)), 6),
                "longitude": round(base_lon + float(rng.normal(0, 0.004)), 6),
                "capacity_kg": capacity,
                "current_uco_kg": current,
                "daily_inflow_kg": daily_inflow,
                "fill_rate_pct": round(fill_rate, 1),
                "remaining_capacity_kg": remaining,
                "days_to_full": round(days_to_full, 1),
                "priority_score": round(priority_score, 1),
                "priority_status": status,
                "collection_required": status in {"HIGH", "CRITICAL"},
            }
        )

    stations = pd.DataFrame(rows)
    if save:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        stations.to_csv(DATA_PATH, index=False)
    return stations


def print_summary(stations: pd.DataFrame) -> None:
    print(DISCLAIMER)
    print(f"Stations: {len(stations)}")
    print(f"Total UCO stored: {stations['current_uco_kg'].sum():,.1f} kg")
    print(f"Requiring collection: {int(stations['collection_required'].sum())}")
    print(f"Average fill level: {stations['fill_rate_pct'].mean():.1f}%")
    print(f"Critical stations: {(stations['priority_status'] == 'CRITICAL').sum()}")
    print(f"Saved: {DATA_PATH}")


if __name__ == "__main__":
    print_summary(generate_station_data())
