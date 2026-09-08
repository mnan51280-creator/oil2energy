"""Competition-focused Streamlit dashboard for the OIL2ENERGY prototype."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from optimization import DEPOT, EMISSION_FACTOR_KG_CO2_PER_KM, calculate_scenario_comparison, run_route_optimization
from simulation import DEFAULT_SEED, generate_station_data


st.set_page_config(page_title="OIL2ENERGY", page_icon="♻️", layout="wide")
STATUS_COLORS = {"LOW": "#22c55e", "MEDIUM": "#eab308", "HIGH": "#f97316", "CRITICAL": "#dc2626"}
DISCLAIMER = "Simulation results are generated under stated assumptions and do not represent measured field performance."


def apply_styles() -> None:
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #f4fbf7 0%, #ffffff 32%); }
    [data-testid="stMetric"] { background: white; border: 1px solid #dcebe3; border-radius: 14px; padding: 16px; box-shadow: 0 3px 14px rgba(15, 64, 43, .05); }
    .hero { padding: 1.2rem 1.4rem; background: linear-gradient(110deg, #064e3b, #0f766e); color: white; border-radius: 18px; margin-bottom: 1rem; }
    .hero h1 { margin: 0; font-size: 2.2rem; }
    .hero p { margin: .3rem 0 0; color: #d1fae5; }
    .disclaimer { color: #475569; background: #f8fafc; border-left: 4px solid #10b981; padding: .65rem 1rem; border-radius: 6px; font-size: .9rem; }
    .value { font-size: 1.08rem; font-weight: 600; color: #134e4a; padding: .8rem 0 .25rem; }
    .flow { display: flex; align-items: center; justify-content: center; gap: .45rem; flex-wrap: wrap; margin: .8rem 0 1.2rem; }
    .flow-step { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; border-radius: 10px; padding: .55rem .75rem; font-size: .78rem; font-weight: 700; text-align: center; }
    .flow-arrow { color: #0f766e; font-weight: 800; }
    .scenario-card { min-height: 205px; background: white; border: 1px solid #dcebe3; border-top: 5px solid #0f766e; border-radius: 14px; padding: 1rem 1.05rem; box-shadow: 0 3px 14px rgba(15, 64, 43, .05); }
    .scenario-card h3 { color: #064e3b; margin: 0 0 .65rem; font-size: 1.05rem; }
    .scenario-card .distance { color: #0f766e; font-size: 1.35rem; font-weight: 750; margin-top: .7rem; }
    .scenario-card .effect { color: #475569; font-size: .86rem; margin-top: .35rem; }
    </style>
    """, unsafe_allow_html=True)


def load_model(seed: int) -> tuple[pd.DataFrame, dict, pd.DataFrame, object, pd.DataFrame]:
    stations = generate_station_data(seed=seed, save=True)
    results, demo_selected, route_figure = run_route_optimization(stations, save=True)
    scenarios = calculate_scenario_comparison(stations)
    return stations, results, demo_selected, route_figure, scenarios


def station_map(stations: pd.DataFrame):
    plot_data = stations.copy()
    plot_data["marker_size"] = 9 + plot_data["fill_rate_pct"] / 10
    figure = px.scatter_map(
        plot_data, lat="latitude", lon="longitude", color="priority_status", size="marker_size",
        color_discrete_map=STATUS_COLORS, hover_name="station_name",
        hover_data={"fill_rate_pct": ":.1f", "current_uco_kg": ":.1f", "days_to_full": ":.1f", "marker_size": False, "latitude": False, "longitude": False},
        labels={"priority_status": "Status", "fill_rate_pct": "Fill %", "current_uco_kg": "UCO kg", "days_to_full": "Days to full"},
        zoom=8.5, center={"lat": 3.10, "lon": 101.64}, height=500,
    )
    figure.update_layout(map_style="open-street-map", margin={"l": 0, "r": 0, "t": 0, "b": 0}, legend_title_text="Simulated status")
    return figure


def percentage_reduction(start: float, end: float) -> float:
    return (start - end) / start * 100 if start else 0.0


apply_styles()
if "simulation_seed" not in st.session_state:
    st.session_state.simulation_seed = DEFAULT_SEED

with st.sidebar:
    st.header("Prototype Information")
    st.caption("Operational priority selection: HIGH and CRITICAL stations only.")
    st.caption(f"Illustrative emission factor: {EMISSION_FACTOR_KG_CO2_PER_KM:.2f} kg CO₂/km")
    with st.expander("Demo Controls"):
        st.caption("Alternative runs demonstrate model behaviour under different simulated station conditions.")
        if st.button("Run Alternative Simulation", width="stretch"):
            st.session_state.simulation_seed += 1
            st.rerun()

stations, results, demo_selected, route_figure, scenarios = load_model(st.session_state.simulation_seed)
scenario_a, scenario_b, scenario_c = (scenarios.iloc[index] for index in range(3))
ab_reduction = percentage_reduction(scenario_a["simulated_route_distance_km"], scenario_b["simulated_route_distance_km"])
bc_reduction = percentage_reduction(scenario_b["simulated_route_distance_km"], scenario_c["simulated_route_distance_km"])
ac_reduction = percentage_reduction(scenario_a["simulated_route_distance_km"], scenario_c["simulated_route_distance_km"])
bc_co2_avoided = scenario_b["estimated_co2_kg"] - scenario_c["estimated_co2_kg"]

st.markdown('<div class="hero"><h1>OIL2ENERGY</h1><p>Smart UCO Collection Intelligence Platform</p><p><b>Proof-of-Concept Simulation | Klang Valley</b></p></div>', unsafe_allow_html=True)
st.markdown('<div class="disclaimer"><b>Proof-of-concept:</b> Simulation result under stated assumptions; not measured field performance.</div>', unsafe_allow_html=True)
st.markdown('<div class="value">OIL2ENERGY does not only optimise how the collection vehicle travels. It first determines which stations require collection, then determines how those stations should be visited.</div>', unsafe_allow_html=True)
st.markdown("""
<div class="flow">
  <div class="flow-step">SMART UCO STATION</div><div class="flow-arrow">→</div>
  <div class="flow-step">FILL / WEIGHT / LOCATION</div><div class="flow-arrow">→</div>
  <div class="flow-step">COLLECTION DECISION</div><div class="flow-arrow">→</div>
  <div class="flow-step">ROUTE DECISION</div><div class="flow-arrow">→</div>
  <div class="flow-step">RESOURCE RECOVERY</div>
</div>
""", unsafe_allow_html=True)

headline = st.columns(4)
headline[0].metric("UCO Ready", f"{scenario_c['uco_collected_kg']:,.1f} kg", help="UCO ready for recovery at operational HIGH and CRITICAL stations")
headline[1].metric("Priority Stations", int(scenario_c["stations_visited"]), help="Operational HIGH and CRITICAL stations selected for collection")
headline[2].metric("Route Reduction", f"{bc_reduction:.1f}%", help="Simulation result: Scenario B versus C for the same priority stations")
headline[3].metric(
    "Estimated CO₂ Reduction",
    f"{bc_co2_avoided:.2f} kg",
    help=(
        "Estimated operational CO₂ emissions reduction from Scenario B to Scenario C, "
        "calculated using an illustrative factor of 0.27 kg CO₂/km. "
        "This is a simulation-based estimate, not measured field emissions."
    ),
)

st.caption(
    "Headline routing indicators compare the same priority stations: "
    "fixed sequence (B) versus heuristic sequence (C)."
)
st.header("1 — Three-Scenario Intelligence Comparison")
st.caption("Simulation Result. A→B isolates the station-selection layer; B→C isolates the visit-sequence layer. Non-priority stations are deferred, not treated as recovered UCO.")
scenario_cards = st.columns(3)
scenario_cards[0].markdown(f"""
<div class="scenario-card">
  <h3>A — CONVENTIONAL</h3>
  <b>{int(scenario_a['stations_visited'])} stations</b><br>
  Fixed collection sequence
  <div class="distance">{scenario_a['simulated_route_distance_km']:.1f} km</div>
  <div class="effect">Geographic-distance proxy</div>
</div>
""", unsafe_allow_html=True)
scenario_cards[1].markdown(f"""
<div class="scenario-card">
  <h3>B — SMART COLLECTION</h3>
  <b>{int(scenario_b['stations_visited'])} priority stations</b><br>
  Non-priority stations deferred
  <div class="distance">{scenario_b['simulated_route_distance_km']:.1f} km</div>
  <div class="effect">Simulation result: {ab_reduction:.1f}% reduction through collection selection (A→B)</div>
</div>
""", unsafe_allow_html=True)
scenario_cards[2].markdown(f"""
<div class="scenario-card">
  <h3>C — OIL2ENERGY</h3>
  <b>{int(scenario_c['stations_visited'])} priority stations</b><br>
  Priority selection + heuristic sequence
  <div class="distance">{scenario_c['simulated_route_distance_km']:.1f} km</div>
  <div class="effect">Simulation result: {bc_reduction:.1f}% additional route reduction (B→C)</div>
</div>
""", unsafe_allow_html=True)
display_scenarios = scenarios.rename(columns={
    "scenario": "Scenario", "description": "Collection logic", "stations_visited": "Stations visited",
    "simulated_route_distance_km": "Simulated route distance (km)", "estimated_co2_kg": "Estimated CO₂ (kg)",
    "uco_collected_kg": "UCO Ready for Collection (kg)", "uco_kg_per_km": "UCO (kg/km)",
})
st.caption("UCO ready for collection represents material scheduled in each simulated scenario. Non-priority station material is deferred. UCO kg/km is most directly comparable between B and C because they visit the same stations.")
st.dataframe(display_scenarios, hide_index=True, width="stretch")
chart = px.bar(
    scenarios, x="scenario", y="simulated_route_distance_km", color="scenario", text="simulated_route_distance_km",
    labels={"scenario": "", "simulated_route_distance_km": "Simulated route distance (km)"},
    color_discrete_sequence=["#64748b", "#14b8a6", "#047857"],
)
chart.update_traces(texttemplate="%{text:.1f} km", textposition="outside")
chart.update_layout(showlegend=False, height=390, margin={"l": 10, "r": 10, "t": 20, "b": 10})
st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
layers = st.columns(3)
layers[0].metric("Simulation Result — A→B Distance Reduction", f"{ab_reduction:.1f}%", help="Benefit from operational priority selection; collection scope differs")
layers[1].metric("Simulation Result — B→C Distance Reduction", f"{bc_reduction:.1f}%", help="Additional benefit from heuristic sequence optimisation for the same priority stations")
layers[2].metric("Simulation Result — Overall A→C Reduction", f"{ac_reduction:.1f}%", help="Includes both operational station selection and heuristic visit sequencing")
st.caption("Overall A→C reduction includes both avoiding unnecessary station visits and improving the route sequence. It is not presented as a route-only effect.")

st.header("2 — Simulated Station Network")
network = st.columns(4)
network[0].metric("Total Simulated Stations", len(stations))
network[1].metric("HIGH / CRITICAL", int(stations["collection_required"].sum()))
network[2].metric("Critical Stations", int((stations["priority_status"] == "CRITICAL").sum()))
network[3].metric("Average Fill", f"{stations['fill_rate_pct'].mean():.1f}%")
st.plotly_chart(station_map(stations), width="stretch", config={"displayModeBar": False})

st.header("3 — Priority Collection Decision")
st.subheader("Today's Operational Queue")
queue = stations[stations["collection_required"]].sort_values(["priority_score", "days_to_full"], ascending=[False, True]).copy()
queue.insert(0, "rank", range(1, len(queue) + 1))
queue["operational_message"] = queue["priority_status"].map({
    "CRITICAL": "Immediate collection recommended", "HIGH": "Priority collection recommended",
    "MEDIUM": "Monitor closely", "LOW": "Routine monitoring",
})
queue = queue.rename(columns={
    "rank": "Rank", "station_name": "Station", "priority_status": "Status", "fill_rate_pct": "Fill %",
    "days_to_full": "Days to Full", "current_uco_kg": "Estimated UCO kg", "operational_message": "Action",
})
st.dataframe(queue[["Rank", "Station", "Status", "Fill %", "Days to Full", "Estimated UCO kg", "Action"]], hide_index=True, width="stretch")

with st.expander("View All Simulated Stations"):
    filter_left, filter_right = st.columns(2)
    statuses = filter_left.multiselect("Priority status", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], default=["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    requirement = filter_right.selectbox("Collection required", ["All", "Yes", "No"])
    filtered = stations[stations["priority_status"].isin(statuses)].copy()
    if requirement != "All":
        filtered = filtered[filtered["collection_required"] == (requirement == "Yes")]
    priority_table = filtered.sort_values("priority_score", ascending=False).rename(columns={
        "station_name": "Station", "fill_rate_pct": "Fill %", "days_to_full": "Days to Full",
        "priority_score": "Priority Score", "priority_status": "Status", "collection_required": "Collection Required",
    })
    st.dataframe(priority_table[["Station", "Fill %", "Days to Full", "Priority Score", "Status", "Collection Required"]], hide_index=True, width="stretch")

st.header("4 — Geographic-Distance Route Demonstration")
st.caption("Nearest-neighbour + 2-opt routing heuristic. The interactive demonstration uses at least five stations for visibility; analytical Scenarios B and C use operational priority selection only, with no forced minimum.")
fixed_demo, optimized_demo = st.columns(2)
with fixed_demo:
    st.subheader("Demo Fixed Sequence")
    a, b, c = st.columns(3)
    a.metric("Simulated Distance", f"{results['baseline_distance_km']:.1f} km")
    b.metric("Estimated CO₂", f"{results['baseline_co2_kg']:.1f} kg")
    c.metric("UCO per km", f"{results['baseline_kg_per_km']:.1f} kg/km")
with optimized_demo:
    st.subheader("Demo Heuristic Sequence")
    a, b, c = st.columns(3)
    a.metric("Simulated Distance", f"{results['optimized_distance_km']:.1f} km")
    b.metric("Estimated CO₂", f"{results['optimized_co2_kg']:.1f} kg")
    c.metric("UCO per km", f"{results['optimized_kg_per_km']:.1f} kg/km")
st.caption("UCO kg/km is comparable here because both routes visit the same demo-selected stations.")
st.info("Map lines show geographic-distance connections, not driven road paths.")
st.plotly_chart(route_figure, width="stretch", config={"displayModeBar": False})

st.header("5 — Methodology")
st.markdown("""
1. Simulated smart stations report fill, estimated weight and location.
2. Priority scoring identifies stations at risk of reaching capacity.
3. Operational priority selection chooses HIGH and CRITICAL stations.
4. A nearest-neighbour route is generated for those stations.
5. 2-opt heuristically improves the visit sequence.
6. Simulation KPIs compare station-selection and route-sequence effects separately.

This prototype demonstrates technical potential. Real deployment requires calibrated sensors and pilot validation using actual UCO generation, road-network, traffic, vehicle-capacity and operational data.
""")
with st.expander("Simulation Assumptions & Prototype Boundaries"):
    st.markdown(f"""
    - 20 simulated Klang Valley stations
    - Station capacity range: 300–800 kg
    - Simulated current fill: approximately 30–98% of capacity
    - Simulated daily UCO inflow: 5–30 kg/day
    - Priority rules: CRITICAL at ≥90% fill or ≤1 day to full; HIGH at ≥80% or ≤3 days; MEDIUM at ≥65% or ≤7 days; otherwise LOW
    - Priority score: 70% fill level + 30% urgency
    - Urgency horizon: score declines from 100 at zero days to 0 at eight days
    - Depot location: {DEPOT['latitude']}, {DEPOT['longitude']} near central Kuala Lumpur
    - Haversine geographic great-circle distance
    - Nearest-neighbour + 2-opt routing heuristic
    - Illustrative emission factor: {EMISSION_FACTOR_KG_CO2_PER_KM:.2f} kg CO₂/km
    - Traffic is not modelled
    - Vehicle capacity is not modelled
    - Station data are not live IoT measurements
    - Real deployment requires sensor calibration and pilot validation

    Geographic great-circle distance is used as a proof-of-concept routing proxy. Live road-network distance and traffic are not modelled.
    """)
