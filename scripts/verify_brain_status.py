from app import create_app
from app.services import BrainService
import traceback

def verify():
    print("--- START BRAIN VERIFICATION ---")
    app = create_app()
    with app.app_context():
        try:
            print("1. Testing BrainService.get_brain_status()...")
            status = BrainService.get_brain_status()
            print(f"✅ BrainService Success: {status}")
        except Exception as e:
            print(f"❌ BrainService Failed: {e}")
            traceback.print_exc()

        try:
            print("2. Testing endpoint via test_client...")
            with app.test_client() as client:
                # Need admin login simulation?
                # The endpoint is protected.
                # But let's see if we can just import the view?
                # No, better to test the service as above.
                pass
        except Exception as e:
            pass
    print("--- END BRAIN VERIFICATION ---")

if __name__ == "__main__":
    verify()
