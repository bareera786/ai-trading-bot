import os
import pytest

pytest.importorskip("playwright")

TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:5000")


@pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1", reason="E2E tests disabled (set RUN_E2E=1)"
)
def test_deploy_shows_toast(page):
    """Navigate to RIBS dashboard, attempt a deploy, and assert a toast appears."""
    # Load the RIBS page
    page.goto(f"{TARGET_URL}/ribs")

    # Override window.confirm to auto-accept the confirmation
    page.evaluate("() => { window.confirm = () => true; }")

    # Ensure the toast container exists
    assert page.query_selector("#ribs-toast-container") is not None

    # Execute the deploy JS (triggering a network request that should fail for a nonexistent strategy)
    page.evaluate("() => deployRIBSStrategy('nonexistent_strategy_test')")

    # Wait for a toast to appear
    toast = page.wait_for_selector("#ribs-toast-container .ribs-toast", timeout=5000)
    assert toast is not None
    text = toast.text_content() or ""
    assert any(
        k in text.lower()
        for k in ("deploy", "failed", "error", "not found", "forbidden")
    )
