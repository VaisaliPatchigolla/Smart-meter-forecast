# Smart Meter Consumption Forecasting MVP

## 1. Project Overview
This repository contains a 3-day MVP for forecasting household electricity consumption using historical smart-meter data.

## 2. Business Problem
Energy providers need to anticipate household electricity demand to support better energy planning. This MVP demonstrates the capability to generate reliable 7-day forecasts at the individual household level using historical smart meter readings.

## 3. Architecture
The MVP consists of:
- **Data Pipeline**: Cleans and prepares historical readings into a unified format.
- **Feature Engineering**: Generates autoregressive lags and rolling windows.
- **ML Model**: A global LightGBM model trained across households.
- **API**: A FastAPI backend providing inference via recursive forecasting.
- **Dashboard**: A Streamlit application for end-users to view predictions.

## 4. Data Strategy
**The raw Kaggle dataset is intentionally excluded from Git.** 
The MVP runs using a perfectly clean, processed 100-household dataset containing 2 years of daily consumption history per household. Missing values, duplicates, and negative consumption values were strictly filtered out during preparation.

## 5. Model
- **Algorithm**: LightGBM
- **Target**: log1p(consumption_kwh)
- **Features**: Lag 1,2,3,7,14,28,364; Rolling Mean/Std 7,14,28; Calendar features.
- **Household Encoding**: Categorical feature.

## 6. 7-Day Forecasting Approach
Inference uses a **recursive one-step forecasting** approach. 
The model predicts Day +1, appends that prediction to the history, regenerates the features for Day +2, predicts Day +2, and repeats until Day +7. This prevents target leakage and accurately reflects short-term trajectory dependencies.

## 7. Validation Result
A rigorous true 7-day recursive backtest was performed over the unseen 3-month winter test period.
- **True 7-Day Baseline MAE**: 3.0898 kWh
- **True 7-Day ML MAE**: 2.5320 kWh
- **Improvement**: 18.05%

## 8. Setup Instructions
Ensure Python 3.9+ is installed.
```bash
pip install -r requirements.txt
```

## 9. How to run API
```bash
uvicorn api.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## 10. How to run Dashboard
Ensure the API is running, then in a separate terminal execute:
```bash
streamlit run dashboard/app.py
```

## 11. API Endpoints
- `GET /health`: Returns API health status.
- `GET /households`: Returns a list of the 100 available household IDs.
- `GET /forecast/{household_id}`: Returns a 7-day recursive forecast for the specified household.
- `GET /metrics/{household_id}`: Returns the overall model metrics.

## 12. Limitations
- **No Weather Data**: The model is completely blind to actual temperature fluctuations and relies entirely on autoregressive patterns to proxy weather.
- **Error Accumulation**: Recursive forecasting naturally accumulates error toward Day 7 if early predictions drift.
- **Default Hyperparameters**: The LightGBM model was not tuned for optimal performance.

## 13. Future Improvements
- Integrate DarkSky weather regressors (temperature, humidity).
- Tune LightGBM hyperparameters (learning rate, num_leaves, max_depth).
- Implement direct multi-step forecasting instead of recursive.
