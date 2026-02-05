import pickle

import pytest

pytest.importorskip("flask_mail")

from ai_ml_auto_bot_final import ParallelPredictionEngine


def test_parallel_engine_pickling_restores_logger():
    pe = ParallelPredictionEngine()
    # remove logger to simulate earlier issue
    if hasattr(pe, "logger"):
        delattr(pe, "logger")

    data = pickle.dumps(pe)
    pe2 = pickle.loads(data)
    assert hasattr(pe2, "logger") and pe2.logger is not None
