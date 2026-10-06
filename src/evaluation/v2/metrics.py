import numpy as np

def mean_absolute_error(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not mask.any():
        return np.nan
    return np.mean(np.abs(y_true[mask] - y_pred[mask]))

def root_mean_squared_error(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not mask.any():
        return np.nan
    return np.sqrt(np.mean((y_true[mask] - y_pred[mask])**2))

def smape(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not mask.any():
        return np.nan
    y_t = y_true[mask]
    y_p = y_pred[mask]
    
    denominator = (np.abs(y_t) + np.abs(y_p)) / 2.0
    
    # Avoid division by zero when both true and pred are exactly zero
    nonzero_mask = denominator != 0
    if not nonzero_mask.any():
        return 0.0
        
    return np.mean(np.abs(y_t[nonzero_mask] - y_p[nonzero_mask]) / denominator[nonzero_mask]) * 100
