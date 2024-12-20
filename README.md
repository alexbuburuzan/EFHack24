# Solar Nowcasting and EV Battery-to-Grid Stabilization

This project demonstrates a "proof-of-concept" dashboard that forecasts solar power production in real-time and integrates Electric Vehicle (EV) batteries' novel vehicle-to-grid (V2G) capabilities. The goal is to leverage EV batteries to stabilize the output of a solar farm by covering unexpected dips in solar generation, thereby enhancing the reliability and stability of renewable energy on the grid.

## Overview

![Dashboard Demo](images/demo.gif)

We build upon the Open Source Quartz Solar Forecast model developed by Open Climate Fix. This model leverages satellite data to make short-term predictions (nowcasts) of solar power production. By accurately forecasting dips in solar output, we can dispatch energy from EV batteries to the grid, effectively smoothing fluctuations and stabilizing the solar farm’s contribution.

### Key Features:

- **Real-time Solar Forecasting**: Use of the Quartz solar forecasting model to provide short-term, granular predictions of solar farm output.
- **Vehicle-to-Grid Integration**: Control logic that simulates EV batteries discharging energy into the grid during predicted shortfalls, improving stability.
- **Interactive Dashboard**: A Streamlit-based dashboard that allows users to visualize forecasts, monitor EV battery states, and explore the potential stabilization provided to the grid.

In proof-of-concept tests, we observed the EV integration could smooth the solar farm’s output by approximately 5-10%, helping the grid better handle the inherent variability in solar generation.

---

## Getting Started
We did not 

### Installation

#### Using Conda (recommended):
```bash
conda create --name ocf --file requirements.txt
conda activate ocf
```

#### Alternatively, using pip:
```bash
pip install -e .
```
---

## Running the API

First, start the backend API that will serve forecast data (on port 8000):

```bash
cd api
python main.py
```

The API should now be running at `http://localhost:8000`.

---

## Running the Dashboard

After the API is running, launch the Streamlit dashboard:

```bash
python -m streamlit run dashboards/dashboard_2/app.py
```

The dashboard will open in your default web browser at `http://localhost:8501` (or a similar local address).

---

## Hackathon Team
This work was done as part of the 2024 Fall Entrepreneur First one-day Hackathon. 

- **Alexandru Buburuzan**
- **Thomas Stuart-Smith**
- **Ariel Thomas**
- **Alramina Myrzabekova**

