import pandas as pd
import numpy as np
import os

base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
input_path = os.path.join(base_dir, "data", "processed", "household_daily_100.csv")
output_path = os.path.join(base_dir, "data", "processed", "features.csv")

def build_features():
    print("Loading processed data...")
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['household_id', 'date']).reset_index(drop=True)
    
    print("Building lag features...")
    lags = [1, 2, 3, 7, 14, 28, 364]
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby('household_id')['consumption_kwh'].shift(lag)
        
    print("Building rolling features...")
    # Shift(1) guarantees that the current day's target is excluded
    shifted_cons = df.groupby('household_id')['consumption_kwh'].shift(1)
    
    df['rolling_mean_7'] = shifted_cons.groupby(df['household_id']).rolling(7).mean().reset_index(level=0, drop=True)
    df['rolling_std_7'] = shifted_cons.groupby(df['household_id']).rolling(7).std().reset_index(level=0, drop=True)
    df['rolling_mean_14'] = shifted_cons.groupby(df['household_id']).rolling(14).mean().reset_index(level=0, drop=True)
    df['rolling_mean_28'] = shifted_cons.groupby(df['household_id']).rolling(28).mean().reset_index(level=0, drop=True)
    
    print("Building calendar features...")
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
    
    # Validation / Leakage checks
    print("Running leakage checks...")
    
    # 1. lag_1 must match exactly yesterday's consumption for the same household
    # we take a random internal row (index 100 which is guaranteed not to be the first day of a household)
    test_idx = 100
    if df.loc[test_idx, 'household_id'] == df.loc[test_idx-1, 'household_id']:
        assert np.isclose(df.loc[test_idx, 'lag_1'], df.loc[test_idx-1, 'consumption_kwh']), "Leakage Check Failed: lag_1 is incorrect"
        
    # 2. Check rolling mean is purely historical
    if df.loc[test_idx, 'household_id'] == df.loc[test_idx-7, 'household_id']:
        hist_values = df.loc[test_idx-7:test_idx-1, 'consumption_kwh'].values
        assert np.isclose(df.loc[test_idx, 'rolling_mean_7'], np.mean(hist_values)), "Leakage Check Failed: rolling_mean_7 is incorrect"
        
    print("Leakage checks passed.")
    
    print(f"Saving features to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done.")

if __name__ == "__main__":
    build_features()
