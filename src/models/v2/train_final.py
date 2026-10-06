import pandas as pd
import numpy as np
import lightgbm as lgb
import json
import joblib

def main():
    print("Re-training best non-oracle model (Experiment A)...")
    df = pd.read_parquet('data/processed/v2/features.parquet')
    df = df.dropna(subset=['consumption_kwh']).reset_index(drop=True)
    
    train_end = pd.to_datetime('2013-06-30')
    val_start = pd.to_datetime('2013-07-01')
    val_end = pd.to_datetime('2013-09-30')
    
    train_mask = df['date'] <= train_end
    val_mask = (df['date'] >= val_start) & (df['date'] <= val_end)
    
    df_train = df[train_mask]
    df_val = df[val_mask]
    
    features = [c for c in df.columns if 'lag' in c or 'rolling' in c or 'historical' in c]
    
    X_train = df_train[features]
    X_val = df_val[features]
    y_train = df_train['consumption_kwh']
    y_val = df_val['consumption_kwh']
    
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
    
    model = lgb.LGBMRegressor(**lgb_params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )
    
    joblib.dump(model, 'models/v2/forecast_model.joblib')
    with open('models/v2/best_features.json', 'w') as f:
        json.dump(features, f)
        
    print("Saved Experiment A as final model.")

if __name__ == '__main__':
    main()
