export interface HealthResponse {
  status: string;
  model_version: string;
}

export interface HouseholdsResponse {
  households: string[];
  total: number;
}

export interface ForecastPoint {
  date: string;
  forecast_day: number;
  predicted_consumption_kwh: number;
}

export interface ForecastInsights {
  total_7d_consumption: number;
  average_daily_consumption: number;
  peak_consumption_day: string;
  lowest_consumption_day: string;
  peak_consumption_kwh: number;
  lowest_consumption_kwh: number;
  trend: string;
  vs_prior_7d_pct: number;
  prediction_interval: string;
}

export interface ForecastResponse {
  household_id: string;
  forecast_start: string;
  forecast_end: string;
  forecast: ForecastPoint[];
  insights: ForecastInsights;
}

export interface MetricsResponse {
  model_type: string;
  model_version: string;
  forecast_horizon_days: number;
  v2_mae_7d: number;
  baseline_mae_7d: number;
  improvement_pct: number;
  disclaimer: string;
}

export interface HistoryPoint {
  date: string;
  consumption_kwh: number;
}

export interface HistoryResponse {
  household_id: string;
  history: HistoryPoint[];
}
