import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import os
import plotly.graph_objects as go
import requests
from PIL import Image
from dotenv import load_dotenv
from utils import *
import pydeck as pdk
import time

from quartz_solar_forecast.pydantic_models import PVSite

# Load environment variables
load_dotenv()

if 'enphase_access_token' not in st.session_state:
    st.session_state.enphase_access_token = None
if 'enphase_system_id' not in st.session_state:
    st.session_state.enphase_system_id = None
if 'redirect_url' not in st.session_state:
    st.session_state.redirect_url = ""
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime(2024, 7, 3, 11, 45, tzinfo=timezone.utc)
if 'prediction_time' not in st.session_state:
    st.session_state.prediction_time = st.session_state.current_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
if 'cars_df' not in st.session_state:
    st.session_state.cars_df = generate_car_dataset()
if 'solar_panels' not in st.session_state:
    st.session_state.solar_panels = pd.DataFrame(
        columns=['Name', 'Latitude', 'Longitude', 'Capacity (kWp)']
    )

# Set up the base URL for the FastAPI server
FASTAPI_BASE_URL = "http://localhost:8000"

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="EFHack24 submission",
    layout="wide",
)
st.title("Stabl")

# Sidebar inputs for selecting CURRENT_TIME
st.sidebar.subheader("Select Current Time")
selected_date = st.sidebar.date_input("Select a date", value=st.session_state.current_time.date())
selected_time = st.sidebar.time_input("Select a time", value=st.session_state.current_time.time())
selected_date = value=st.session_state.current_time.date()
selected_time = value=st.session_state.current_time.time()

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

# Main app logic
st.sidebar.header("PV Site Configuration")

latitude = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=51.82, step=0.01)
longitude = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-1.25, step=0.01)
capacity_kwp = st.sidebar.number_input("Capacity (kWp)", min_value=0.1, value=5000., step=0.01)

# Manage Solar Panel Database
st.sidebar.subheader("Solar Farm Database")
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
st.sidebar.subheader("Solar Farms")
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

# EV Vehicle Selection and Visualization
if not st.session_state.cars_df.empty:
    # Discrete color selection based on battery percentage
    def get_car_color(percentage):
        if percentage <= 33:
            # Red
            return [255, 0, 0, 150]
        elif percentage <= 66:
            # Yellow
            return [255, 255, 0, 150]
        else:
            # Green
            return [0, 255, 0, 150]

    st.session_state.cars_df["color"] = st.session_state.cars_df["Battery_Percentage"].apply(get_car_color)

    solar_farm_layer = pdk.Layer(
        "ScatterplotLayer",
        data=st.session_state.solar_panels,
        get_position=["Longitude", "Latitude"],
        get_radius=300,
        get_fill_color=[0, 0, 255, 255],
        pickable=True,
        radius_min_pixels=5,
        radius_max_pixels=30,
        tooltip={"text": "Name: {Name}\nCapacity: {Capacity (kWp)} kWp"}
    )

    car_layer = pdk.Layer(
        "ScatterplotLayer",
        data=st.session_state.cars_df,
        get_position=["Longitude", "Latitude"],
        get_radius=30,
        get_fill_color="color",
        pickable=True,
        radius_min_pixels=2,
        radius_max_pixels=10,
        tooltip={"text": "Name: {Car_ID}\nContribution: {Energy_Contribution_kWh} kWh"}
    )

    # compute center of all points
    center = st.session_state.cars_df[["Latitude", "Longitude"]].mean().values
    view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=10)
    r = pdk.Deck(
        layers=[solar_farm_layer, car_layer],
        initial_view_state=view_state,
    )
    st.pydeck_chart(r)

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
            st.subheader(f"Rolling forecast generated")

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
            st.markdown(f"**Difference in power generation between current and forecasted: :** <span style='color:red'>{delta:.2f}kWh</span>", unsafe_allow_html=True)

            value = valuegenerated(delta)

            fig = go.Figure()
            # Find the common index range between daily_forecast and current_forecast
            common_index = daily_forecast.index.intersection(current_forecast.index)

            # First, plot the full daily forecast line if desired
            fig.add_trace(
                go.Scatter(
                    x=daily_forecast.index,
                    y=daily_forecast["power_kw"],
                    mode='lines',
                    name='Day forecast (full)'
                )
            )

            # Now plot the restricted daily forecast line over the common range without adding it to the legend
            fig.add_trace(
                go.Scatter(
                    x=common_index,
                    y=daily_forecast.loc[common_index, "power_kw"],
                    mode='lines',
                    showlegend=False
                )
            )

            # Plot the current forecast line only over the common range, with fill to show the difference
            fig.add_trace(
                go.Scatter(
                    x=common_index,
                    y=current_forecast.loc[common_index, "power_kw"],
                    mode='lines',
                    name='30min prediction',
                    line=dict(color='red'),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.2)',
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

            result, _ = vehicle_selection(delta, st.session_state.cars_df)

            st.markdown(f"**Value generated:** <span style='color:green'>£{value:.2f}</span>", unsafe_allow_html=True)

            st.subheader("Selected Car Discharge Contributions")

            if isinstance(result, pd.DataFrame) and "Energy_Contribution_kWh" in result.columns:
                # Sort by contribution in descending order
                result_sorted = result.sort_values(by="Energy_Contribution_kWh", ascending=False)

                # Interpolation parameters
                num_updates = 20
                update_interval = 2  # in seconds
                battery_placeholder = st.empty()

                # Extract initial and final battery percentages
                initial_percentages = result_sorted["Battery_Percentage"].values
                # Assuming "Final_Battery_Percentage" is present in result
                final_percentages = result_sorted["Final_Battery_Percentage"].values

                # Live update loop
                for i in range(num_updates + 1):
                    t = i / num_updates
                    current_percentages = initial_percentages + t * (final_percentages - initial_percentages)
                    temp_df = result_sorted.copy()
                    temp_df["Current_Battery_Percentage"] = current_percentages

                    battery_placeholder.dataframe(
                        temp_df[["Car_ID", "Current_Battery_Percentage", "Final_Battery_Percentage", "Energy_Contribution_kWh"]]
                    )
                    time.sleep(update_interval)

            else:
                st.write("No cars selected or data not available.")
        else:
            st.error("No forecast data available. Please check your inputs and try again.")
    else:
        st.error("No site selected for forecasting. Please add and select a site.")
