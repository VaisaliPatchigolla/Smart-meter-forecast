import pandas as pd
from pathlib import Path
import json

def main():
    print("Forecasting Driver Audit...")
    
    pq_file = Path('data/processed/v2/features.parquet')
    if not pq_file.exists():
        print(f"Error: {pq_file} not found. Run convert_to_parquet.py first.")
        return
        
    # Read just the columns to audit
    df_cols = pd.read_parquet(pq_file).columns
    
    # Classify existing features
    groups = {
        'Historical Demand': [c for c in df_cols if 'lag' in c or 'rolling' in c or 'historical' in c],
        'Weather': [c for c in df_cols if 'observed_' in c],
        'Calendar': ['day_of_week', 'is_weekend', 'day_of_month', 'month', 'day_of_year', 'week_of_year', 'is_month_start', 'is_month_end', 'sin_day_of_year', 'cos_day_of_year', 'sin_day_of_week', 'cos_day_of_week', 'is_bank_holiday'],
        'Household Metadata': ['Acorn', 'Acorn_grouped', 'stdorToU']
    }
    
    print("\n--- Current Available Features ---")
    for group, features in groups.items():
        existing = [f for f in features if f in df_cols]
        print(f"\n{group} ({len(existing)}):")
        for f in existing:
            print(f"  - {f}")
            
    # Identify missing drivers conceptually
    print("\n--- Missing Important Forecasting Drivers ---")
    missing_drivers = {
        "True Weather Forecast": "We only have historical observed weather. In a true production environment, we need Day 1 to Day 7 numerical weather forecasts (e.g. from Met Office). Using observed weather as a proxy represents Oracle-knowledge.",
        "Heating / Cooling Degree Days (HDD/CDD)": "Although we have temperature, explicit HDD/CDD derivations typically represent non-linear HVAC response curves better than raw temperature. Not present.",
        "Solar Generation Behind-the-Meter": "If households have PV solar, net meter consumption will artificially drop during sunny days. We lack PV installation metadata or generation proxy.",
        "Electric Vehicle (EV) Ownership": "EV charging creates massive spikes. We lack metadata on EV ownership.",
        "Heat Pump Ownership": "Electrification of heat shifts the response to temperature. We lack metadata on heat pumps.",
        "Occupancy Data / Working from Home": "Real-time occupancy drastically changes profiles. We lack proxy data (e.g., smart home sensors)."
    }
    
    for driver, reason in missing_drivers.items():
        print(f"Missing: {driver}")
        print(f"Impact: {reason}")
        
    print("\nAudit Complete.")

if __name__ == '__main__':
    main()
