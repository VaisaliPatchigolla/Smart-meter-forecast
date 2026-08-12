import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os
import sys

# Add src to path to import metrics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.evaluation.metrics import calculate_mae, calculate_rmse

base_dir = r"c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting"
features_path = os.path.join(base_dir, "data", "processed", "features.csv")
model_path = os.path.join(base_dir, "models", "forecast_model.joblib")
report_path = os.path.join(base_dir, "reports", "model_evaluation.md")

def train_model():
    print("Loading features...")
    df = pd.read_csv(features_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Exclude rows where lag_364 is null to ensure a fair comparison for all algorithms, 
    # but the instructions specifically say "do not add unnecessary features", and 364 days lag 
    # will wipe out 1 year of train data. We'll drop rows where the target is NA or base lags are NA.
    # Actually, tree models handle NAs, but it's best to drop initial rows per household to have a stable training set.
    # Let's keep LightGBM's default NA handling, but ensure target isn't NA. Target shouldn't be NA anyway.
    
    # 3. TIME SPLIT
    train_mask = (df['date'] >= '2012-01-01') & (df['date'] <= '2013-06-30')
    val_mask = (df['date'] >= '2013-07-01') & (df['date'] <= '2013-09-30')
    test_mask = (df['date'] >= '2013-10-01') & (df['date'] <= '2013-12-31')
    
    # Validation/Leakage Check for Split
    assert (train_mask & val_mask).sum() == 0, "Train and Val overlap!"
    assert (val_mask & test_mask).sum() == 0, "Val and Test overlap!"
    assert (train_mask & test_mask).sum() == 0, "Train and Test overlap!"
    
    df_train = df[train_mask].copy()
    df_val = df[val_mask].copy()
    df_test = df[test_mask].copy()
    
    # Features list
    base_features = [
        'lag_1', 'lag_2', 'lag_3', 'lag_7', 'lag_14', 'lag_28', 'lag_364',
        'rolling_mean_7', 'rolling_std_7', 'rolling_mean_14', 'rolling_mean_28',
        'day_of_week', 'is_weekend', 'day_of_month', 'month', 'week_of_year'
    ]
    target_col = 'consumption_kwh'
    
    # Convert household_id to categorical
    df_train['household_id'] = df_train['household_id'].astype('category')
    df_val['household_id'] = df_val['household_id'].astype('category')
    df_test['household_id'] = df_test['household_id'].astype('category')
    
    # 5. BASELINE EVALUATION (Seasonal Naive = lag_7)
    # The dataset has lag_7 which is exactly consumption(T-7)
    val_baseline_preds = df_val['lag_7']
    test_baseline_preds = df_test['lag_7']
    
    # Remove NaNs for baseline evaluation if any exist in the test/val period 
    # (Since date starts 2013-07-01, lag_7 is fully populated)
    baseline_val_mae = calculate_mae(df_val[target_col], val_baseline_preds)
    baseline_val_rmse = calculate_rmse(df_val[target_col], val_baseline_preds)
    
    baseline_test_mae = calculate_mae(df_test[target_col], test_baseline_preds)
    baseline_test_rmse = calculate_rmse(df_test[target_col], test_baseline_preds)
    
    print(f"Baseline Val MAE: {baseline_val_mae:.4f}")
    
    # 6. MODEL EXPERIMENTS
    lgb_params = {
        'objective': 'regression',
        'metric': 'mae',
        'random_state': 42,
        'n_estimators': 100, # keep it simple for MVP
        'learning_rate': 0.1,
        'verbose': -1
    }
    
    experiments = {}
    
    # A. Raw target, no household_id
    print("Running Exp A...")
    model_A = lgb.LGBMRegressor(**lgb_params)
    model_A.fit(df_train[base_features], df_train[target_col])
    preds_A = model_A.predict(df_val[base_features])
    experiments['A'] = {
        'desc': 'Raw target, no household_id',
        'features': base_features,
        'categorical': [],
        'log_target': False,
        'mae': calculate_mae(df_val[target_col], preds_A),
        'rmse': calculate_rmse(df_val[target_col], preds_A)
    }
    
    # B. Raw target + household_id
    print("Running Exp B...")
    features_B = base_features + ['household_id']
    model_B = lgb.LGBMRegressor(**lgb_params)
    model_B.fit(df_train[features_B], df_train[target_col], categorical_feature=['household_id'])
    preds_B = model_B.predict(df_val[features_B])
    experiments['B'] = {
        'desc': 'Raw target, with household_id',
        'features': features_B,
        'categorical': ['household_id'],
        'log_target': False,
        'mae': calculate_mae(df_val[target_col], preds_B),
        'rmse': calculate_rmse(df_val[target_col], preds_B)
    }
    
    # C. log1p target, no household_id
    print("Running Exp C...")
    target_log_train = np.log1p(df_train[target_col])
    model_C = lgb.LGBMRegressor(**lgb_params)
    model_C.fit(df_train[base_features], target_log_train)
    preds_C_log = model_C.predict(df_val[base_features])
    preds_C = np.expm1(preds_C_log)
    experiments['C'] = {
        'desc': 'Log1p target, no household_id',
        'features': base_features,
        'categorical': [],
        'log_target': True,
        'mae': calculate_mae(df_val[target_col], preds_C),
        'rmse': calculate_rmse(df_val[target_col], preds_C)
    }
    
    # D. log1p target + household_id
    print("Running Exp D...")
    model_D = lgb.LGBMRegressor(**lgb_params)
    model_D.fit(df_train[features_B], target_log_train, categorical_feature=['household_id'])
    preds_D_log = model_D.predict(df_val[features_B])
    preds_D = np.expm1(preds_D_log)
    experiments['D'] = {
        'desc': 'Log1p target, with household_id',
        'features': features_B,
        'categorical': ['household_id'],
        'log_target': True,
        'mae': calculate_mae(df_val[target_col], preds_D),
        'rmse': calculate_rmse(df_val[target_col], preds_D)
    }
    
    # 7. MODEL SELECTION
    best_exp = None
    best_mae = float('inf')
    best_rmse = float('inf')
    
    for key, res in experiments.items():
        print(f"Exp {key}: MAE={res['mae']:.4f}, RMSE={res['rmse']:.4f}")
        # Tie-breaker logic using RMSE if MAE is within 0.001
        if res['mae'] < best_mae - 0.001:
            best_mae = res['mae']
            best_rmse = res['rmse']
            best_exp = key
        elif abs(res['mae'] - best_mae) <= 0.001:
            if res['rmse'] < best_rmse:
                best_mae = res['mae']
                best_rmse = res['rmse']
                best_exp = key
                
    best_config = experiments[best_exp]
    print(f"Selected Config: {best_exp} ({best_config['desc']})")
    
    # 8. FINAL TRAINING
    print("Training final model on Train + Validation...")
    df_train_val = pd.concat([df_train, df_val]).copy()
    
    final_model = lgb.LGBMRegressor(**lgb_params)
    
    target_final = np.log1p(df_train_val[target_col]) if best_config['log_target'] else df_train_val[target_col]
    
    # Check if household_id is used to pass categorical_feature parameter
    fit_kwargs = {}
    if 'household_id' in best_config['categorical']:
        fit_kwargs['categorical_feature'] = ['household_id']
        
    final_model.fit(df_train_val[best_config['features']], target_final, **fit_kwargs)
    
    print("Evaluating on Test Set...")
    test_preds_raw = final_model.predict(df_test[best_config['features']])
    test_preds = np.expm1(test_preds_raw) if best_config['log_target'] else test_preds_raw
    
    model_test_mae = calculate_mae(df_test[target_col], test_preds)
    model_test_rmse = calculate_rmse(df_test[target_col], test_preds)
    
    print(f"Model Test MAE: {model_test_mae:.4f}")
    
    # 9. FINAL COMPARISON
    mae_improvement = ((baseline_test_mae - model_test_mae) / baseline_test_mae) * 100
    beats_baseline = model_test_mae < baseline_test_mae
    
    # 10. MODEL ARTIFACT
    model_package = {
        'model': final_model,
        'features': best_config['features'],
        'categorical': best_config['categorical'],
        'log_target': best_config['log_target']
    }
    joblib.dump(model_package, model_path)
    
    # 11. OUTPUTS / FINAL REPORT
    report_content = f"""# Model Evaluation Report

## Dataset Information
- **Training Rows**: {len(df_train)}
- **Validation Rows**: {len(df_val)}
- **Test Rows**: {len(df_test)}
- **Feature Count**: {len(best_config['features'])}
- **Train Period**: 2012-01-01 to 2013-06-30
- **Validation Period**: 2013-07-01 to 2013-09-30
- **Test Period**: 2013-10-01 to 2013-12-31

## Model Selection (Validation Set)
- Baseline Validation MAE: {baseline_val_mae:.4f}
- Baseline Validation RMSE: {baseline_val_rmse:.4f}

### Experiments
- A (Raw target, no household_id): MAE={experiments['A']['mae']:.4f}, RMSE={experiments['A']['rmse']:.4f}
- B (Raw target, with household_id): MAE={experiments['B']['mae']:.4f}, RMSE={experiments['B']['rmse']:.4f}
- C (Log1p target, no household_id): MAE={experiments['C']['mae']:.4f}, RMSE={experiments['C']['rmse']:.4f}
- D (Log1p target, with household_id): MAE={experiments['D']['mae']:.4f}, RMSE={experiments['D']['rmse']:.4f}

### Selected Configuration
- **Best Experiment**: {best_exp} ({best_config['desc']})
- **Log1p transformation helped?**: {'Yes' if best_config['log_target'] else 'No'}
- **Household_id helped?**: {'Yes' if 'household_id' in best_config['categorical'] else 'No'}

## Final Test Evaluation
- **Baseline Test MAE**: {baseline_test_mae:.4f}
- **Baseline Test RMSE**: {baseline_test_rmse:.4f}
- **Model Test MAE**: {model_test_mae:.4f}
- **Model Test RMSE**: {model_test_rmse:.4f}
- **MAE Improvement**: {mae_improvement:.2f}%
- **Beats Baseline?**: {'Yes' if beats_baseline else 'No'}

## 7-Day Recursive Forecasting Approach
For inference (handled in `src/models/predict.py`), the model uses a one-step recursive approach to forecast 7 days ahead:
1. The historical lag and rolling features are calculated using the available true consumption up to Day T.
2. The model predicts Day T+1.
3. The prediction for Day T+1 is temporarily appended to the historical dataset.
4. The lag and rolling features for Day T+2 are regenerated using this updated temporary history.
5. The model predicts Day T+2.
6. This sequence recurses until Day T+7. 
This ensures the model properly responds to its own predictions for short-term dependencies, without polluting the original processed dataset.

## Known Limitations
- LightGBM was trained with default parameters; hyperparameter tuning was skipped for this MVP.
- Recursive forecasting can accumulate errors exponentially if the model makes a poor initial prediction.
- Weather features are absent, making the model blind to actual temperature fluctuations (relying solely on historical lags).

**Model saved to**: {model_path}
"""
    
    with open(report_path, 'w') as f:
        f.write(report_content)
        
    print(f"Report generated at {report_path}")

if __name__ == "__main__":
    train_model()
