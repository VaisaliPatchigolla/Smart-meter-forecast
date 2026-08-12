# Data Dictionary

## Processed Dataset: `household_daily_100.csv`

This dataset contains a deterministically selected, representative sample of 100 London households spanning exactly 2 full years (2012-01-01 to 2013-12-31).

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `household_id` | String | Unique identifier for each household. Mapped directly from the original `LCLid` field. |
| `date` | Date | The date of electricity consumption in YYYY-MM-DD format. Mapped directly from the original `day` field. |
| `consumption_kwh` | Float | The total daily electricity consumption in kilowatt-hours (kWh). Mapped directly from the original `energy_sum` field. No arbitrary unit conversions have been applied. |

## Processed Dataset: `household_metadata.csv`

Contains demographic and tariff metadata for the 100 selected households.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `household_id` | String | Unique identifier for each household (`LCLid`). |
| `stdorToU` | String | Tariff type (Standard or Time of Use). |
| `Acorn` | String | Detailed Acorn demographic classification. |
| `Acorn_grouped` | String | Grouped Acorn demographic classification. |
| `file` | String | Original block file reference. |
