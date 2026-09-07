# OIL2ENERGY

OIL2ENERGY is a fully runnable proof-of-concept simulation of a smart Used Cooking Oil (UCO) collection network in Klang Valley, Malaysia.

> **Proof-of-concept simulation under stated assumptions.** Demonstration results use simulated station data and do not represent measured field performance. Percentage improvements are simulation results and should not be interpreted as field performance.

## What the MVP demonstrates

- 20 simulated smart UCO stations with fill, inflow, capacity and location data
- transparent collection priority scoring and operational status
- operational selection of HIGH and CRITICAL stations
- a minimum five-stop selection used only for the interactive route demonstration
- three analytical scenarios separating station-selection and visit-sequence intelligence
- nearest-neighbour + 2-opt heuristic route optimisation
- estimated distance, UCO-per-kilometre and CO₂ indicators under stated assumptions
- an interactive Streamlit decision-support dashboard

OIL2ENERGY does not only optimise how the collection vehicle travels. It first determines which stations require collection, then determines how those stations should be visited.

The analytical comparison contains:

- **Scenario A — Conventional:** all 20 stations in fixed station-ID order
- **Scenario B — Smart Collection:** operational HIGH and CRITICAL stations in fixed station-ID order, with no forced minimum
- **Scenario C — OIL2ENERGY:** the same operational priority stations as Scenario B, using nearest-neighbour + 2-opt heuristic sequencing

The depot is set near central Kuala Lumpur at `3.1390, 101.6869`. Vehicle emissions use an assumed illustrative factor of `0.27 kg CO₂/km`; this is configurable in `optimization.py` and is not a measured fleet value. Geographic great-circle distance is used as a proof-of-concept routing proxy. Live road-network distance and traffic are not modelled.

## Setup and run

From this `oil2energy` directory:

```bash
pip install -r requirements.txt

python simulation.py

python optimization.py

streamlit run dashboard.py
```

The first command installs the four required Python packages. The next two commands generate station and route outputs. The dashboard also regenerates missing outputs automatically.

## Generated files

- `data/simulated_stations.csv`
- `outputs/route_results.csv`
- `outputs/scenario_comparison.csv`
- `outputs/optimized_route.csv`
- `outputs/simulation_results.json`
- `outputs/route_map.html`

The default presentation uses random seed `42` for reproducibility. The dashboard's **Run Alternative Simulation** control explicitly advances the seed and refreshes the simulated station and route results.

## Method and limitations

Priority score is calculated as `0.7 × fill rate + 0.3 × urgency score`. The urgency score declines linearly from 100 at zero days remaining to 0 at eight days remaining. Status thresholds then identify LOW, MEDIUM, HIGH and CRITICAL stations.

The route is **heuristically optimised**; the method does not establish a global optimum. It starts with nearest neighbour and applies 2-opt improvements. Scenario A→B reflects a change in collection scope, while Scenario B→C compares visit sequences for the same operational priority stations. Results are simulation results under stated assumptions.

Traffic and vehicle capacity are not modelled, and station data are not live IoT measurements. This prototype demonstrates technical potential. Real deployment requires sensor calibration and pilot validation using actual UCO generation, road-network distance, traffic, service time, vehicle capacity, fleet emissions and operational data.
