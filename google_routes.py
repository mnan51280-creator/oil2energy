import os
import re
from typing import List, Tuple

import requests
import streamlit as st


ROUTES_MATRIX_URL = (
    "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
)


def get_google_routes_api_key() -> str:
    """
    Read the Google Routes API key safely.

    Priority:
    1. Environment variable
    2. Streamlit secrets
    """
    api_key = os.getenv("GOOGLE_ROUTES_API_KEY")

    if api_key:
        return api_key

    try:
        return st.secrets["GOOGLE_ROUTES_API_KEY"]
    except Exception as exc:
        raise RuntimeError(
            "GOOGLE_ROUTES_API_KEY was not found. "
            "Add it to .streamlit/secrets.toml or Streamlit Cloud Secrets."
        ) from exc


def _duration_to_seconds(duration: str) -> float:
    """
    Convert Google duration strings such as '1234s'
    to seconds.
    """
    if not duration:
        return 0.0

    match = re.match(r"^([0-9.]+)s$", duration)

    if not match:
        raise ValueError(f"Unexpected Google duration format: {duration}")

    return float(match.group(1))


def build_driving_matrices(
    coordinates: List[Tuple[float, float]],
) -> Tuple[List[List[float]], List[List[float]]]:
    """
    Build road-network driving distance and duration matrices.

    Parameters
    ----------
    coordinates:
        List of (latitude, longitude) tuples.

    Returns
    -------
    distance_matrix_km:
        NxN matrix of road driving distances in kilometres.

    duration_matrix_min:
        NxN matrix of estimated driving times in minutes.

    Notes
    -----
    - Uses Google Routes API ComputeRouteMatrix.
    - Uses DRIVE mode.
    - Uses TRAFFIC_UNAWARE so results are more reproducible
      for simulation / competition evaluation.
    - Road distances are directional:
      A -> B may differ from B -> A.
    """

    if not coordinates:
        raise ValueError("coordinates cannot be empty.")

    api_key = get_google_routes_api_key()

    origins = []
    destinations = []

    for latitude, longitude in coordinates:
        waypoint = {
            "waypoint": {
                "location": {
                    "latLng": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                    }
                }
            }
        }

        origins.append(waypoint)
        destinations.append(waypoint)

    payload = {
        "origins": origins,
        "destinations": destinations,
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "originIndex,"
            "destinationIndex,"
            "status,"
            "condition,"
            "distanceMeters,"
            "duration"
        ),
    }

    response = requests.post(
        ROUTES_MATRIX_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Google Routes API request failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    elements = response.json()

    n = len(coordinates)

    distance_matrix_km = [
        [0.0 for _ in range(n)]
        for _ in range(n)
    ]

    duration_matrix_min = [
        [0.0 for _ in range(n)]
        for _ in range(n)
    ]

    found_pairs = set()

    for element in elements:
        origin_index = element.get("originIndex")
        destination_index = element.get("destinationIndex")

        if origin_index is None or destination_index is None:
            continue

        if origin_index == destination_index:
            distance_matrix_km[origin_index][destination_index] = 0.0
            duration_matrix_min[origin_index][destination_index] = 0.0
            found_pairs.add((origin_index, destination_index))
            continue

        condition = element.get("condition")

        if condition != "ROUTE_EXISTS":
            raise RuntimeError(
                "Google Routes API could not find a road route "
                f"from point {origin_index} to point {destination_index}. "
                f"Condition: {condition}"
            )

        distance_meters = element.get("distanceMeters")
        duration = element.get("duration")

        if distance_meters is None or duration is None:
            raise RuntimeError(
                "Google Routes API returned an incomplete matrix element "
                f"for {origin_index} -> {destination_index}."
            )

        distance_matrix_km[origin_index][destination_index] = (
            float(distance_meters) / 1000.0
        )

        duration_matrix_min[origin_index][destination_index] = (
            _duration_to_seconds(duration) / 60.0
        )

        found_pairs.add((origin_index, destination_index))

    expected_pairs = {
        (i, j)
        for i in range(n)
        for j in range(n)
    }

    missing_pairs = expected_pairs - found_pairs

    # Some APIs may omit explicit self-to-self entries.
    missing_non_diagonal = {
        (i, j)
        for i, j in missing_pairs
        if i != j
    }

    if missing_non_diagonal:
        raise RuntimeError(
            "Google Routes API returned an incomplete matrix. "
            f"Missing pairs: {sorted(missing_non_diagonal)}"
        )

    return distance_matrix_km, duration_matrix_min


def route_total(
    route: List[int],
    matrix: List[List[float]],
) -> float:
    """
    Sum the cost of a route using a directional matrix.

    Example:
        route = [0, 2, 1, 3, 0]
    """

    if len(route) < 2:
        return 0.0

    total = 0.0

    for current_index, next_index in zip(route[:-1], route[1:]):
        total += matrix[current_index][next_index]

    return total
