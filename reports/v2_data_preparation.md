# V2 Data Preparation Report

## 1. Executive Summary
This report details the end-to-end data preparation and validation of the V2 dataset for Smart Meter Consumption Forecasting. The preparation pipeline successfully produced a clean, continuous daily baseline spanning 716 days across 5,373 households. The final datasets are strictly isolated from target-leakage and represent the maximal continuous historical period available. 

## 2. Source Dataset Inventory
- `data/raw/daily_dataset.csv`
- `data/raw/weather_daily_darksky.csv`
- `data/raw/informations_households.csv`
- `data/raw/uk_bank_holidays.csv`

## 3. Consumption Dataset
The consumption dataset (`v2_consumption.csv`) was restricted strictly to `household_id`, `date`, and `consumption_kwh`. All other statistical aggregates (`energy_max`, `energy_std`, etc.) were intentionally dropped as they represent post-facto derived statistics of the target period, posing a leakage risk. Missing days were populated with `NaN` consumption values to maintain continuous time indexes.

## 4. Household Metadata
Metadata (`v2_household_metadata.csv`) was perfectly joined to the eligible households. Variables preserved: `Acorn`, `Acorn_grouped`, and `stdorToU`.

## 5. Weather Dataset
Weather data (`v2_weather_daily.csv`) contains observed daily meteorology. Extraneous variables were excluded, retaining strictly observed predictors: `temperatureMax`, `temperatureMin`, `cloudCover`, `windSpeed`, `humidity`, `precipType`, `pressure`, `visibility`, and `dewPoint`.

## 6. Bank Holidays
Holidays (`v2_bank_holidays.csv`) cover the exact date range of the consumption data, ensuring deterministic holiday alignment without temporal leakage.

## 7. Join Strategy
- Consumption + Metadata: Joinable on `household_id`.
- Consumption + Weather: Joinable on `date`.
- Consumption + Holidays: Joinable on `date`.
All relationships are Many-to-1 against the primary consumption table.

## 8. Household Eligibility
**Rule:** A household was retained if it had valid `consumption_kwh` observations for at least 50% of the selected date range.
- Total raw households: 5,566
- Eligible retained households: 5,373

## 9. Date Range Selection
The maximum defensible historical period was determined dynamically by finding the longest contiguous period where at least 1,000 households were actively reporting. 
**Final Date Range:** 2012-03-15 to 2014-02-28 (716 days).

## 10. Data Quality Results
- **Household count:** PASS (5,373)
- **Date range:** PASS (2012-03-15 to 2014-02-28)
- **Duplicate household/date:** PASS (0)
- **Negative consumption:** PASS (0)
- **Metadata join coverage:** PASS (100%)
- **Leakage check:** PASS (0 leakage columns)

## 11. Missing Data
Missing consumption values account for 11.52% (443,032 rows) of the finalized grid. These were injected intentionally as `NaN` rows to preserve time-series continuity. Feature engineering steps will be responsible for handling imputation securely.
Weather data is nearly perfect, with only 1 total null value across all preserved variables.

## 12. Outlier Summary
Zero-consumption days exist and are preserved. No negative values exist.

## 13. Leakage Safety
Absolutely no future-derived targets exist in the dataset. `energy_sum` is strictly aliased to `consumption_kwh`, and same-day summaries are purged.

## 14. Final V2 Dataset Schema
- `v2_consumption.csv`: household_id, date, consumption_kwh
- `v2_weather_daily.csv`: date, temperatureMax, temperatureMin, cloudCover, windSpeed, humidity, precipType, pressure, visibility, dewPoint
- `v2_household_metadata.csv`: household_id, Acorn, Acorn_grouped, stdorToU
- `v2_bank_holidays.csv`: date, holiday_name

## 15. Dataset Sizes
- `v2_consumption.csv`: 125.19 MB
- `v2_household_metadata.csv`: 0.17 MB
- `v2_weather_daily.csv`: 0.04 MB
- `v2_bank_holidays.csv`: 0.00 MB

*Note: `v2_consumption.csv` exceeds standard Git limits (100 MB). It should NOT be committed directly. We recommend tracking this file using DVC (Data Version Control) or generating a `< 5MB` sample for standard git repository demonstration purposes.*

## 16. Known Limitations
- The 11.5% missing consumption blocks will require careful imputation.
- A small number of consumption dates lack weather records (2 dates) due to Dark Sky API original data gaps.

## 17. Recommendation for Feature Engineering
The dataset is cleanly normalized. Next steps should focus on:
1. Interpolation/Imputation of NaN consumption values (using localized moving averages).
2. Rolling window feature construction (lags, rolling means).
3. Derived calendar features (Day of week, Season).
