
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app import create_app
from app.models import MLModel
from app.extensions import db

app = create_app()

with app.app_context():
    print("--- MODEL REGISTRY INSPECTION ---")
    models = MLModel.query.all()
    for m in models:
        print(f"ID: {m.id} | Version: {m.version} | Symbol: '{m.symbol}' | Status: {m.status}")
        
    print("\n--- SIMULATING ACTIVATION QUERY ---")
    # Pick a random model (e.g. first one) to simulate what would happen
    if models:
        target = models[0]
        print(f"Testing activation for Model {target.id} ({target.version}) Symbol: {target.symbol}")
        
        query = MLModel.query.filter_by(status="active")
        
        # Replicate logic from brain_service.py
        if target.symbol:
            query = query.filter_by(symbol=target.symbol)
            print("Query filtered by symbol.")
        else:
            print("WARNING: No symbol on target! Query NOT filtered (Global Archive).")
            
        current = query.all()
        print(f"Would archive: {[c.version for c in current]}")
