# Model Evaluation Report

## Dataset Information
- **Training Rows**: 54700
- **Validation Rows**: 9200
- **Test Rows**: 9200
- **Feature Count**: 17
- **Train Period**: 2012-01-01 to 2013-06-30
- **Validation Period**: 2013-07-01 to 2013-09-30
- **Test Period**: 2013-10-01 to 2013-12-31

## Model Selection (Validation Set)
- Baseline Validation MAE: 2.2855
- Baseline Validation RMSE: 3.9432

### Experiments
- A (Raw target, no household_id): MAE=1.6254, RMSE=2.6275
- B (Raw target, with household_id): MAE=1.5866, RMSE=2.5590
- C (Log1p target, no household_id): MAE=1.5966, RMSE=2.6553
- D (Log1p target, with household_id): MAE=1.5512, RMSE=2.5955

### Selected Configuration
- **Best Experiment**: D (Log1p target, with household_id)
- **Log1p transformation helped?**: Yes
- **Household_id helped?**: Yes

## Final Test Evaluation
- **Baseline Test MAE**: 3.1087
- **Baseline Test RMSE**: 5.2806
- **Model Test MAE**: 2.2819
- **Model Test RMSE**: 3.9204
- **MAE Improvement**: 26.60%
- **Beats Baseline?**: Yes

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

**Model saved to**: c:\Users\TS6194_HARSHINI\Downloads\Smart-meter-Forecasting\models\forecast_model.joblib
