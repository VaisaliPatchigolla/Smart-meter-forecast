# V2 Data Dictionary

This dictionary documents the schema and provenance of the V2 electricity consumption forecasting base datasets.

## 1. `v2_consumption.csv`
**Source:** `data/raw/daily_dataset.csv`
**Description:** The primary household daily electricity consumption dataset. Missing dates for eligible households are represented with `NaN` in `consumption_kwh`.

| Column | Meaning | Unit | Data Type | Transformations Performed | Leakage Considerations |
|---|---|---|---|---|---|
| `household_id` | Unique identifier for a household | ID | String | Renamed from `LCLid` | None. |
| `date` | The day of the consumption record | Date | String (YYYY-MM-DD) | Renamed from `day`. Padded missing days with grid join. | None. Target is matched exactly. |
| `consumption_kwh`| The total electricity consumed over the day | kWh | Float | Renamed from `energy_sum`. Filtered to selected period. | None. Target variable only. |

**Transformations NOT performed:** `energy_mean`, `energy_max`, `energy_min`, `energy_median`, `energy_std`, `energy_count` were EXCLUDED to prevent target-period leakage. Missing data was NOT imputed.

---

## 2. `v2_household_metadata.csv`
**Source:** `data/raw/informations_households.csv`
**Description:** Static metadata for households present in the V2 consumption dataset.

| Column | Meaning | Unit | Data Type | Transformations Performed | Leakage Considerations |
|---|---|---|---|---|---|
| `household_id` | Unique identifier | ID | String | Renamed from `LCLid`, filtered. | None. |
| `Acorn` | Detailed socio-demographic grouping | Category| String | None | Static mapping, no temporal leak. |
| `Acorn_grouped`| High-level demographic grouping (Affluent, etc.) | Category| String | None | Static mapping, no temporal leak. |
| `stdorToU` | Tariff type (Standard or Time-of-Use) | Category| String | None | Assumed static over time. |

---

## 3. `v2_weather_daily.csv`
**Source:** `data/raw/weather_daily_darksky.csv`
**Description:** Daily historical meteorological data.

| Column | Meaning | Unit | Data Type | Transformations Performed | Leakage Considerations |
|---|---|---|---|---|---|
| `date` | Observation date | Date | String (YYYY-MM-DD) | Extracted from `time`. Filtered to match consumption range. | None. Source is strictly historical. |
| `temperatureMax` | Maximum daily temperature | °C | Float | None | None |
| `temperatureMin` | Minimum daily temperature | °C | Float | None | None |
| `cloudCover` | Fractional cloud cover | 0-1 | Float | None | None |
| `windSpeed` | Average wind speed | m/s | Float | None | None |
| `humidity` | Relative humidity | 0-1 | Float | None | None |
| `precipType` | Type of precipitation (rain, snow) | Category| String | None | None |
| `pressure` | Atmospheric pressure | hPa | Float | None | None |
| `visibility` | Average visibility | km | Float | None | None |
| `dewPoint` | Dew point temperature | °C | Float | None | None |

---

## 4. `v2_bank_holidays.csv`
**Source:** `data/raw/uk_bank_holidays.csv`
**Description:** Canonical UK bank holidays overlapping the V2 period.

| Column | Meaning | Unit | Data Type | Transformations Performed | Leakage Considerations |
|---|---|---|---|---|---|
| `date` | Date of the holiday | Date | String (YYYY-MM-DD) | Renamed from `Bank holidays`. Filtered to date range. | None. Calendar is deterministic. |
| `holiday_name` | Name of the holiday | Category| String | Renamed from `Type`. | None. |

