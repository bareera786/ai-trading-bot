import json
import threading

from app.services.persistence import _atomic_write_json, _bot_state_file_lock


def test_bot_state_atomic_write_is_single_writer_safe(tmp_path):
    """Concurrent read-modify-write must never corrupt bot_state.json."""

    state_file = tmp_path / "bot_state.json"
    _atomic_write_json(str(state_file), {"trader_state": {}, "timestamp": "t0"})

    def worker(i: int):
        # Simulate the route/persistence pattern: lock -> read -> mutate -> atomic replace.
        with _bot_state_file_lock(str(state_file)):
            with open(state_file, "r", encoding="utf-8") as handle:
                state = json.load(handle)
            trader_state = state.get("trader_state") or {}
            trader_state[f"k{i}"] = i
            state["trader_state"] = trader_state
            state["timestamp"] = f"t{i}"
            _atomic_write_json(str(state_file), state)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    with open(state_file, "r", encoding="utf-8") as handle:
        final_state = json.load(handle)

    assert isinstance(final_state, dict)
    trader_state = final_state.get("trader_state")
    assert isinstance(trader_state, dict)

    # Single-writer semantics: all keys from all writers must be present.
    for i in range(20):
        assert trader_state.get(f"k{i}") == i
