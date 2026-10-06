import pandas as pd
import numpy as np
import joblib
from pathlib import Path

class HouseholdNotFoundError(Exception):
    """Raised when the requested household ID is not found in the dataset."""
    pass

class InsufficientHistoryError(Exception):
    """Raised when the household lacks sufficient contiguous history to generate model features."""
    pass

class ForecastGenerationError(Exception):
    """Raised when an error occurs during inference (e.g. invalid feature structures)."""
    pass

class ForecastService:
    def __init__(self, model_path: str, data_path: str):
        self.model_path = Path(model_path)
        self.data_path = Path(data_path)
        
        self.model = None
        self.expected_features = [
            "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_28",
            "rolling_mean_7", "rolling_std_7", "rolling_mean_14", "rolling_std_14",
            "rolling_mean_28", "rolling_std_28", "historical_mean_consumption"
        ]
        
        self._load_model()
        self._load_data()
        
    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}")
        self.model = joblib.load(self.model_path)
        
        # Programmatically inspect the artifact's feature names
        if hasattr(self.model, 'booster_'):
            actual_features = list(self.model.booster_.feature_name())
        elif hasattr(self.model, 'feature_name_'):
            actual_features = list(self.model.feature_name_)
        else:
            raise ForecastGenerationError("Could not determine feature names from the loaded model artifact.")
            
        if actual_features != self.expected_features:
            raise ForecastGenerationError(
                f"Model artifact feature mismatch.\nExpected: {self.expected_features}\nActual: {actual_features}"
            )
        
    def _load_data(self):
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data not found at {self.data_path}")
        
        print("Loading data...")
        self.df = pd.read_parquet(self.data_path, columns=['household_id', 'date', 'consumption_kwh'])
        self.df['date'] = pd.to_datetime(self.df['date'])
        
        # Ensure it is sorted correctly so history extraction is deterministic
        self.df = self.df.sort_values(['household_id', 'date']).reset_index(drop=True)

    def validate_household(self, household_id: str, forecast_origin=None):
        hh_data = self.df[self.df['household_id'] == household_id]
        if hh_data.empty:
            raise HouseholdNotFoundError(f"Household {household_id} not found.")
            
        if forecast_origin:
            hh_data = hh_data[hh_data['date'] <= pd.to_datetime(forecast_origin)]
            
        valid_history = hh_data.dropna(subset=['consumption_kwh'])
        if len(valid_history) < 28:
            raise InsufficientHistoryError(f"Household {household_id} has insufficient valid history (<28 days).")
            
        latest_date = hh_data['date'].max()
        cutoff = latest_date - pd.Timedelta(days=28)
        recent_chunk = hh_data[hh_data['date'] > cutoff]
        if recent_chunk['consumption_kwh'].isna().any():
            raise InsufficientHistoryError(f"Household {household_id} has NaNs in the required 28-day lag window.")
            
        return True, hh_data
        
    def get_recent_history(self, household_id: str, days: int = 28, forecast_origin=None):
        """Returns recent ACTUAL history strictly before or at forecast_origin without predictions."""
        _, hh_data = self.validate_household(household_id, forecast_origin)
        latest_date = hh_data['date'].max()
        cutoff = latest_date - pd.Timedelta(days=days)
        return hh_data[hh_data['date'] > cutoff].copy()

    def generate_insights(self, forecast_df: pd.DataFrame, recent_history_df: pd.DataFrame) -> dict:
        total_forecast = float(forecast_df['predicted_consumption_kwh'].sum())
        avg_forecast = float(forecast_df['predicted_consumption_kwh'].mean())
        
        peak_idx = forecast_df['predicted_consumption_kwh'].idxmax()
        lowest_idx = forecast_df['predicted_consumption_kwh'].idxmin()
        
        peak_day = forecast_df.loc[peak_idx, 'date']
        lowest_day = forecast_df.loc[lowest_idx, 'date']
        peak_kwh = float(forecast_df.loc[peak_idx, 'predicted_consumption_kwh'])
        lowest_kwh = float(forecast_df.loc[lowest_idx, 'predicted_consumption_kwh'])
        
        recent_7d_total = float(recent_history_df['consumption_kwh'].sum())
        
        if recent_7d_total > 0:
            vs_prior_7d_pct = ((total_forecast - recent_7d_total) / recent_7d_total) * 100
        else:
            vs_prior_7d_pct = 0.0

        if vs_prior_7d_pct > 5:
            trend = "increasing"
        elif vs_prior_7d_pct < -5:
            trend = "decreasing"
        else:
            trend = "stable"
            
        return {
            "total_7d_consumption": round(total_forecast, 2),
            "average_daily_consumption": round(avg_forecast, 2),
            "peak_consumption_day": peak_day,
            "lowest_consumption_day": lowest_day,
            "peak_consumption_kwh": round(peak_kwh, 2),
            "lowest_consumption_kwh": round(lowest_kwh, 2),
            "trend": trend,
            "vs_prior_7d_pct": round(vs_prior_7d_pct, 2),
            "prediction_interval": "Prediction range derived from 28-day historical volatility."
        }

    def recursive_forecast(self, household_id: str, forecast_origin=None) -> dict:
        _, hh_data = self.validate_household(household_id, forecast_origin)
        
        # Exclude known incomplete final day from forecasting context
        incomplete_date = pd.to_datetime('2014-02-28')
        hh_data = hh_data[hh_data['date'] != incomplete_date].copy()
        
        latest_date = hh_data['date'].max()
        valid_history = hh_data.dropna(subset=['consumption_kwh'])
        
        if len(valid_history) < 28:
            raise InsufficientHistoryError(f"Household {household_id} has insufficient valid history after excluding incomplete dates.")

        
        sum_actual = valid_history['consumption_kwh'].sum()
        count_actual = len(valid_history)
        
        recent_values = valid_history['consumption_kwh'].values[-28:].tolist()
        
        # Methodology: Prediction range is derived from the household's recent 28-day 
        # historical standard deviation to capture individualized volatility.
        # We use a 1.28 multiplier (approx 80% confidence interval under normal distribution)
        # to provide a realistic visual planning range without being overly wide.
        recent_std = np.std(recent_values, ddof=1) if len(recent_values) > 1 else 2.53
        margin_of_error = 1.28 * recent_std
        
        predictions = []
        current_date = latest_date
        
        for day in range(1, 8):
            current_date += pd.Timedelta(days=1)
            
            lag_1 = recent_values[-1]
            lag_2 = recent_values[-2]
            lag_3 = recent_values[-3]
            lag_7 = recent_values[-7]
            lag_14 = recent_values[-14]
            lag_28 = recent_values[-28]
            
            rolling_mean_7 = np.mean(recent_values[-7:])
            rolling_std_7 = np.std(recent_values[-7:], ddof=1) if len(recent_values[-7:]) > 1 else np.nan
            
            rolling_mean_14 = np.mean(recent_values[-14:])
            rolling_std_14 = np.std(recent_values[-14:], ddof=1) if len(recent_values[-14:]) > 1 else np.nan
            
            rolling_mean_28 = np.mean(recent_values[-28:])
            rolling_std_28 = np.std(recent_values[-28:], ddof=1) if len(recent_values[-28:]) > 1 else np.nan
            
            hist_mean = sum_actual / count_actual if count_actual > 0 else np.nan
            
            feature_row = [
                lag_1, lag_2, lag_3, lag_7, lag_14, lag_28,
                rolling_mean_7, rolling_std_7, rolling_mean_14, rolling_std_14,
                rolling_mean_28, rolling_std_28, hist_mean
            ]
            
            X_infer = pd.DataFrame([feature_row], columns=self.expected_features)
            
            if list(X_infer.columns) != self.expected_features:
                raise ForecastGenerationError("Feature ordering mismatch during inference.")
                
            pred_kwh = float(self.model.predict(X_infer)[0])
            
            predictions.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "forecast_day": day,
                "predicted_consumption_kwh": round(pred_kwh, 4),
                "predicted_upper_kwh": round(pred_kwh + margin_of_error, 4),
                "predicted_lower_kwh": round(max(0.0, pred_kwh - margin_of_error), 4)
            })
            
            recent_values.append(pred_kwh)
            recent_values.pop(0) 
            
            sum_actual += pred_kwh
            count_actual += 1

        forecast_df = pd.DataFrame(predictions)
        recent_history_df = hh_data[hh_data['date'] > (latest_date - pd.Timedelta(days=7))]
        insights = self.generate_insights(forecast_df, recent_history_df)
        
        return {
            "household_id": household_id,
            "forecast_start": predictions[0]['date'],
            "forecast_end": predictions[-1]['date'],
            "forecast": predictions,
            "insights": insights
        }
