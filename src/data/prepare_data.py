import pandas as pd
import os
import math

# Paths
base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
raw_dir = os.path.join(base_dir, "data", "raw")
processed_dir = os.path.join(base_dir, "data", "processed")

daily_csv = os.path.join(raw_dir, "daily_dataset.csv")
info_csv = os.path.join(raw_dir, "informations_households.csv")
output_data = os.path.join(processed_dir, "household_daily_100.csv")
output_meta = os.path.join(processed_dir, "household_metadata.csv")

def prepare_data():
    print("Loading data...")
    # 1. Load data
    df = pd.read_csv(daily_csv, usecols=['LCLid', 'day', 'energy_sum'])
    meta = pd.read_csv(info_csv)
    
    # 2. Filter date range
    df['day'] = pd.to_datetime(df['day'], errors='coerce')
    start_date = pd.to_datetime('2012-01-01')
    end_date = pd.to_datetime('2013-12-31')
    
    df = df[(df['day'] >= start_date) & (df['day'] <= end_date)].copy()
    
    # Expected dates
    expected_dates = pd.date_range(start=start_date, end=end_date)
    expected_days = len(expected_dates) # 731
    
    print(f"Expected dates range length: {expected_days}")
    
    # 3. Filter complete households
    # We must ensure they have exactly all expected dates
    # Count unique dates per household
    date_counts = df.groupby('LCLid')['day'].nunique()
    eligible_ids = date_counts[date_counts == expected_days].index.tolist()
    
    # Further check that they literally have those dates
    # Since they have exactly 731 unique dates in a 731 day period, they must cover all days.
    df_eligible = df[df['LCLid'].isin(eligible_ids)].copy()
    print(f"Eligible households with complete coverage: {len(eligible_ids)}")
    
    # Exclude households with missing values in energy_sum to be safe
    # If a household has missing energy_sum, they shouldn't be selected
    missing_energy_ids = df_eligible[df_eligible['energy_sum'].isna()]['LCLid'].unique()
    eligible_ids = [x for x in eligible_ids if x not in missing_energy_ids]
    
    print(f"Eligible households after dropping those with missing energy_sum: {len(eligible_ids)}")
    
    # 4. Stratified Proportional Selection
    meta_eligible = meta[meta['LCLid'].isin(eligible_ids)].copy()
    
    # Create stratification key
    meta_eligible['stratum'] = meta_eligible['Acorn_grouped'].astype(str) + "_" + meta_eligible['stdorToU'].astype(str)
    stratum_counts = meta_eligible['stratum'].value_counts()
    
    # Calculate exact allocations to sum to 100 using largest remainder method
    total_eligible = len(meta_eligible)
    target = 100
    
    allocations = {}
    remainders = {}
    
    for stratum, count in stratum_counts.items():
        exact = (count / total_eligible) * target
        allocations[stratum] = int(math.floor(exact))
        remainders[stratum] = exact - allocations[stratum]
        
    current_sum = sum(allocations.values())
    shortfall = target - current_sum
    
    # Sort remainders descending to distribute the shortfall
    sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
    
    for i in range(shortfall):
        stratum = sorted_remainders[i][0]
        allocations[stratum] += 1
        
    # Select households deterministically
    selected_ids = []
    
    for stratum, alloc_count in allocations.items():
        if alloc_count == 0:
            continue
        # Get households in this stratum, sort deterministically
        stratum_hhs = meta_eligible[meta_eligible['stratum'] == stratum].sort_values('LCLid')['LCLid'].tolist()
        
        # Take the required amount
        selected_ids.extend(stratum_hhs[:alloc_count])
        
    print(f"Selected exactly {len(selected_ids)} households.")
    
    # 5. Format Columns & Output
    df_final = df_eligible[df_eligible['LCLid'].isin(selected_ids)].copy()
    
    df_final.rename(columns={
        'LCLid': 'household_id',
        'day': 'date',
        'energy_sum': 'consumption_kwh'
    }, inplace=True)
    
    # Sort for final output
    df_final = df_final.sort_values(['household_id', 'date']).reset_index(drop=True)
    
    meta_final = meta[meta['LCLid'].isin(selected_ids)].copy()
    meta_final.rename(columns={'LCLid': 'household_id'}, inplace=True)
    meta_final = meta_final.sort_values('household_id').reset_index(drop=True)
    
    print("Writing files to data/processed/ ...")
    df_final.to_csv(output_data, index=False)
    meta_final.to_csv(output_meta, index=False)
    
    print("Data preparation complete.")

if __name__ == "__main__":
    prepare_data()
