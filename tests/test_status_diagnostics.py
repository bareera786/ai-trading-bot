import unittest

from scripts import status_diagnostics as diag


class AnalyzeStatusTests(unittest.TestCase):
    def test_flags_underperforming_models_and_activity(self) -> None:
        payload = {
            "ultimate": {
                "summary": {
                    "avg_accuracy_percent": 45.0,
                    "low_accuracy_models": 3,
                    "low_accuracy_threshold": 65,
                    "stale_models": 1,
                    "stale_threshold_hours": 18,
                    "latest_training_age_hours": 20.0,
                    "model_count": 7,
                    "latest_training_display": "2025-11-10 12:00",
                }
            },
            "system_status": {
                "trading_enabled": True,
                "ml_system_available": True,
                "models_loaded": True,
                "ensemble_active": False,
                "indicators_used": 28,
                "last_trade": None,
            },
            "performance": {
                "total_trades": 0,
                "win_rate": 0.0,
            },
        }

        thresholds = diag.StatusThresholds(
            min_accuracy_percent=60.0,
            max_model_age_hours=12.0,
            min_indicator_count=30,
            min_total_trades=1,
        )

        issues, summaries = diag.analyze_status(payload, thresholds)
        self.assertTrue(summaries, "Expected diagnostic summary lines to be returned")

        messages = {issue.message for issue in issues}
        self.assertIn("Average accuracy 45.00% below minimum 60.00%", messages)
        self.assertIn("3 models < 65%", messages)
        self.assertIn("1 models stale beyond 18.0h", messages)
        self.assertIn("Latest training age 20.0h exceeds 12.0h", messages)
        self.assertIn("Only 0 trades executed (< 1)", messages)
        self.assertIn("Win rate is zero", messages)

        severities = {issue.severity for issue in issues}
        self.assertIn("error", severities)
        self.assertIn("warning", severities)

    def test_passes_for_healthy_payload(self) -> None:
        payload = {
            "ultimate": {
                "summary": {
                    "avg_accuracy_percent": 72.0,
                    "low_accuracy_models": 0,
                    "stale_models": 0,
                    "latest_training_age_hours": 2.0,
                    "model_count": 12,
                    "latest_training_display": "2025-11-11 23:10",
                }
            },
            "system_status": {
                "trading_enabled": True,
                "ml_system_available": True,
                "models_loaded": True,
                "ensemble_active": True,
                "indicators_used": 36,
                "last_trade": "2025-11-11T23:05:00",
            },
            "performance": {
                "total_trades": 6,
                "win_rate": 0.5,
            },
        }

        thresholds = diag.StatusThresholds(
            min_accuracy_percent=60.0,
            max_model_age_hours=12.0,
            min_indicator_count=30,
            min_total_trades=1,
        )

        issues, summaries = diag.analyze_status(payload, thresholds)
        self.assertTrue(summaries)
        self.assertFalse(issues)


if __name__ == "__main__":
    unittest.main()
