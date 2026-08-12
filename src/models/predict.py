import pandas as pd
import numpy as np
import joblib
import os
import sys

base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
model_path = os.path.join(base_dir, "models", "forecast_model.joblib")

def generate_features_for_day(history_df, target_date):
    """
    Given a history of actuals and previous predictions for a single household,
    generates the features required to predict 'target_date'.
    """
    # Create a dummy row for the target date
    dummy_row = pd.DataFrame({'date': [target_date]})
    df = pd.concat([history_df, dummy_row], ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)
    
    # Calculate lags
    lags = [1, 2, 3, 7, 14, 28, 364]
    for lag in lags:
        df[f'lag_{lag}'] = df['consumption_kwh'].shift(lag)
        
    # Calculate rolling features (shift(1) ensures target date is purely based on historical values)
    shifted_cons = df['consumption_kwh'].shift(1)
    df['rolling_mean_7'] = shifted_cons.rolling(7).mean()
    df['rolling_std_7'] = shifted_cons.rolling(7).std()
    df['rolling_mean_14'] = shifted_cons.rolling(14).mean()
    df['rolling_mean_28'] = shifted_cons.rolling(28).mean()
    
    # Calendar features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
    
    # Return just the features for the target_date
    target_row = df[df['date'] == target_date].copy()
    return target_row

def recursive_forecast(model_package, history_df, household_id, start_date, steps=7):
    """
    Implements recursive forecasting.
    
    1. Uses actual history to predict Day +1.
    2. Appends Day +1 prediction to the temporary history.
    3. Generates Day +2 features using the updated history.
    4. Predicts Day +2, and repeats until Day +7.
    """
    model = model_package['model']
    feature_cols = model_package['features']
    log_target = model_package['log_target']
    
    # Isolate history for the household
    hh_history = history_df[history_df['household_id'] == household_id].copy()
    
    predictions = []
    current_date = start_date
    
    for step in range(steps):
        # 1. Generate features for the current step based on temporary history
        current_features = generate_features_for_day(hh_history, current_date)
        current_features['household_id'] = household_id
        
        # Format for model
        if 'household_id' in feature_cols:
            current_features['household_id'] = current_features['household_id'].astype('category')
            
        X = current_features[feature_cols]
        
        # 2. Predict
        pred_raw = model.predict(X)[0]
        pred_kwh = np.expm1(pred_raw) if log_target else pred_raw
        predictions.append({'date': current_date, 'forecast_kwh': pred_kwh})
        
        # 3. Append to temporary history for the next recursive step
        new_row = pd.DataFrame({
            'household_id': [household_id],
            'date': [current_date],
            'consumption_kwh': [pred_kwh]
        })
        hh_history = pd.concat([hh_history, new_row], ignore_index=True)
        
        # Advance date
        current_date = current_date + pd.Timedelta(days=1)
        
    return pd.DataFrame(predictions)

if __name__ == "__main__":
    pass
