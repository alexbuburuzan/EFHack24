import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import os
import plotly.graph_objects as go
import requests
from PIL import Image
from dotenv import load_dotenv

from quartz_solar_forecast.pydantic_models import PVSite

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
    page_title="EFHack24 submission powered by Open Climate Fix",
    layout="wide",
    page_icon=im,
)
st.title("☀️ Open Source Quartz Solar Forecast")

if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime(2024, 7, 3, 11, 45, tzinfo=timezone.utc)

if 'prediction_time' not in st.session_state:
    st.session_state.prediction_time = st.session_state.current_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

# Sidebar inputs for selecting CURRENT_TIME
st.sidebar.subheader("Select Current Time")
selected_date = st.sidebar.date_input("Select a date", value=st.session_state.current_time.date())
selected_time = st.sidebar.time_input("Select a time", value=st.session_state.current_time.time())

# Update CURRENT_TIME based on user input
new_current_time = datetime.combine(selected_date, selected_time).replace(tzinfo=timezone.utc)
if new_current_time != st.session_state.current_time:
    st.session_state.current_time = new_current_time
    # Update PREDICTION_TIME to the morning of the selected CURRENT_TIME
    st.session_state.prediction_time = new_current_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

# Display current and prediction times
CURRENT_TIME = st.session_state.current_time.isoformat()
PREDICTION_TIME = st.session_state.prediction_time.isoformat()

st.sidebar.write(f"**Current Time:** {CURRENT_TIME}")
st.sidebar.write(f"**Prediction Time:** {PREDICTION_TIME}")

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

def valuegenerated(delta,price=0.1,buffer=0.05,fine=2.0,ev=0.2):
    if delta < -buffer:
        value = -(1+ev)*price*buffer+buffer*price+fine*price*(-delta-buffer)
    elif -buffer<delta<=0:
        value = -(buffer+delta)*(1+ev)*price + buffer*price
    else:
        value = price*buffer
    return value

# Main app logic
st.sidebar.header("PV Site Configuration")

latitude = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=51.75, step=0.01)
longitude = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-1.25, step=0.01)
capacity_kwp = st.sidebar.number_input("Capacity (kWp)", min_value=0.1, value=5000., step=0.01)

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
            st.subheader(f"Rolling forecast generated at: {current_forecast['timestamp']}")

            # Process and display predictions
            daily_forecast = pd.DataFrame(daily_forecast['predictions'])
            daily_forecast = daily_forecast.iloc[:len(daily_forecast)//2]
            current_forecast = pd.DataFrame(current_forecast['predictions'])
            current_forecast = current_forecast.iloc[:3]

            daily_predicted = daily_forecast.loc[current_forecast.index].power_kw.values
            current_predicted = current_forecast.power_kw.values

            area_daily = ((daily_predicted[0] + daily_predicted[1]) * 0.5 + (daily_predicted[1] + daily_predicted[2]) * 0.5) / 4
            area_current = ((current_predicted[0] + current_predicted[1]) * 0.5 + (current_predicted[1] + current_predicted[2]) * 0.5) / 4
            delta = area_current - area_daily
            st.write(f"Difference in power generation between current and forecasted: {delta:.2f} kWh")

            value = valuegenerated(delta)
            st.write(f"Value generated: £{value:.2f}")

            fig = go.Figure()

            # Add the first line
            fig.add_trace(
                go.Scatter(
                    x=daily_forecast.index,  # Ensure "index" exists
                    y=daily_forecast["power_kw"],  # Ensure "power_kw" exists
                    mode='lines',
                    name='Day forecast'
                )
            )

            # Add the second line
            fig.add_trace(
                go.Scatter(
                    x=current_forecast.index,  # Ensure "index" exists
                    y=current_forecast["power_kw"],  # Ensure "power_kw" exists
                    mode='markers+lines',
                    name='30min prediction',
                    line=dict(color='red'),  # Customize color if needed
                    marker=dict(size=8)
                )
            )

            # Customize the layout
            fig.update_layout(
                title="Energy gap between forecast and current prediction",
                xaxis_title="Time",
                yaxis_title="Power (kW)"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No forecast data available. Please check your inputs and try again.")
    else:
        st.error("No site selected for forecasting. Please add and select a site.")
