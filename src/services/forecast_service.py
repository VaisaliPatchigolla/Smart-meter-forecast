import pandas as pd
import numpy as np
import joblib
import os
import sys

base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
model_path = os.path.join(base_dir, "models", "forecast_model.joblib")
data_path = os.path.join(base_dir, "data", "processed", "household_daily_100.csv")

# Import the feature generation from predict.py to reuse logic
sys.path.append(os.path.join(base_dir))
from src.models.predict import generate_features_for_day, recursive_forecast

class ForecastService:
    def __init__(self):
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model artifact not found.")
        if not os.path.exists(data_path):
            raise FileNotFoundError("Processed historical data not found.")
            
        self.model_package = joblib.load(model_path)
        self.history_df = pd.read_csv(data_path)
        self.history_df['date'] = pd.to_datetime(self.history_df['date'])
        
        # Get list of valid households
        self.valid_households = sorted(self.history_df['household_id'].unique().tolist())
        
    def get_households(self):
        return self.valid_households
        
    def get_forecast(self, household_id):
        if household_id not in self.valid_households:
            raise ValueError(f"Household {household_id} not found.")
            
        hh_history = self.history_df[self.history_df['household_id'] == household_id].copy()
        latest_date = hh_history['date'].max()
        start_date = latest_date + pd.Timedelta(days=1)
        
        # We can just use the recursive_forecast function from predict.py
        forecast_df = recursive_forecast(
            model_package=self.model_package,
            history_df=self.history_df,
            household_id=household_id,
            start_date=start_date,
            steps=7
        )
        
        forecast_list = []
        for _, row in forecast_df.iterrows():
            forecast_list.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "predicted_consumption_kwh": float(row['forecast_kwh'])
            })
            
        return {
            "household_id": household_id,
            "forecast_horizon_days": 7,
            "forecast": forecast_list
        }
