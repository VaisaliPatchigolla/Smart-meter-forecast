import os
import pandas as pd
import numpy as np
from pathlib import Path

def main():
    raw_dir = Path('data/raw')
    out_dir = Path('data/processed/v2')
    out_dir.mkdir(parents=True, exist_ok=True)

    print("--- Phase 1: Inspect Source Schemas ---")
    
    # 1. Read Daily Consumption
    print("Reading consumption data...")
    df_cons_raw = pd.read_csv(raw_dir / 'daily_dataset.csv', usecols=['LCLid', 'day', 'energy_sum'])
    df_cons_raw = df_cons_raw.rename(columns={'LCLid': 'household_id', 'day': 'date', 'energy_sum': 'consumption_kwh'})
    df_cons_raw['date'] = pd.to_datetime(df_cons_raw['date'])
    
    # Clean consumption: coerce to numeric
    df_cons_raw['consumption_kwh'] = pd.to_numeric(df_cons_raw['consumption_kwh'], errors='coerce')
    
    print(f"Raw consumption rows: {len(df_cons_raw)}")
    print(f"Raw households: {df_cons_raw['household_id'].nunique()}")
    print(f"Raw date range: {df_cons_raw['date'].min()} to {df_cons_raw['date'].max()}")

    # Determine maximum usable date range
    daily_counts = df_cons_raw.groupby('date')['household_id'].nunique()
    
    # Rule for date range: Find the longest contiguous block where active households > 1000
    # Because there are 5566 total, >1000 is a decent chunk.
    valid_dates = daily_counts[daily_counts >= 1000].index
    if len(valid_dates) > 0:
        min_date = valid_dates.min()
        max_date = valid_dates.max()
    else:
        min_date = df_cons_raw['date'].min()
        max_date = df_cons_raw['date'].max()
        
    print(f"Selected date range: {min_date.date()} to {max_date.date()}")
    
    # Filter by date range
    df_cons = df_cons_raw[(df_cons_raw['date'] >= min_date) & (df_cons_raw['date'] <= max_date)].copy()
    
    # Eligibility Rule: A household must have valid observations for at least 300 days to be considered
    # a useful continuous time series for this period. 
    # Actually, we will just say: at least 50% of the chosen date range.
    total_days = (max_date - min_date).days + 1
    
    # Drop NAs before counting valid observations
    valid_obs = df_cons.dropna(subset=['consumption_kwh'])
    hh_counts = valid_obs.groupby('household_id')['date'].count()
    eligible_hhs = hh_counts[hh_counts >= (total_days * 0.5)].index
    print(f"Eligible households (>= 50% valid coverage): {len(eligible_hhs)} out of {df_cons['household_id'].nunique()}")
    
    df_cons = df_cons[df_cons['household_id'].isin(eligible_hhs)]
    
    # To preserve missing dates as NaN consumption:
    # Create a full grid of (eligible_hhs x date_range)
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    idx = pd.MultiIndex.from_product([eligible_hhs, all_dates], names=['household_id', 'date'])
    grid = pd.DataFrame(index=idx).reset_index()
    
    # Ensure there are no duplicate dates per household in the raw data before merging
    # Some households have multiple tariffs or duplicates in raw data? Let's take the first one or sum them.
    # Actually, checking duplicates:
    dups = df_cons.duplicated(subset=['household_id', 'date'])
    if dups.any():
        print(f"Warning: {dups.sum()} duplicates found. Grouping by sum...")
        df_cons = df_cons.groupby(['household_id', 'date'])['consumption_kwh'].sum().reset_index()
        
    # Merge grid with consumption
    df_cons_full = pd.merge(grid, df_cons, on=['household_id', 'date'], how='left')
    
    # Output consumption
    print(f"Exporting v2_consumption.csv...")
    df_cons_full.to_csv(out_dir / 'v2_consumption.csv', index=False)
    
    # 2. Weather
    print("Reading weather...")
    df_weather_raw = pd.read_csv(raw_dir / 'weather_daily_darksky.csv')
    df_weather_raw['time'] = pd.to_datetime(df_weather_raw['time'])
    
    # Inspect schema and select variables that exist
    keep_weather = ['time']
    for col in ['temperatureMax', 'temperatureMin', 'cloudCover', 'windSpeed', 'humidity', 'precipType', 'pressure', 'visibility', 'dewPoint']:
        if col in df_weather_raw.columns:
            keep_weather.append(col)
            
    df_weather = df_weather_raw[keep_weather].rename(columns={'time': 'date'})
    # Ensure no duplicates
    df_weather = df_weather.drop_duplicates(subset=['date'])
    
    # Filter weather by date range
    df_weather = df_weather[(df_weather['date'] >= min_date) & (df_weather['date'] <= max_date)]
    
    print(f"Exporting v2_weather_daily.csv...")
    df_weather.to_csv(out_dir / 'v2_weather_daily.csv', index=False)
    
    # 3. Household metadata
    print("Reading household metadata...")
    df_meta = pd.read_csv(raw_dir / 'informations_households.csv')
    df_meta = df_meta.rename(columns={'LCLid': 'household_id'})
    # Filter for eligible
    df_meta = df_meta[df_meta['household_id'].isin(eligible_hhs)]
    
    # Select cols
    meta_cols = ['household_id']
    for col in ['Acorn', 'Acorn_grouped', 'stdorToU']:
        if col in df_meta.columns:
            meta_cols.append(col)
            
    df_meta = df_meta[meta_cols].drop_duplicates(subset=['household_id'])
    
    print(f"Exporting v2_household_metadata.csv...")
    df_meta.to_csv(out_dir / 'v2_household_metadata.csv', index=False)
    
    # 4. Holidays
    print("Reading bank holidays...")
    df_holidays = pd.read_csv(raw_dir / 'uk_bank_holidays.csv')
    df_holidays = df_holidays.rename(columns={'Bank holidays': 'date', 'Type': 'holiday_name'})
    df_holidays['date'] = pd.to_datetime(df_holidays['date'], errors='coerce')
    df_holidays = df_holidays.dropna(subset=['date'])
    df_holidays = df_holidays[(df_holidays['date'] >= min_date) & (df_holidays['date'] <= max_date)]
    df_holidays = df_holidays.drop_duplicates(subset=['date'])
    
    print(f"Exporting v2_bank_holidays.csv...")
    df_holidays.to_csv(out_dir / 'v2_bank_holidays.csv', index=False)
    
    print("Data preparation complete.")

if __name__ == '__main__':
    main()
