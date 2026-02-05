import pytest

pytest.importorskip("flask_mail")

import os
import pickle
import tempfile
from app.services.ribs_optimizer import TradingRIBSOptimizer


def test_parallel_prediction_engine_logger_behavior():
    # Import and ensure deleting the logger doesn't raise in parallel_predict
    from ai_ml_auto_bot_final import ParallelPredictionEngine

    pe = ParallelPredictionEngine()
    # Remove logger and call with empty inputs to exercise fallback logging
    delattr(pe, "logger")
    res = pe.parallel_predict([], {}, None)
    assert isinstance(res, dict)


def test_save_checkpoint_does_not_create_zero_byte_files(monkeypatch, tmp_path):
    # Use a temporary checkpoints dir to isolate
    opt = TradingRIBSOptimizer()
    opt.checkpoints_dir = str(tmp_path)
    os.makedirs(opt.checkpoints_dir, exist_ok=True)

    # Monkeypatch pickle.dump to simulate a partial write (raise after creating file)
    real_dump = pickle.dump

    def failing_dump(obj, file):
        # write nothing and raise
        file.write(b"")
        raise RuntimeError("simulated crash during dump")

    monkeypatch.setattr(pickle, "dump", failing_dump)

    # Call save_checkpoint; it should not replace/create zero-byte final .pkl files
    opt.save_checkpoint()

    # Ensure there are no .tmp files left and no zero-byte .pkl files
    files = list(os.listdir(opt.checkpoints_dir))
    assert not any(f.endswith(".tmp") for f in files)
    assert not any(
        (
            f.endswith(".pkl")
            and os.path.getsize(os.path.join(opt.checkpoints_dir, f)) == 0
        )
        for f in files
    )

    # Restore pickle.dump
    monkeypatch.setattr(pickle, "dump", real_dump)


def test_save_checkpoint_removes_existing_zero_byte_files(tmp_path):
    opt = TradingRIBSOptimizer()
    opt.checkpoints_dir = str(tmp_path)
    os.makedirs(opt.checkpoints_dir, exist_ok=True)

    # Create a zero-byte .pkl file that should be cleaned up
    zero_path = os.path.join(opt.checkpoints_dir, "ribs_checkpoint_0000.pkl")
    open(zero_path, "wb").close()
    assert os.path.exists(zero_path)

    # Run save_checkpoint which should remove zero-byte files
    opt.save_checkpoint()

    assert not os.path.exists(zero_path)
