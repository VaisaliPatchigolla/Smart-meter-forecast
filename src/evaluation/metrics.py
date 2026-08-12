import numpy as np

def calculate_mae(y_true, y_pred):
    return np.mean(np.abs(y_true - y_pred))

def calculate_rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred)**2))

def calculate_smape(y_true, y_pred):
    # sMAPE formula with safety for division by zero
    numerator = np.abs(y_true - y_pred)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    
    # Avoid division by zero where both true and pred are exactly 0
    safe_denominator = np.where(denominator == 0, 1e-10, denominator)
    return np.mean(numerator / safe_denominator) * 100
