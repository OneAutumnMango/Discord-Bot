import pandas as pd
import requests
from datetime import datetime, timedelta, date, time
import os
import pickle
from urllib.parse import quote
import numpy as np
from utide import solve, reconstruct
import io
import pytz

from sklearn.metrics import mean_squared_error
from itertools import product


STATION_NAME = "Dublin Port"
ERDDAP_URL = "https://erddap.marine.ie/erddap/tabledap/IrishNationalTideGaugeNetwork.csv"
MODEL_FILE = "tide_model.pkl"
DAYS_LOOKBACK = 90
DATA_FILE = 'data.csv'
IRELAND_TZ = pytz.timezone("Europe/Dublin")

def download_tide_data(redownload=False):
    if not redownload and os.path.exists(DATA_FILE):
        print("Loading tide data from local cache...")
        df = pd.read_csv(DATA_FILE, parse_dates=['time'], index_col='time')
        return df

    print("Downloading recent tide data...")
    time_end = datetime.now(IRELAND_TZ)
    time_start = time_end - timedelta(days=DAYS_LOOKBACK)
    
    query = (
        f"?{quote('time,station_id,Water_Level_LAT')}"
        f"&station_id=%22{quote(STATION_NAME)}%22"
        f"&time%3E={quote(time_start.isoformat())}Z"
        f"&time%3C={quote(time_end.isoformat())}Z"
    )
    
    url = ERDDAP_URL + query
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        print("Attemping to reach local cache...")
        if os.path.exists(DATA_FILE):
            print("Loading tide data from local cache...")
            df = pd.read_csv(DATA_FILE, parse_dates=['time'], index_col='time')
            return df
        else: print("no cache found, exiting")
        return None

    df = pd.read_csv(io.StringIO(response.text), skiprows=[1])
    
    if df.empty:
        print("No data found for the given time range.")
        return None

    df['time'] = pd.to_datetime(df['time'])
    df = df.dropna(subset=["Water_Level_LAT"])
    df.set_index('time', inplace=True)
    print(f"Downloaded {len(df)} rows of tide data.")

    df = remove_outliers(df)
    df.to_csv(DATA_FILE)
    return df

def remove_outliers(df, z_thresh=3):
    """Remove tide height outliers using Z-score thresholding."""
    heights = df["Water_Level_LAT"]
    mean = heights.mean()
    std = heights.std()
    z_scores = (heights - mean) / std
    filtered_df = df[abs(z_scores) < z_thresh]
    print(f"Removed {len(df) - len(filtered_df)} outliers from data")
    return filtered_df

def fit_tide_model(df):
    print("Fitting harmonic model with UTide...")
    
    times = df.index.values
    heights = df["Water_Level_LAT"].values

    # plt.figure(figsize=(12, 5))
    # plt.plot(times, heights, label='Observed Water Level (LAT)', color='blue')
    # plt.xlabel('Hours since start')
    # plt.ylabel('Water Level (m)')
    # plt.title('Observed Tide Data - Dublin Port')
    # plt.grid(True)
    # plt.legend()
    # plt.tight_layout()
    # plt.savefig("figreal.png")

    coef = solve(
        times,
        heights,
        # lat=53.34,  # Dublin Port approx latitude
        lat=53.35,
        nodal=True,
        trend=True,
        method='ols',
        conf_int='none',
        Rayleigh_min=0.95,
    )

    print("Harmonic model fitted successfully.")
    return {"coef": coef, "t0": df.index[0]}

def predict_tide(dt, model=None):
    model = model if model is not None else get_or_create_model()
    if model is None:
        print("Unable to proceed without a valid harmonic model.")
        return

    if isinstance(dt, (list, np.ndarray)):  # If it's a list or array, process each item
        dt = [
            pd.to_datetime(t).tz_localize(pytz.UTC) + timedelta(minutes=6)
            if pd.to_datetime(t).tzinfo is None
            else t + timedelta(minutes=6)
            for t in dt
        ]
    else:  # If it's a single datetime
        dt = pd.to_datetime(dt).tz_localize(pytz.UTC) + timedelta(minutes=6) \
            if pd.to_datetime(dt).tzinfo is None \
            else dt + timedelta(minutes=6)
    
    return reconstruct(dt, model["coef"]).h

def get_or_create_model():
    # if False: #os.path.exists(MODEL_FILE):
    if os.path.exists(MODEL_FILE):
        print("Loading cached harmonic model...")
        with open(MODEL_FILE, 'rb') as f:
            model = pickle.load(f)
    else:
        df = download_tide_data()
        if df is None:
            return None
        model = fit_tide_model(df)
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump(model, f)
    return model

def test_all_configs(df):
    print("Testing all configurations for UTide...")

    # Define parameter options
    nodal_options = [True, False, 'linear_time']
    trend_options = [True, False]
    method_options = ['ols', 'robust']  # OLS or least squares
    conf_int_options = ['linear', 'MC', 'none']  # Confidence intervals or none
    r_min_options = [0.9,0.95,1.0]

    # Prepare data
    times = df.index.values
    heights = df["Water_Level_LAT"].values

    split_index = int(len(times) * 0.75)
    train_times = times[:split_index]
    train_heights = heights[:split_index]
    test_times = times[split_index:]
    test_heights = heights[split_index:]

    # To store best MSE and configuration
    best_mse = float('inf')
    best_config = None
    best_coef = None

    # Loop through all combinations of parameters
    for nodal, trend, method, conf_int, r_min in product(nodal_options, trend_options, method_options, conf_int_options, r_min_options):
        print(f"Testing configuration: {nodal=}, {trend=}, {method=}, {conf_int=}, {r_min=}")

        try:
            # Fit the model with the current configuration
            coef = solve(
                train_times,
                train_heights,
                lat=53.585,
                nodal=nodal,
                trend=trend,
                method=method,
                conf_int=conf_int,
                Rayleigh_min=r_min
            )

            # Reconstruct predicted heights using the model
            predicted_heights_train = reconstruct(train_times, coef)
            predicted_heights_test = reconstruct(test_times, coef)

            # Calculate MSE for the current configuration
            mse_train = mean_squared_error(train_heights, predicted_heights_train.h)
            mse_test = mean_squared_error(test_heights, predicted_heights_test.h)

            print(f"MSE (train set): {mse_train:.4f}")
            print(f"MSE (test set): {mse_test:.4f}\n")

            # If this configuration has a lower MSE, save it as the best
            if mse_test < best_mse:
                best_mse = mse_test
                best_config = (nodal, trend, method, conf_int)
                best_coef = coef

        except Exception as e:
            print(f"Error fitting model for configuration {nodal}, {trend}, {method}, {conf_int}: {e}")
            continue

    # Print the best configuration and MSE
    print("\nBest configuration:")
    print(f"nodal={best_config[0]}, trend={best_config[1]}, method={best_config[2]}, conf_int={best_config[3]}")
    print(f"Best MSE: {best_mse:.4f}")

    # Return the best model
    return {"coef": best_coef, "t0": df.index[0]}

def rebuild_model():
    df = download_tide_data(redownload=True)
    if df is None: return False
    model = fit_tide_model(df)
    if model is None: return False
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model, f)
    return True

def main():
    # print(download_tide_data())
    model = get_or_create_model()
    if model is None:
        print("Unable to proceed without a valid harmonic model.")
        return



    df = download_tide_data()
    times = df.index.values

    extended_times = np.concatenate([times, np.arange(times[-1], times[-1] + np.timedelta64(7, 'D'), dtype='datetime64[m]')])
    predicted_heights = predict_tide(extended_times)


    # plt.figure(figsize=(12, 6))
    # plt.plot(df.index.values, df["Water_Level_LAT"].values, label='Observed Water Level (LAT)', color='red')
    # plt.plot(extended_times, predicted_heights.h, label='Predicted Water Level (LAT)', color='blue')
    # plt.xlabel('Date and Time')
    # plt.ylabel('Water Level (m)')
    # plt.title('Tide Prediction and Observed Water Level - Dublin Port')
    # plt.legend()
    # plt.grid(True)
    # plt.xticks(rotation=45)
    # plt.tight_layout()
    # plt.savefig("tide_predictions_with_real.png")

    # target_dt = datetime.now(IRELAND_TZ).replace(hour=17, minute=30, second=0, microsecond=0)# + timedelta(days=1)
    target_date = date(2025, 5, 11)
    target_time = time(18,10)
    target_dt = pytz.utc.localize(datetime.combine(target_date, target_time))
    predicted_height = predict_tide(target_dt)
    print(f"Predicted tide height at {target_dt.isoformat()}: {predicted_height[0]:.2f} meters")

    target_time = time(19,10)
    target_dt = pytz.utc.localize(datetime.combine(target_date, target_time))
    predicted_height = predict_tide(target_dt)
    print(f"Predicted tide height at {target_dt.isoformat()}: {predicted_height[0]:.2f} meters")

    target_time = time(20,10)
    target_dt = pytz.utc.localize(datetime.combine(target_date, target_time))
    predicted_height = predict_tide(target_dt)
    print(f"Predicted tide height at {target_dt.isoformat()}: {predicted_height[0]:.2f} meters")

    

if __name__ == "__main__":
    main()
