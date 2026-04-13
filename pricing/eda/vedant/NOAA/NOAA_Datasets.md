## Data Dictionary

- `airports.csv`: US airport and station reference table.
  Key columns: `icao_id`, `faa_id`, `name`, `lat`, `lon`, `elevation_m`, `state`, `country`, `market_group`, `has_metar`, `has_taf`.
  
- `metar_observations.csv`: current METAR observations normalized to a tabular format.
  Key columns: `icao_id`, `obs_time_utc`, `receipt_time_utc`, `temp_c`, `dewpoint_c`, `wind_dir_deg`, `wind_speed_kt`, `wind_gust_kt`, `visibility_sm`, `altimeter_hpa`, `flight_category`, `weather_code`, `cloud_layers_json`, `raw_text`.

- `taf_forecasts.csv`: one row per TAF issuance.
  Key columns: `icao_id`, `issue_time_utc`, `valid_from_utc`, `valid_to_utc`, `raw_taf`, `remarks`, `forecast_blocks_json`.

- `taf_forecast_blocks.csv`: exploded TAF forecast segments.
  Key columns: `icao_id`, `issue_time_utc`, `block_from_utc`, `block_to_utc`, `change_type`, `probability`, `wind_dir_deg`, `wind_speed_kt`, `wind_gust_kt`, `visibility_sm`, `weather_code`, `cloud_layers_json`, `icing_turbulence_json`, `temperature_json`.

- `pireps.csv`: pilot reports filtered to US coverage.
  Key columns: `report_id_surrogate`, `receipt_time_utc`, `obs_time_utc`, `lat`, `lon`, `flight_level_hundreds_ft`, `aircraft_type`, `flight_phase`, `weather_code`, `visibility`, `turbulence_fields_json`, `icing_fields_json`, `clouds_json`, `raw_text`.

- `sigmets.csv`: SIGMET hazard advisories.
  Key columns: `sigmet_id_surrogate`, `product_family`, `hazard`, `severity`, `valid_from_utc`, `valid_to_utc`, `altitude_low_ft`, `altitude_high_ft`, `movement_dir_deg`, `movement_speed_kt`, `geometry_json`, `raw_text`.

- `gairmets.csv`: G-AIRMET advisories.
  Key columns: `gairmet_id_surrogate`, `product`, `hazard`, `forecast_valid_time_utc`, `valid_from_utc`, `valid_to_utc`, `geometry_json`, `conditions_json`.

- `notams.csv`: placeholder schema only in this notebook.
  Key columns: `notam_id`, `icao_id`, `effective_from_utc`, `effective_to_utc`, `classification`, `subject`, `condition`, `traffic`, `purpose`, `scope`, `lower_limit`, `upper_limit`, `text`, `source_system`.

Time fields are UTC. Geometry fields are stored as JSON text.
