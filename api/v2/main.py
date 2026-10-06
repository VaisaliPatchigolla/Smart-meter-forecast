from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import sys

# Ensure src is importable
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.services.v2.forecast_service import ForecastService, HouseholdNotFoundError, InsufficientHistoryError, ForecastGenerationError
from api.v2 import schemas

app = FastAPI(
    title="Smart Meter Consumption Forecasting API - V2",
    version="2.0.0",
    description="This is a historical forecasting demonstration. The current dataset ends on 2014-02-28 and is not connected to live smart meter data or future weather forecasts."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
forecast_service: ForecastService = None

@app.on_event("startup")
def startup_event():
    global forecast_service
    # Initialize the service exactly once
    model_path = "models/v2/forecast_model.joblib"
    data_path = "data/processed/v2/features.parquet"
    try:
        forecast_service = ForecastService(model_path=model_path, data_path=data_path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to load forecast service on startup: {str(e)}")

@app.get("/health", response_model=schemas.HealthResponse)
def health_check():
    if forecast_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast service is currently unavailable"
        )
    return {
        "status": "healthy",
        "model_version": "v2_demand_history"
    }

@app.get("/households", response_model=schemas.HouseholdsResponse)
def get_households():
    if forecast_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast service is currently unavailable"
        )
        
    unique_households = forecast_service.df['household_id'].unique().tolist()
    return {
        "households": unique_households,
        "total": len(unique_households)
    }

@app.get("/forecast/{household_id}", response_model=schemas.ForecastResponse)
def get_forecast(household_id: str):
    if forecast_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast service is currently unavailable"
        )
        
    try:
        # Generate the forecast
        forecast_result = forecast_service.recursive_forecast(household_id=household_id)
        return forecast_result
        
    except HouseholdNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found"
        )
    except InsufficientHistoryError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient historical data for forecasting"
        )
    except Exception as e:
        # Catch ForecastGenerationError and any other unexpected exceptions as 500
        # Do not expose the python stack trace or raw exception internally
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate forecast"
        )

@app.get("/metrics", response_model=schemas.MetricsResponse)
def get_metrics():
    # Validated V2 MVP historical backtest metrics
    return {
        "model_type": "LightGBM (Recursive Autoregressive)",
        "model_version": "v2_demand_history",
        "forecast_horizon_days": 7,
        "v2_mae_7d": 2.3101,
        "baseline_mae_7d": 2.8184,
        "improvement_pct": 18.04,
        "disclaimer": "Metrics represent historical backtest performance. Actual future error may vary."
    }

@app.get(
    "/history/{household_id}", 
    response_model=schemas.HistoryResponse,
    description="Return recent actual electricity consumption for a household. This endpoint returns historical observations only and does not generate forecasts."
)
def get_history(household_id: str, days: int = 365):
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days must be a positive integer"
        )
        
    if forecast_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecast service is currently unavailable"
        )
        
    try:
        recent_df = forecast_service.get_recent_history(household_id, days=days)
        
        # Ensure it's chronological (oldest -> newest) as returned by get_recent_history
        # get_recent_history returns the chunk naturally ordered if the source was ordered.
        # But let's explicitly enforce it just to be perfectly compliant.
        recent_df = recent_df.sort_values('date')
        
        history_list = []
        for _, row in recent_df.iterrows():
            history_list.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "consumption_kwh": float(row['consumption_kwh'])
            })
            
        return {
            "household_id": household_id,
            "history": history_list
        }
        
    except HouseholdNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve historical data"
        )
