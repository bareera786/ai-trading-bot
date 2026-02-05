import sys
import os
import json

# Add app to path
sys.path.append(os.getcwd())

from app.services.binance import BinanceCredentialService, BinanceCredentialStore

def check_users():
    store = BinanceCredentialStore()
    ids = store.list_user_ids()
    print(f"User IDs in store: {ids}")
    
    if ids:
        for uid in ids:
            creds = store.get_credentials(uid)
            print(f"User {uid} credentials: {list(creds.keys())}")
            
    # Check default.json directly?
    try:
        with open("secrets/credentials/default.json", "r") as f:
            data = json.load(f)
            print(f"Raw file keys: {list(data.get('credentials', {}).keys())}")
    except Exception as e:
        print(f"Error reading raw file: {e}")

if __name__ == "__main__":
    check_users()
