"""Heuristic route optimisation for the OIL2ENERGY proof of concept."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import pandas as pd
import plotly.graph_objects as go

from simulation import DATA_PATH, DISCLAIMER, generate_station_data


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
DEPOT = {"station_id": 0, "station_name": "Central UCO Depot", "latitude": 3.1390, "longitude": 101.6869}

# Assumed illustrative vehicle emission factor; not a measured fleet value.
EMISSION_FACTOR_KG_CO2_PER_KM = 0.27


def haversine_km(a: dict | pd.Series, b: dict | pd.Series) -> float:
    """Calculate great-circle distance between two latitude/longitude points."""
    radius_km = 6371.0088
    lat1, lon1 = math.radians(float(a["latitude"])), math.radians(float(a["longitude"]))
    lat2, lon2 = math.radians(float(b["latitude"])), math.radians(float(b["longitude"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.asin(math.sqrt(h))


def operational_priority_selection(stations: pd.DataFrame) -> pd.DataFrame:
    """Select only HIGH and CRITICAL stations for analytical scenarios."""
    return (
        stations[stations["priority_status"].isin(["HIGH", "CRITICAL"])]
        .copy()
        .sort_values("station_id")
        .reset_index(drop=True)
    )


def demo_selection(stations: pd.DataFrame, minimum: int = 5) -> pd.DataFrame:
    """Select priority stations, adding high-ranked stations only for the demo map."""
    selected = operational_priority_selection(stations)
    if len(selected) < minimum:
        candidates = stations[~stations.index.isin(selected.index)].sort_values("priority_score", ascending=False)
        # MEDIUM stations are considered first; LOW is a safe fallback for unusual custom data.
        medium = candidates[candidates["priority_status"] == "MEDIUM"]
        selected = pd.concat([selected, medium.head(minimum - len(selected))])
        if len(selected) < minimum:
            remaining = candidates[~candidates.index.isin(selected.index)]
            selected = pd.concat([selected, remaining.head(minimum - len(selected))])
    return selected.drop_duplicates("station_id").sort_values("station_id").reset_index(drop=True)


def select_stations(stations: pd.DataFrame, minimum: int = 5) -> pd.DataFrame:
    """Backward-compatible alias for the minimum-five interactive demo selection."""
    return demo_selection(stations, minimum)


def route_distance(route: Sequence[dict | pd.Series]) -> float:
    return sum(haversine_km(route[i], route[i + 1]) for i in range(len(route) - 1))


def nearest_neighbour(stations: pd.DataFrame) -> list[dict]:
    remaining = stations.to_dict("records")
    route: list[dict] = [DEPOT.copy()]
    while remaining:
        nearest = min(remaining, key=lambda station: haversine_km(route[-1], station))
        route.append(nearest)
        remaining.remove(nearest)
    route.append(DEPOT.copy())
    return route


def two_opt(route: list[dict]) -> list[dict]:
    """Improve a closed route by repeatedly reversing beneficial segments."""
    best = route[:]
    improved = True
    while improved:
        improved = False
        best_distance = route_distance(best)
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                candidate_distance = route_distance(candidate)
                if candidate_distance + 1e-9 < best_distance:
                    best, best_distance = candidate, candidate_distance
                    improved = True
        # Continue until a complete pass makes no improvement.
    return best


def scenario_metrics(name: str, description: str, route: list[dict], stations: pd.DataFrame) -> dict:
    """Calculate claim-safe metrics for one simulated collection scenario."""
    distance = route_distance(route)
    uco = float(stations["current_uco_kg"].sum())
    return {
        "scenario": name,
        "description": description,
        "stations_visited": len(stations),
        "simulated_route_distance_km": round(distance, 2),
        "estimated_co2_kg": round(distance * EMISSION_FACTOR_KG_CO2_PER_KM, 2),
        "uco_collected_kg": round(uco, 1),
        "uco_kg_per_km": round(uco / distance, 2) if distance else 0.0,
    }


def calculate_scenario_comparison(stations: pd.DataFrame) -> pd.DataFrame:
    """Compare station selection and visit-sequence intelligence separately."""
    all_stations = stations.sort_values("station_id").reset_index(drop=True)
    priority_stations = operational_priority_selection(stations)

    scenario_a_route = [DEPOT.copy(), *all_stations.to_dict("records"), DEPOT.copy()]
    scenario_b_route = [DEPOT.copy(), *priority_stations.to_dict("records"), DEPOT.copy()]
    scenario_c_route = two_opt(nearest_neighbour(priority_stations))

    rows = [
        scenario_metrics(
            "A — Conventional",
            "All stations + fixed collection sequence",
            scenario_a_route,
            all_stations,
        ),
        scenario_metrics(
            "B — Smart Collection",
            "Operational priority stations only + fixed sequence",
            scenario_b_route,
            priority_stations,
        ),
        scenario_metrics(
            "C — OIL2ENERGY",
            "Operational priority stations + heuristic route optimisation",
            scenario_c_route,
            priority_stations,
        ),
    ]
    return pd.DataFrame(rows)


def create_route_map(selected: pd.DataFrame, baseline: list[dict], optimized: list[dict]) -> go.Figure:
    colors = {"MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#dc2626"}
    figure = go.Figure()
    figure.add_trace(go.Scattermap(
        lat=[point["latitude"] for point in baseline], lon=[point["longitude"] for point in baseline],
        mode="lines", name="Demo selection — fixed sequence", line={"width": 2, "color": "#94a3b8"},
        hoverinfo="skip",
    ))
    figure.add_trace(go.Scattermap(
        lat=[point["latitude"] for point in optimized], lon=[point["longitude"] for point in optimized],
        mode="lines", name="Demo selection — heuristic sequence", line={"width": 4, "color": "#059669"},
        hoverinfo="skip",
    ))
    for status in ["MEDIUM", "HIGH", "CRITICAL"]:
        subset = selected[selected["priority_status"] == status]
        if subset.empty:
            continue
        figure.add_trace(go.Scattermap(
            lat=subset["latitude"], lon=subset["longitude"], mode="markers", name=status.title(),
            marker={"size": 12, "color": colors[status]},
            text=subset["station_name"],
            customdata=subset[["fill_rate_pct", "current_uco_kg", "days_to_full"]],
            hovertemplate="<b>%{text}</b><br>Fill: %{customdata[0]:.1f}%<br>UCO: %{customdata[1]:.1f} kg<br>Days to full: %{customdata[2]:.1f}<extra></extra>",
        ))
    figure.add_trace(go.Scattermap(
        lat=[DEPOT["latitude"]], lon=[DEPOT["longitude"]], mode="markers", name="Depot",
        marker={"size": 16, "color": "#0f172a", "symbol": "circle"}, text=[DEPOT["station_name"]],
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))
    figure.update_layout(
        map={"style": "open-street-map", "center": {"lat": 3.10, "lon": 101.64}, "zoom": 8.7},
        margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=560,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "center", "x": 0.5},
    )
    return figure


def run_route_optimization(stations: pd.DataFrame | None = None, save: bool = True) -> tuple[dict, pd.DataFrame, go.Figure]:
    """Run the interactive demo route plus the three analytical scenarios."""
    if stations is None:
        if not DATA_PATH.exists():
            stations = generate_station_data()
        else:
            stations = pd.read_csv(DATA_PATH)
    # Minimum-five selection applies only to the interactive route demonstration.
    selected = demo_selection(stations)
    station_records = selected.sort_values("station_id").to_dict("records")
    baseline = [DEPOT.copy(), *station_records, DEPOT.copy()]
    optimized = two_opt(nearest_neighbour(selected))

    baseline_distance = route_distance(baseline)
    optimized_distance = route_distance(optimized)
    total_uco = float(selected["current_uco_kg"].sum())
    saved = baseline_distance - optimized_distance
    results = {
        "baseline_distance_km": round(baseline_distance, 2),
        "optimized_distance_km": round(optimized_distance, 2),
        "distance_saved_km": round(saved, 2),
        "distance_reduction_pct": round(saved / baseline_distance * 100, 1) if baseline_distance else 0.0,
        "total_uco_collected_kg": round(total_uco, 1),
        "baseline_kg_per_km": round(total_uco / baseline_distance, 2) if baseline_distance else 0.0,
        "optimized_kg_per_km": round(total_uco / optimized_distance, 2) if optimized_distance else 0.0,
        "number_of_stations_visited": len(selected),
        "baseline_co2_kg": round(baseline_distance * EMISSION_FACTOR_KG_CO2_PER_KM, 2),
        "optimized_co2_kg": round(optimized_distance * EMISSION_FACTOR_KG_CO2_PER_KM, 2),
        "co2_avoided_kg": round(saved * EMISSION_FACTOR_KG_CO2_PER_KM, 2),
        "stations_visited": [point["station_name"] for point in optimized[1:-1]],
    }
    route_rows = []
    for order, point in enumerate(optimized):
        route_rows.append({
            "visit_order": order,
            "station_id": int(point["station_id"]),
            "station_name": point["station_name"],
            "latitude": point["latitude"],
            "longitude": point["longitude"],
        })
    optimized_route = pd.DataFrame(route_rows)
    figure = create_route_map(selected, baseline, optimized)
    scenarios = calculate_scenario_comparison(stations)

    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([results]).to_csv(OUTPUT_DIR / "route_results.csv", index=False)
        scenarios.to_csv(OUTPUT_DIR / "scenario_comparison.csv", index=False)
        optimized_route.to_csv(OUTPUT_DIR / "optimized_route.csv", index=False)
        with (OUTPUT_DIR / "simulation_results.json").open("w", encoding="utf-8") as file:
            json.dump(results, file, indent=2)
        figure.write_html(OUTPUT_DIR / "route_map.html", include_plotlyjs="cdn")
    return results, selected, figure


def print_summary(results: dict) -> None:
    print(DISCLAIMER)
    print("Heuristic route optimisation: nearest-neighbour + 2-opt; no global optimum is established.")
    print(f"Stations visited: {results['number_of_stations_visited']}")
    print(f"Demo fixed-sequence geographic distance: {results['baseline_distance_km']:.2f} km")
    print(f"Demo heuristic geographic distance: {results['optimized_distance_km']:.2f} km")
    print(f"Simulation result — distance reduction: {results['distance_reduction_pct']:.1f}%")
    print(f"Estimated CO2 avoided: {results['co2_avoided_kg']:.2f} kg")
    print(f"UCO collected: {results['total_uco_collected_kg']:.1f} kg")
    print(f"Saved outputs to: {OUTPUT_DIR}")


if __name__ == "__main__":
    print_summary(run_route_optimization()[0])
