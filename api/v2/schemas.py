from pydantic import BaseModel, Field
from typing import List, Optional

class HealthResponse(BaseModel):
    status: str
    model_version: str

class HouseholdsResponse(BaseModel):
    households: List[str]
    total: int

class ForecastPoint(BaseModel):
    date: str
    forecast_day: int
    predicted_consumption_kwh: float

class ForecastInsights(BaseModel):
    total_7d_consumption: float
    average_daily_consumption: float
    peak_consumption_day: str
    lowest_consumption_day: str
    peak_consumption_kwh: float
    lowest_consumption_kwh: float
    trend: str
    prediction_interval: str

class ForecastResponse(BaseModel):
    household_id: str
    forecast_start: str
    forecast_end: str
    forecast: List[ForecastPoint]
    insights: ForecastInsights

class MetricsResponse(BaseModel):
    model_type: str
    model_version: str
    forecast_horizon_days: int
    v2_mae_7d: float
    baseline_mae_7d: float
    improvement_pct: float
    disclaimer: str

class HistoryPoint(BaseModel):
    date: str
    consumption_kwh: float

class HistoryResponse(BaseModel):
    household_id: str
    history: List[HistoryPoint]
