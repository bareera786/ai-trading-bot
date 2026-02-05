import os
import json
import sys
from pathlib import Path

# Add project root to path so we can import app utilities
sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    from utils.compression import get_compressor
except ImportError:
    print("❌ Could not import compression utils. Ensure this script is run from the project root.")
    sys.exit(1)

def restore():
    user_id = "user_751d38ba-1031-4d40-b3e8-59ca8577f84f"
    backup_file = "state_backup_20260201_183209.json.zst"
    
    project_root = Path(__file__).resolve().parents[1]
    persistence_dir = project_root / "bot_persistence" / user_id
    backup_path = persistence_dir / "backups" / backup_file
    target_path = persistence_dir / "bot_state.json"
    
    if not backup_path.exists():
        print(f"❌ Backup not found: {backup_path}")
        return False
        
    print(f"🔄 Restoring {backup_file} to {target_path}...")
    
    try:
        # Use robust decompression for frames without content size header
        import zstandard as zstd
        dctx = zstd.ZstdDecompressor()
        with open(backup_path, "rb") as f:
            decompressed = dctx.decompress(f.read(), max_output_size=10*1024*1024) # 10MB limit
        
        state_data = json.loads(decompressed.decode('utf-8'))
        
        # Verify the data before writing
        if "configuration" not in state_data:
            print("❌ Decompressed data seems invalid (missing configuration key)")
            return False
            
        with open(target_path, "w") as f:
            json.dump(state_data, f, indent=2)
            
        print(f"✅ Restoration complete!")
        return True
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False

if __name__ == "__main__":
    if restore():
        sys.exit(0)
    else:
        sys.exit(1)
