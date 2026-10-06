import sys
from pathlib import Path
import traceback

sys.path.append(str(Path(__file__).resolve().parent))

from src.services.v2.forecast_service import ForecastService

model_path = "models/v2/forecast_model.joblib"
data_path = "data/processed/v2/features.parquet"

try:
    forecast_service = ForecastService(model_path=model_path, data_path=data_path)
    print("SUCCESS")
except Exception as e:
    print("FAILED")
    traceback.print_exc()
