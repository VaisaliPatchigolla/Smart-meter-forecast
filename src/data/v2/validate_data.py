import pandas as pd
from pathlib import Path

def print_result(check, result, details=""):
    print(f"[{result}] {check} - {details}")

def main():
    out_dir = Path('data/processed/v2')
    
    print("--- Phase 10: Data Quality Validation ---")
    
    try:
        df_cons = pd.read_csv(out_dir / 'v2_consumption.csv')
        df_weather = pd.read_csv(out_dir / 'v2_weather_daily.csv')
        df_meta = pd.read_csv(out_dir / 'v2_household_metadata.csv')
        df_holidays = pd.read_csv(out_dir / 'v2_bank_holidays.csv')
    except Exception as e:
        print_result("Files exist", "FAIL", str(e))
        return

    # Convert dates
    df_cons['date'] = pd.to_datetime(df_cons['date'])
    df_weather['date'] = pd.to_datetime(df_weather['date'])
    df_holidays['date'] = pd.to_datetime(df_holidays['date'])
    
    # 1. Household count
    hh_count = df_cons['household_id'].nunique()
    print_result("1. Household count", "PASS" if hh_count > 0 else "FAIL", f"{hh_count} households")

    # 2. Date range
    min_date = df_cons['date'].min()
    max_date = df_cons['date'].max()
    print_result("2. Date range", "PASS", f"{min_date.date()} to {max_date.date()}")
    
    # 3. Total rows
    total_rows = len(df_cons)
    print_result("3. Total rows", "PASS", f"{total_rows} rows")
    
    # 4. Missing consumption
    missing_cons = df_cons['consumption_kwh'].isnull().sum()
    pct_missing = (missing_cons / total_rows) * 100
    print_result("4. Missing consumption", "WARNING" if missing_cons > 0 else "PASS", f"{missing_cons} rows ({pct_missing:.2f}%)")
    
    # 5. Duplicate household/date combinations
    dups = df_cons.duplicated(subset=['household_id', 'date']).sum()
    print_result("5. Duplicate household/date", "FAIL" if dups > 0 else "PASS", f"{dups} duplicates")
    
    # 6. Negative consumption
    negatives = (df_cons['consumption_kwh'] < 0).sum()
    print_result("6. Negative consumption", "FAIL" if negatives > 0 else "PASS", f"{negatives} negative values")
    
    # 7. Invalid dates
    invalid_dates = df_cons['date'].isnull().sum()
    print_result("7. Invalid dates", "FAIL" if invalid_dates > 0 else "PASS", f"{invalid_dates} invalid dates")
    
    # 8. Household ID consistency
    cons_hhs = set(df_cons['household_id'].unique())
    meta_hhs = set(df_meta['household_id'].unique())
    diff = len(cons_hhs ^ meta_hhs)
    print_result("8. Household ID consistency", "FAIL" if diff > 0 else "PASS", f"{diff} mismatched households")
    
    # 9. Metadata join coverage
    missing_meta = df_cons[~df_cons['household_id'].isin(meta_hhs)]
    print_result("9. Metadata join coverage", "FAIL" if len(missing_meta) > 0 else "PASS", f"{len(missing_meta)} missing metadata rows")
    
    # 10. Weather date coverage
    weather_dates = set(df_weather['date'])
    cons_dates = set(df_cons['date'])
    missing_weather_dates = len(cons_dates - weather_dates)
    print_result("10. Weather date coverage", "WARNING" if missing_weather_dates > 0 else "PASS", f"{missing_weather_dates} consumption dates missing weather")
    
    # 11. Weather missingness
    weather_missing = df_weather.isnull().sum().sum()
    print_result("11. Weather missingness", "WARNING" if weather_missing > 0 else "PASS", f"{weather_missing} total nulls in weather")
    
    # 12. Bank-holiday date validity
    invalid_holidays = df_holidays['date'].isnull().sum()
    print_result("12. Bank-holiday date validity", "FAIL" if invalid_holidays > 0 else "PASS", f"{invalid_holidays} invalid dates")
    
    # 13. Duplicate weather dates
    weather_dups = df_weather.duplicated(subset=['date']).sum()
    print_result("13. Duplicate weather dates", "FAIL" if weather_dups > 0 else "PASS", f"{weather_dups} duplicates")
    
    # 14. Duplicate holiday dates where applicable
    holiday_dups = df_holidays.duplicated(subset=['date']).sum()
    print_result("14. Duplicate holiday dates", "FAIL" if holiday_dups > 0 else "PASS", f"{holiday_dups} duplicates")

    # Leakage check
    leakage_cols = ['energy_mean', 'energy_max', 'energy_min', 'energy_median', 'energy_std', 'energy_count']
    leaks = [c for c in leakage_cols if c in df_cons.columns]
    print_result("Leakage check", "FAIL" if leaks else "PASS", f"Leakage columns found: {leaks}" if leaks else "No leakage columns found")

if __name__ == '__main__':
    main()
