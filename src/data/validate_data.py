import pandas as pd
import os

base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
processed_dir = os.path.join(base_dir, "data", "processed")
output_data = os.path.join(processed_dir, "household_daily_100.csv")

def validate_data():
    print("--- Validation Report ---")
    
    if not os.path.exists(output_data):
        print(f"FAIL: {output_data} not found.")
        return
        
    df = pd.read_csv(output_data)
    
    # Validation constraints
    expected_households = 100
    expected_rows = 73100
    
    households = df['household_id'].nunique()
    print(f"Selected household count: {households}")
    
    total_rows = len(df)
    print(f"Total row count: {total_rows}")
    
    min_date = df['date'].min()
    max_date = df['date'].max()
    print(f"Minimum date: {min_date}")
    print(f"Maximum date: {max_date}")
    
    unique_dates_per_hh = df.groupby('household_id')['date'].nunique()
    print(f"Unique dates per household: {unique_dates_per_hh.unique()}")
    
    # Households with missing dates (should be 0)
    missing_dates_hhs = (unique_dates_per_hh != 731).sum()
    print(f"Households with missing dates: {missing_dates_hhs}")
    
    missing_cons = df['consumption_kwh'].isna().sum()
    print(f"Missing consumption count: {missing_cons}")
    
    duplicates = df.duplicated(subset=['household_id', 'date']).sum()
    print(f"Duplicate household/date count: {duplicates}")
    
    negative_cons = (df['consumption_kwh'] < 0).sum()
    print(f"Negative consumption count: {negative_cons}")
    
    min_cons = df['consumption_kwh'].min()
    max_cons = df['consumption_kwh'].max()
    mean_cons = df['consumption_kwh'].mean()
    print(f"Minimum consumption: {min_cons}")
    print(f"Maximum consumption: {max_cons}")
    print(f"Mean consumption: {mean_cons}")
    
    file_size_mb = os.path.getsize(output_data) / (1024 * 1024)
    print(f"Processed file size: {file_size_mb:.2f} MB")
    
    # PASS/FAIL Logic
    passed = True
    if households != expected_households:
        print("FAIL: Expected exactly 100 households.")
        passed = False
    if total_rows != expected_rows:
        print(f"FAIL: Expected exactly {expected_rows} rows.")
        passed = False
    if missing_dates_hhs > 0:
        print("FAIL: Some households are missing dates.")
        passed = False
    if missing_cons > 0:
        print("FAIL: Missing consumption values present.")
        passed = False
    if duplicates > 0:
        print("FAIL: Duplicate household/date entries found.")
        passed = False
    if negative_cons > 0:
        print("FAIL: Negative consumption values found.")
        passed = False
        
    print("-------------------------")
    if passed:
        print("Validation: PASS")
    else:
        print("Validation: FAIL")

if __name__ == "__main__":
    validate_data()
