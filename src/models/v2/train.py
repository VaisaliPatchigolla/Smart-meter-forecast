import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
import json
import joblib
import sys
import os

# Add src to path so we can import metrics
sys.path.append(str(Path(__file__).resolve().parents[3]))
from src.evaluation.v2.metrics import mean_absolute_error, root_mean_squared_error, smape

def main():
    print("Loading V2 Parquet dataset...")
    df = pd.read_parquet('data/processed/v2/features.parquet')
    
    # Target Handling
    print(f"Original rows: {len(df)}")
    df = df.dropna(subset=['consumption_kwh']).reset_index(drop=True)
    print(f"Valid supervised rows: {len(df)}")
    
    # Splits
    train_end = pd.to_datetime('2013-06-30')
    val_start = pd.to_datetime('2013-07-01')
    val_end = pd.to_datetime('2013-09-30')
    test_start = pd.to_datetime('2013-10-01')
    
    train_mask = df['date'] <= train_end
    val_mask = (df['date'] >= val_start) & (df['date'] <= val_end)
    test_mask = df['date'] >= test_start
    
    df_train = df[train_mask]
    df_val = df[val_mask]
    df_test = df[test_mask]
    
    print(f"Train rows: {len(df_train)} (Households: {df_train['household_id'].nunique()})")
    print(f"Val rows: {len(df_val)} (Households: {df_val['household_id'].nunique()})")
    print(f"Test rows: {len(df_test)} (Households: {df_test['household_id'].nunique()})")
    
    # Feature Groups
    demand_features = [c for c in df.columns if 'lag' in c or 'rolling' in c or 'historical' in c]
    calendar_features = ['day_of_week', 'is_weekend', 'day_of_month', 'month', 'day_of_year', 'week_of_year', 'is_month_start', 'is_month_end', 'sin_day_of_year', 'cos_day_of_year', 'sin_day_of_week', 'cos_day_of_week', 'is_bank_holiday']
    household_features = ['Acorn', 'Acorn_grouped', 'stdorToU'] # Tariff is effectively in here
    weather_features = [c for c in df.columns if 'observed_' in c]
    
    experiments = {
        'A': {'name': 'Demand history only', 'features': demand_features},
        'B': {'name': 'Demand + Calendar', 'features': demand_features + calendar_features},
        'C': {'name': 'Demand + Calendar + Household', 'features': demand_features + calendar_features + household_features},
        'D': {'name': 'Demand + Calendar + Weather (Oracle)', 'features': demand_features + calendar_features + weather_features},
        'E': {'name': 'Full V2 (Demand + Calendar + Household + Weather)', 'features': demand_features + calendar_features + household_features + weather_features}
    }
    
    # Fixed configuration
    lgb_params = {
        'objective': 'regression',
        'metric': 'mae',
        'boosting_type': 'gbdt',
        'learning_rate': 0.1,
        'num_leaves': 63,
        'feature_fraction': 0.8,
        'n_estimators': 200,
        'random_state': 42,
        'verbose': -1
    }
    
    results = {}
    
    y_train = df_train['consumption_kwh'].values
    y_val = df_val['consumption_kwh'].values
    
    best_exp = None
    best_mae = float('inf')
    best_model = None
    best_features = None
    
    for exp_id, config in experiments.items():
        print(f"\n--- Running Experiment {exp_id}: {config['name']} ---")
        features = config['features']
        
        X_train = df_train[features].copy()
        X_val = df_val[features].copy()
        
        # Convert categorical properly
        cat_cols = list(X_train.select_dtypes(exclude=[np.number, 'datetime']).columns)
        for c in household_features:
            if c in features and c not in cat_cols:
                cat_cols.append(c)
                
        for c in cat_cols:
            X_train[c] = X_train[c].astype('category')
            X_val[c] = X_val[c].astype('category')
        
        model = lgb.LGBMRegressor(**lgb_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            categorical_feature=cat_cols,
            callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
        )
        
        val_preds = model.predict(X_val)
        mae = mean_absolute_error(y_val, val_preds)
        rmse = root_mean_squared_error(y_val, val_preds)
        
        print(f"Validation MAE: {mae:.4f}")
        
        results[exp_id] = {
            'name': config['name'],
            'mae': float(mae),
            'rmse': float(rmse),
            'num_features': len(features)
        }
        
        if mae < best_mae:
            best_mae = mae
            best_exp = exp_id
            best_model = model
            best_features = features
            
    print(f"\nSelected Experiment: {best_exp} (MAE: {best_mae:.4f})")
    
    # Feature Importance for selected model
    importance = pd.DataFrame({
        'feature': best_features,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    results['best_model'] = best_exp
    results['feature_importance'] = importance.head(20).to_dict('records')
    
    with open('experiment_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print("Saving best model to models/v2/...")
    Path('models/v2').mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, 'models/v2/forecast_model.joblib')
    
    # Save the feature list of the best model so predict.py knows what to use
    with open('models/v2/best_features.json', 'w') as f:
        json.dump(best_features, f)
        
    print("Training complete.")

if __name__ == '__main__':
    main()
