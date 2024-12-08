from quartz_solar_forecast.utils.forecast_csv import write_out_forecasts

if __name__ == "__main__":
    # please change the site name, start_datetime and end_datetime, latitude, longitude and capacity_kwp as per your requirement
    write_out_forecasts(
        init_time_freq=6,
        start_datetime="2024-12-07 00:00:01",
        end_datetime="2024-12-08 00:00:01",
        site_name="Test",
        latitude=51.75,
        longitude=-1.25,
        capacity_kwp=1.25
    )