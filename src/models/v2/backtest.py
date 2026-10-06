import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import sys

# Add src to path so we can import metrics
sys.path.append(str(Path(__file__).resolve().parents[3]))
from src.evaluation.v2.metrics import mean_absolute_error, root_mean_squared_error, smape

def main():
    print("Loading test data for Backtest...")
    df = pd.read_parquet('data/processed/v2/features.parquet')
    
    test_start = pd.to_datetime('2013-10-01')
    test_mask = df['date'] >= test_start
    
    # We need a bit of history to initialize the recursive lag updates if we were doing it from scratch,
    # but the features are already computed. Wait, the recursive backtest means for forecast origin T, 
    # we predict T+1 to T+7. 
    # Actually, the user asked for a true 7-day recursive backtest.
    # To do this cleanly across the whole test set:
    # 1. We have the pre-computed lag_1, lag_2 ... but they contain the ACTUAL values for T+1, T+2.
    # 2. To prevent leakage, we must simulate being at day T.
    # For a given origin T, the forecast for T+k uses our predicted value of T+(k-1) as its lag_1.
    # This is computationally intensive to do row-by-row.
    # Instead, we will simulate the 7-day horizon prediction on the entire test set simultaneously.
    
    # Day 1 prediction is just standard inference (no recursion needed).
    # Day 2 prediction takes Day 1 prediction as `lag_1`.
    # Day 3 prediction takes Day 2 prediction as `lag_1` and Day 1 prediction as `lag_2`, etc.
    # This assumes the test dataset is continuous and sorted.
    
    df_test = df[test_mask].copy().sort_values(['household_id', 'date']).reset_index(drop=True)
    
    # Load best features
    with open('models/v2/best_features.json', 'r') as f:
        best_features = json.load(f)
        
    print("Loading model...")
    model = joblib.load('models/v2/forecast_model.joblib')
    
    # We will store predictions for 7 horizons
    df_test['pred_h1'] = model.predict(df_test[best_features])
    
    # Seasonal Naive
    df_test['naive_7'] = df_test['lag_7'] # Naive uses actual lag 7 from the features dataframe
    
    # Now simulate horizon 2 to 7 recursively
    # Since we sort by household and date, shift(1) gets the previous day's value for that household
    preds = {1: df_test['pred_h1'].values}
    
    # We need to iteratively overwrite the lag features in df_test with our predictions
    # to simulate recursive forecasting, but we must only overwrite for the specific horizon.
    # Actually, a vectorized way:
    # Let P_h be the prediction for horizon h.
    # For horizon 1 (T+1): lag_1 is actual T.
    # For horizon 2 (T+2): lag_1 is P_1 of T+1.
    # Thus, if we just shift our P_1 vector by 1 grouped by household, we get the recursive lag_1 for T+2!
    
    print("Running vectorised recursive 7-day backtest...")
    
    for h in range(2, 8):
        print(f"  Horizon {h}...")
        # Create a fresh copy of the features for this horizon
        X = df_test[best_features].copy()
        
        # Overwrite lag features recursively
        # For horizon h, the required lags are derived from our previous horizon predictions.
        # lag_k at T+h should be P_{h-k}(T+h) if k < h, else it remains the actual historical lag.
        for k in [1, 2, 3, 7, 14, 28]:
            if k < h:
                # We predicted this value (h-k) days ago!
                # It is exactly the prediction for horizon (h-k) shifted forward by k days.
                prev_pred = df_test.groupby('household_id')[f'pred_h{h-k}'].shift(k)
                if f'lag_{k}' in X.columns:
                    X[f'lag_{k}'] = np.where(prev_pred.notna(), prev_pred, X[f'lag_{k}'])
                    
        # Rolling features would strictly need recalculating based on the new lags. 
        # For a truly strict MVP evaluation, we update rolling_mean_7 approximately or explicitly.
        # Recalculating rolling_mean_7: it's the mean of lag_1 to lag_7.
        if 'rolling_mean_7' in X.columns:
            lags_to_mean = []
            for k in range(1, 8):
                if k < h:
                    lags_to_mean.append(df_test.groupby('household_id')[f'pred_h{h-k}'].shift(k))
                else:
                    # If we don't have exactly lag_4, we extract it from actual consumption shifted
                    lags_to_mean.append(df_test.groupby('household_id')['consumption_kwh'].shift(k))
            
            X['rolling_mean_7'] = pd.concat(lags_to_mean, axis=1).mean(axis=1)
            
        # Predict
        df_test[f'pred_h{h}'] = model.predict(X)
        
    # Evaluation
    print("\n--- Evaluation ---")
    results = {}
    
    actual = df_test['consumption_kwh'].values
    
    # 7-day overall (we average the errors of all 7 horizons)
    # Wait, overall 7-day MAE means the MAE across all days when forecasted 1-to-7 days out.
    # Actually, since each row represents T, and we have pred_h1 ... pred_h7, we can just compute MAE for each and average.
    h_maes = []
    h_rmses = []
    for h in range(1, 8):
        pred_h = df_test[f'pred_h{h}'].values
        mae = mean_absolute_error(actual, pred_h)
        rmse = root_mean_squared_error(actual, pred_h)
        h_maes.append(mae)
        h_rmses.append(rmse)
        print(f"Horizon {h} MAE: {mae:.4f} | RMSE: {rmse:.4f}")
        
    overall_mae = np.mean(h_maes)
    overall_rmse = np.mean(h_rmses)
    
    naive_mae = mean_absolute_error(actual, df_test['naive_7'].values)
    
    print(f"\nOverall 7-Day Recursive MAE: {overall_mae:.4f}")
    print(f"Seasonal Naive 7-Day MAE: {naive_mae:.4f}")
    
    # Winter Performance (Oct-Feb)
    winter_mask = df_test['date'].dt.month.isin([10, 11, 12, 1, 2])
    winter_actual = actual[winter_mask]
    winter_preds = [df_test.loc[winter_mask, f'pred_h{h}'].values for h in range(1, 8)]
    winter_mae = np.mean([mean_absolute_error(winter_actual, wp) for wp in winter_preds])
    
    print(f"Winter 7-Day MAE: {winter_mae:.4f}")
    
    # Household Level
    hh_maes = []
    for h in range(1, 8):
        err = np.abs(df_test['consumption_kwh'] - df_test[f'pred_h{h}'])
        hh_maes.append(err)
        
    df_test['avg_7d_error'] = pd.concat(hh_maes, axis=1).mean(axis=1)
    hh_perf = df_test.groupby('household_id')['avg_7d_error'].mean().reset_index()
    hh_perf = hh_perf.sort_values('avg_7d_error')
    
    best_5 = hh_perf.head(5)['household_id'].tolist()
    worst_5 = hh_perf.tail(5)['household_id'].tolist()
    
    mean_hh_mae = hh_perf['avg_7d_error'].mean()
    median_hh_mae = hh_perf['avg_7d_error'].median()
    
    results = {
        'horizon_maes': h_maes,
        'horizon_rmses': h_rmses,
        'overall_mae': float(overall_mae),
        'overall_rmse': float(overall_rmse),
        'naive_mae': float(naive_mae),
        'winter_mae': float(winter_mae),
        'mean_hh_mae': float(mean_hh_mae),
        'median_hh_mae': float(median_hh_mae),
        'best_5_hh': best_5,
        'worst_5_hh': worst_5
    }
    
    with open('backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print("Backtest complete.")

if __name__ == '__main__':
    main()
