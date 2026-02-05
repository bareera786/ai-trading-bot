
import sys
import os

sys.path.append(os.getcwd())

from app import create_app
from app.services import BrainService
from app.models import MLModel

app = create_app()

with app.app_context():
    print("--- START ACTIVATION DEBUG ---")
    
    # 1. State Before
    print("BEFORE:")
    models = MLModel.query.all()
    for m in models:
        prefix = "✅" if m.status == 'active' else "  "
        print(f"{prefix} {m.id} | {m.version} | {m.symbol} | {m.status}")

    # 2. Activate Model 1 (BTCUSDT)
    print("\n--- ACTIVATING MODEL 1 (BTCUSDT) ---")
    success, msg = BrainService.activate_model(1, confirmation_phrase="I AUTHORIZE DEPLOYMENT")
    print(f"Result: {success} - {msg}")

    # 3. State After
    print("\nAFTER:")
    models = MLModel.query.all()
    for m in models:
        prefix = "✅" if m.status == 'active' else "  "
        print(f"{prefix} {m.id} | {m.version} | {m.symbol} | {m.status}")
        
    print("--- END DEBUG ---")
    sys.stdout.flush()
