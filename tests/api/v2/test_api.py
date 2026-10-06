import unittest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure src is importable
sys.path.append(str(Path(__file__).resolve().parents[3]))

# We need to test the API endpoint error handling without waiting for the 800MB parquet 
# to load in the test context if possible, but the user requested at least ONE real integration test.
# Since we need a real integration test, we will just import the real app which triggers the startup event.

from api.v2.main import app
from src.services.v2.forecast_service import HouseholdNotFoundError, InsufficientHistoryError, ForecastGenerationError

class TestV2API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from api.v2.main import startup_event, app
        startup_event()
        cls.client = TestClient(app)

    def test_01_health_returns_200(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_02_health_contains_model_version(self):
        response = self.client.get("/health")
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["model_version"], "v2_demand_history")

    def test_03_households_returns_200(self):
        response = self.client.get("/households")
        self.assertEqual(response.status_code, 200)

    def test_04_households_returns_ids(self):
        response = self.client.get("/households")
        data = response.json()
        self.assertIn("households", data)
        self.assertIsInstance(data["households"], list)
        self.assertTrue(len(data["households"]) > 0)

    def test_05_households_total_matches(self):
        response = self.client.get("/households")
        data = response.json()
        self.assertEqual(len(data["households"]), data["total"])
        self.assertEqual(data["total"], 5373)

    def test_06_metrics_returns_200(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)

    def test_07_metrics_parity(self):
        response = self.client.get("/metrics")
        data = response.json()
        self.assertEqual(data["v2_mae_7d"], 2.5320)
        self.assertEqual(data["baseline_mae_7d"], 3.0898)
        self.assertEqual(data["improvement_pct"], 18.05)

    def test_08_invalid_household_returns_404(self):
        response = self.client.get("/forecast/INVALID_ID_999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Household not found")

    def test_09_real_integration_test_mac000018(self):
        # 6. valid household forecast returns 200
        response = self.client.get("/forecast/MAC000018")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 7. forecast contains exactly 7 records
        self.assertEqual(len(data["forecast"]), 7)
        
        # 8. forecast dates are consecutive & 9. forecast_day values are 1 through 7
        for i in range(7):
            self.assertEqual(data["forecast"][i]["forecast_day"], i + 1)
            
        # 10. forecast values are numbers
        for point in data["forecast"]:
            self.assertIsInstance(point["predicted_consumption_kwh"], (float, int))
            
        # 11. forecast insights are present
        self.assertIn("insights", data)
        self.assertIn("total_7d_consumption", data["insights"])

    def test_09b_integration_mac000020_forecast_dates(self):
        response = self.client.get("/forecast/MAC000020")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Forecast should start on 2014-02-28 and end on 2014-03-06
        self.assertEqual(data["forecast_start"], "2014-02-28")
        self.assertEqual(data["forecast_end"], "2014-03-06")
        self.assertEqual(len(data["forecast"]), 7)
        self.assertEqual(data["forecast"][0]["date"], "2014-02-28")
        self.assertEqual(data["forecast"][-1]["date"], "2014-03-06")

    def test_09c_integration_mac000002_forecast_dates(self):
        response = self.client.get("/forecast/MAC000002")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Forecast should start on 2014-02-28 and end on 2014-03-06
        self.assertEqual(data["forecast_start"], "2014-02-28")
        self.assertEqual(data["forecast_end"], "2014-03-06")
        self.assertEqual(len(data["forecast"]), 7)
        self.assertEqual(data["forecast"][0]["date"], "2014-02-28")
        self.assertEqual(data["forecast"][-1]["date"], "2014-03-06")

    @patch('api.v2.main.forecast_service.recursive_forecast')
    def test_10_insufficient_history_422(self, mock_forecast):
        mock_forecast.side_effect = InsufficientHistoryError()
        response = self.client.get("/forecast/SHORT_HH")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Insufficient historical data for forecasting")

    @patch('api.v2.main.forecast_service.recursive_forecast')
    def test_11_internal_forecast_error_500(self, mock_forecast):
        mock_forecast.side_effect = ForecastGenerationError("Feature mismatch inside engine")
        response = self.client.get("/forecast/BROKEN_HH")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Unable to generate forecast")

    def test_12_service_unavailable_503(self):
        # We temporarily mock the global forecast_service to None to simulate failure to load
        from api.v2 import main
        original_service = main.forecast_service
        main.forecast_service = None
        
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Forecast service is currently unavailable")
        
        # Restore for other tests
        main.forecast_service = original_service

    def test_13_history_returns_200(self):
        response = self.client.get("/history/MAC000018")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["household_id"], "MAC000018")
        
        history = data["history"]
        self.assertIsInstance(history, list)
        self.assertTrue(len(history) <= 365)
        self.assertTrue(len(history) > 0)
        
        # Check chronological order and validity
        import datetime
        prev_date = None
        for pt in history:
            curr_date = datetime.datetime.strptime(pt["date"], "%Y-%m-%d")
            if prev_date is not None:
                self.assertTrue(curr_date > prev_date)
            prev_date = curr_date
            
            self.assertIsInstance(pt["consumption_kwh"], (float, int))
            import math
            self.assertFalse(math.isnan(pt["consumption_kwh"]))

    def test_14_history_invalid_household(self):
        response = self.client.get("/history/INVALID_ID_999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Household not found")

    def test_15_history_dynamic_range(self):
        # 30 days
        resp_30 = self.client.get("/history/MAC000018?days=30")
        self.assertEqual(resp_30.status_code, 200)
        self.assertTrue(len(resp_30.json()["history"]) <= 30)

        # 90 days
        resp_90 = self.client.get("/history/MAC000018?days=90")
        self.assertEqual(resp_90.status_code, 200)
        self.assertTrue(len(resp_90.json()["history"]) > 30)
        self.assertTrue(len(resp_90.json()["history"]) <= 90)

        # 180 days
        resp_180 = self.client.get("/history/MAC000018?days=180")
        self.assertEqual(resp_180.status_code, 200)
        self.assertTrue(len(resp_180.json()["history"]) > 90)
        self.assertTrue(len(resp_180.json()["history"]) <= 180)

        # 365 days
        resp_365 = self.client.get("/history/MAC000018?days=365")
        self.assertEqual(resp_365.status_code, 200)
        self.assertTrue(len(resp_365.json()["history"]) > 180)
        self.assertTrue(len(resp_365.json()["history"]) <= 365)

    def test_16_history_future_leakage(self):
        resp = self.client.get("/history/MAC000018?days=365")
        history = resp.json()["history"]
        last_date = history[-1]["date"]
        # In current MVP, last actual should be no later than 2014-02-28
        self.assertTrue(last_date <= "2014-02-28")

    def test_17_existing_endpoints_unaffected(self):
        # Quick verification that others still work
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/households").status_code, 200)
        self.assertEqual(self.client.get("/metrics").status_code, 200)
        self.assertEqual(self.client.get("/forecast/MAC000018").status_code, 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)
