import numpy as np
import pandas as pd
import requests
import streamlit as st

# Set up the base URL for the FastAPI server
FASTAPI_BASE_URL = "http://localhost:8000"

def vehicle_selection(delta, dataset, battery_capacity_per_car=50, max_distance=20):
    """
    Allocate energy for V2G based on battery percentage and distance criteria.
    Returns a DataFrame of cars selected with initial and final energy allocations.
    """
    # Filter cars based on criteria
    valid_cars = dataset[
        (dataset["Battery_Percentage"] > 30) & 
        (dataset["Radius_from_Powerplant_km"] <= max_distance) & 
        (dataset["Trip_Scheduled"] == 0)
    ].copy()

    # Calculate battery energy (in kWh)
    valid_cars["Battery_Energy_kWh"] = (valid_cars["Battery_Percentage"] / 100) * battery_capacity_per_car

    # Calculate biases
    if delta < 0:  # Discharging energy
        valid_cars["Battery_Bias"] = np.exp((valid_cars["Battery_Percentage"] - 30) / 20) - 1
    else:  # Charging energy
        valid_cars["Battery_Bias"] = np.exp((100 - valid_cars["Battery_Percentage"]) / 20) - 1

    valid_cars["Distance_Multiplier"] = 1 - (valid_cars["Radius_from_Powerplant_km"] / max_distance)
    valid_cars["Distance_Multiplier"] = valid_cars["Distance_Multiplier"].clip(lower=0)
    valid_cars["Total_Bias"] = valid_cars["Battery_Bias"] * valid_cars["Distance_Multiplier"]

    # Normalize biases and allocate energy
    total_bias = valid_cars["Total_Bias"].sum()
    valid_cars["Energy_Contribution_kWh"] = (valid_cars["Total_Bias"] / total_bias) * abs(delta)

    # Clip allocation by capacity
    if delta < 0:  # Discharging
        # Can't discharge more than we have
        valid_cars["Energy_Contribution_kWh"] = valid_cars["Energy_Contribution_kWh"].clip(upper=valid_cars["Battery_Energy_kWh"])
        valid_cars["Final_Battery_Energy_kWh"] = valid_cars["Battery_Energy_kWh"] - valid_cars["Energy_Contribution_kWh"]
    else:  # Charging
        # Can't charge beyond full battery
        valid_cars["Energy_Contribution_kWh"] = valid_cars["Energy_Contribution_kWh"].clip(
            upper=battery_capacity_per_car - valid_cars["Battery_Energy_kWh"]
        )
        valid_cars["Final_Battery_Energy_kWh"] = valid_cars["Battery_Energy_kWh"] + valid_cars["Energy_Contribution_kWh"]

    valid_cars["Final_Battery_Percentage"] = (valid_cars["Final_Battery_Energy_kWh"] / battery_capacity_per_car) * 100


    result = valid_cars[
        ["Car_ID", "Battery_Percentage", "Energy_Contribution_kWh", "Final_Battery_Percentage", "Latitude", "Longitude"]
    ]

    return result, valid_cars

def generate_car_dataset(num_cars=1000, 
                         center_lat=51.7520, 
                         center_lon=-1.2577, 
                         min_radius_km=0.1, 
                         max_radius_km=40, 
                         min_battery=20, 
                         max_battery=100, 
                         trip_probability=0.1, 
                         random_seed=42):
    """
    Generate a dataset of cars around a specified central point (solar farm in Oxford).
    Each car has:
    - A unique Car_ID
    - Random battery percentage
    - Random distance (km) from the center within the given radius
    - Random position (latitude, longitude) approximated
    - Trip scheduled or not

    Returns:
        pd.DataFrame: A DataFrame with columns:
            Car_ID, Battery_Percentage, Radius_from_Powerplant_km, 
            Trip_Scheduled, Latitude, Longitude
    """
    np.random.seed(random_seed)

    # Generate Car IDs
    car_ids = [f"Car_{i+1}" for i in range(num_cars)]

    # Battery percentages (uniformly distributed)
    battery_percentages = np.random.uniform(min_battery, max_battery, size=num_cars)

    # Radius from power plant (km)
    radii = np.random.uniform(min_radius_km, max_radius_km, size=num_cars)

    # Trip scheduled or not
    # Probability that a car has a trip scheduled is trip_probability
    trips = np.random.choice([0, 1], size=num_cars, p=[1 - trip_probability, trip_probability])

    # Random angles for direction
    angles = np.random.uniform(0, 2 * np.pi, size=num_cars)

    # Approximate conversions:
    # 1 degree latitude = ~111 km
    # 1 degree longitude at given latitude = ~111 km * cos(latitude)
    lat_factor = 111.0
    lon_factor = 111.0 * np.cos(np.radians(center_lat))

    # Calculate latitude and longitude offsets
    lat_offsets = (radii * np.cos(angles)) / lat_factor
    lon_offsets = (radii * np.sin(angles)) / lon_factor

    # Final lat/long
    lats = center_lat + lat_offsets
    lons = center_lon + lon_offsets

    # Create DataFrame
    df = pd.DataFrame({
        "Car_ID": car_ids,
        "Battery_Percentage": battery_percentages,
        "Radius_from_Powerplant_km": radii,
        "Trip_Scheduled": trips,
        "Latitude": lats,
        "Longitude": lons
    })

    return df

def make_api_request(endpoint, method="GET", data=None):
    try:
        url = f"{FASTAPI_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {e}")
        return None
    

def valuegenerated(delta,price=0.1,buffer=0.05,fine=2.0,ev=0.2):
    if delta < -buffer:
        value = -(1+ev)*price*buffer+buffer*price+fine*price*(-delta-buffer)
    elif -buffer<delta<=0:
        value = -(buffer+delta)*(1+ev)*price + buffer*price
    else:
        value = price*buffer
    return value
    