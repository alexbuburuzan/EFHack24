import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import os
import requests
from PIL import Image
from dotenv import load_dotenv

from quartz_solar_forecast.pydantic_models import PVSite

PREDICTION_TIME = datetime(2024, 12, 5, 0, 0, 0, tzinfo=timezone.utc).isoformat()
CURRENT_TIME = datetime(2024, 12, 5, 11, 0, 0, tzinfo=timezone.utc).isoformat()

# Load environment variables
load_dotenv()

if 'enphase_access_token' not in st.session_state:
    st.session_state.enphase_access_token = None
if 'enphase_system_id' not in st.session_state:
    st.session_state.enphase_system_id = None
if 'redirect_url' not in st.session_state:
    st.session_state.redirect_url = ""

# Set up the base URL for the FastAPI server
FASTAPI_BASE_URL = "http://localhost:8000"

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to logo.png
logo_path = os.path.join(script_dir, "logo.png")
im = Image.open(logo_path)

st.set_page_config(
    page_title="Open Source Quartz Solar Forecast | Open Climate Fix",
    layout="wide",
    page_icon=im,
)
st.title("☀️ Open Source Quartz Solar Forecast")

# In-memory database for solar panels
if 'solar_panels' not in st.session_state:
    st.session_state.solar_panels = pd.DataFrame(
        columns=['Name', 'Latitude', 'Longitude', 'Capacity (kWp)']
    )

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

# Main app logic
st.sidebar.header("PV Site Configuration")

latitude = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=51.75, step=0.01)
longitude = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-1.25, step=0.01)
capacity_kwp = st.sidebar.number_input("Capacity (kWp)", min_value=0.1, value=1.25, step=0.01)

# Manage Solar Panel Database
st.sidebar.subheader("Solar Panel Database")
if st.sidebar.button("Add to Database"):
    new_panel = {
        'Name': f"Site {len(st.session_state.solar_panels) + 1}",
        'Latitude': latitude,
        'Longitude': longitude,
        'Capacity (kWp)': capacity_kwp
    }
    st.session_state.solar_panels = pd.concat([st.session_state.solar_panels, pd.DataFrame([new_panel])], ignore_index=True)
    st.success(f"Added {new_panel['Name']} to the database!")

# Display Solar Panel Database
st.sidebar.subheader("Current Solar Panels")
st.sidebar.dataframe(st.session_state.solar_panels)

# Dropdown for site selection
st.sidebar.subheader("Select Site for Forecast")
if not st.session_state.solar_panels.empty:
    site_names = st.session_state.solar_panels['Name'].tolist()
    selected_site_name = st.sidebar.selectbox("Choose a site", site_names)
    selected_site = st.session_state.solar_panels[st.session_state.solar_panels['Name'] == selected_site_name].iloc[0]
else:
    selected_site = None
    st.sidebar.info("No sites available for selection. Add a site first.")

# Map Display
st.subheader("Map of Solar Panel Sites")
if not st.session_state.solar_panels.empty:
    map_data = st.session_state.solar_panels.rename(columns={"Latitude": "latitude", "Longitude": "longitude"})
    st.map(map_data[['latitude', 'longitude']])
else:
    st.info("No solar panel sites added yet. Add a site to see it on the map.")

# Forecast Logic
if st.sidebar.button("Run Forecast"):
    if selected_site is not None:
        site = PVSite(
            latitude=selected_site['Latitude'],
            longitude=selected_site['Longitude'],
            capacity_kwp=selected_site['Capacity (kWp)'],
            inverter_type=""
        )

        daily_forecast = make_api_request("/forecast/", method="POST", data={
            "site": site.dict(),
            "timestamp": PREDICTION_TIME,
        })
        current_forecast = make_api_request("/forecast/", method="POST", data={
            "site": site.dict(),
            "timestamp": CURRENT_TIME,
        })

        if daily_forecast and current_forecast:
            st.success("Forecast completed successfully!")

            # Display current timestamp
            st.subheader(f"Forecast generated at: {daily_forecast['timestamp']}")

            # Process and display predictions
            predictions = pd.DataFrame(daily_forecast['predictions'])
            predictions = predictions.iloc[:len(predictions)//2]

            # Plotting
            if 'power_kw' in predictions.columns:
                fig = px.line(
                    predictions.reset_index(),
                    x="index",
                    y="power_kw",
                    title="Forecasted Power Generation",
                    labels={"power_kw": "Power (kW)", "index": "Time"}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No forecast data available. Please check your inputs and try again.")
    else:
        st.error("No site selected for forecasting. Please add and select a site.")
