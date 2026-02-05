import sys
import os

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.services.protection import ProtectionService
    from app.domain.trading.risk import RiskManager
    
    print("✅ ProtectionService import successful")
    print("✅ RiskManager import successful")
    
    if ProtectionService is RiskManager:
        print("✅ ProtectionService is correctly aliased to RiskManager")
    else:
        print("❌ ProtectionService is NOT aliased correctly")
        sys.exit(1)
        
    print("Phase A Verification Passed")
except Exception as e:
    print(f"❌ Verification Failed: {e}")
    sys.exit(1)
