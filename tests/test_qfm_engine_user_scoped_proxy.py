from __future__ import annotations

from app.runtime.context import UserScopedProxy


class _DummyQFMEngine:
    def __init__(self):
        self.state = {}
        self.analytics_cache = {}

    def run_analysis(self):
        # Simulate a user-facing mutation path.
        count = int(self.state.get("runs", 0)) + 1
        self.state["runs"] = count
        self.analytics_cache["last"] = f"run{count}"
        return {"runs": count, "last": self.analytics_cache["last"]}


def test_user_scoped_qfm_engine_does_not_leak_state_across_users():
    current_user_id = None

    def user_id_provider():
        return current_user_id

    base = _DummyQFMEngine()
    proxy = UserScopedProxy(base=base, factory=_DummyQFMEngine, user_id_provider=user_id_provider)

    current_user_id = 1
    result1 = proxy.run_analysis()
    assert result1["runs"] == 1
    assert proxy.state["runs"] == 1

    current_user_id = 2
    result2 = proxy.run_analysis()
    assert result2["runs"] == 1
    assert proxy.state["runs"] == 1

    # Ensure user 1's engine state is unchanged by user 2.
    current_user_id = 1
    assert proxy.state["runs"] == 1
    assert proxy.analytics_cache["last"] == "run1"

    # And vice-versa.
    current_user_id = 2
    assert proxy.state["runs"] == 1
    assert proxy.analytics_cache["last"] == "run1"
