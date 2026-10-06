# Smart Meter Consumption Forecasting (V2)

## 1. Project Overview
This repository contains the V2 MVP for forecasting household electricity consumption using historical smart-meter data. The V1 implementation has been completely removed to ensure a single, reliable application architecture.

## 2. Architecture
The MVP consists of:
- **FastAPI V2 Backend**: Serves predictions and historical data, enforcing a strict separation between ML logic and API routing.
- **Next.js V2 Frontend**: A clean, manager-friendly dashboard with Light/Dark/System theme support, dynamic historical charting, and clear KPIs.
- **V2 LightGBM Model**: A trained model artifact (`models/v2/forecast_model.joblib`) relying on 13 features (autoregressive lags and rolling statistics).
- **V2 Historical Data**: Prepared parquet features (`data/processed/v2/features.parquet`) used for both feature generation and historical display.

## 3. Data Scope & Limitations
- **Historical Data**: The current dataset ends on **February 28, 2014**.
- **No Future Actuals**: The frontend and backend strictly prevent future data leakage. Forecast origin is always the latest available actual data point (e.g., Feb 28).
- **No External Data**: Forecasts are generated strictly from historical consumption patterns. The model is not connected to live smart-meter streams or external weather data.

## 4. 7-Day Forecasting Approach
Inference uses a **recursive one-step forecasting** approach. 
The model predicts Day +1, appends that prediction to the history, regenerates the features for Day +2, predicts Day +2, and repeats until Day +7.

The 13 features are strictly preserved in this order:
`lag_1, lag_2, lag_3, lag_7, lag_14, lag_28, rolling_mean_7, rolling_std_7, rolling_mean_14, rolling_std_14, rolling_mean_28, rolling_std_28, historical_mean_consumption`.

## 5. Setup Instructions
Ensure Python 3.9+ and Node.js are installed.

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend_v2
npm install
```

## 6. How to run Backend
```bash
# Using uvicorn directly
uvicorn api.v2.main:app --reload --port 8001

# Or using the batch script
run_backend.bat
```
The API will be available at `http://127.0.0.1:8001`.

## 7. How to run Frontend
In a separate terminal:
```bash
cd frontend_v2
npm run dev
```
The dashboard will be available at `http://localhost:3000`.

## 8. API Endpoints
- `GET /health`: Returns API health status and model version.
- `GET /households`: Returns a list of available household IDs.
- `GET /history/{household_id}?days=N`: Returns chronological historical consumption up to `N` days (30, 90, 180, 365) before the forecast origin.
- `GET /forecast/{household_id}`: Returns a 7-day recursive forecast and calculated insights for the specified household.
- `GET /metrics`: Returns the historical backtest performance metrics.

## 9. Testing
**Backend API Tests:**
```bash
python -m unittest tests/api/v2/test_api.py -v
```

**Forecast Service Tests:**
```bash
python -m unittest tests/v2/test_forecast_service.py -v
```

**Frontend Build:**
```bash
cd frontend_v2
npm run build
```
