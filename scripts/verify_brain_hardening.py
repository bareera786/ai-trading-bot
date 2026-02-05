import requests
import json
import time

BASE_URL = "http://151.243.171.80:5000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def verify_hardening():
    print("🛡️ Verifying Brain Hardening...")
    
    session = requests.Session()
    
    # 1. Login
    print("\n1️⃣ Logging in as Admin...")
    try:
        # Get CSRF token first?
        # Standard login usually requires CSRF. 
        # But maybe we can hit the API directly if we are admin?
        # Let's try simulating browser login flow.
        
        login_page = session.get(f"{BASE_URL}/auth/login")
        # Extract CSRF if needed, but standard Flask-Login might need it in form data.
        # Assuming we can just POST if CSRF is disabled for API or handled via cookie.
        # Let's try simple POST.
        
        # We need to know how login is handled. 
        # app/routes/auth.py handles it.
        # It expects form data: email, password, csrf_token.
        # For simplicity, if this fails, we might need a more complex script or use the browser tool.
        # But let's try.
        
        # Actually, let's look at verify_dashboard_api.py. It uses app.test_client().
        # Can we do that? No, we want to verify the DEPLOYED app.
        
        # For now, let's assume we can login.
        # Extract CSRF token from login page
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
        
        login_data = {
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "csrf_token": csrf_token
        }
        
        resp = session.post(f"{BASE_URL}/auth/login", data=login_data)
        if resp.status_code == 200 and "dashboard" in resp.url: # successful login redirects
             print("✅ Login Successful")
        elif resp.history: # Redirect happened
             print("✅ Login Successful (Redirected)")
        else:
             print(f"⚠️ Login might have failed. Status: {resp.status_code}")
             # Proceed anyway, maybe session cookie was set?
             
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return False

    # 2. Verify Simulation
    print("\n2️⃣ Testing Backtest Simulation...")
    try:
        sim_data = {"symbol": "BTCUSDT", "days": 30}
        headers = {"X-CSRFToken": csrf_token, "Content-Type": "application/json"} # API might verify CSRF
        # But wait, endpoint method is POST. 
        # If standard CSRF is on, we need header X-CSRFToken. 
        
        resp = session.post(f"{BASE_URL}/api/brain/simulate", json=sim_data, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if "total_trades" in data:
                print(f"✅ Simulation OK: {data['total_trades']} trades, ROI: {data['total_pnl_percent']}%")
            else:
                print(f"❌ Simulation Failed: Invalid Response {data}")
        else:
             print(f"❌ Simulation Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Simulation Error: {e}")

    # 3. Verify Training
    print("\n3️⃣ Testing Training Job Spawn...")
    job_id = None
    try:
        train_data = {"model_type": "LSTM", "epochs": 5}
        resp = session.post(f"{BASE_URL}/api/brain/train", json=train_data, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            job_id = data.get("job_id")
            print(f"✅ Training Spawned. Job ID: {job_id}")
        else:
            print(f"❌ Training Spawn Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Training Error: {e}")

    # 4. Verify Training Status
    if job_id:
        print("\n4️⃣ Checking Training Status...")
        try:
            time.sleep(2) # Wait for worker to start
            resp = session.get(f"{BASE_URL}/api/brain/train/status/{job_id}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Status: {data['status']} | Progress: {data['progress']}%")
                if data['status'] in ['pending', 'running', 'completed']:
                    print("✅ Worker is responding correctly.")
                else:
                    print(f"⚠️ Unexpected status: {data['status']}")
            else:
                print(f"❌ Status Check Failed: {resp.status_code}")
        except Exception as e:
            print(f"❌ Status Error: {e}")

    # 5. Model Archiving (Optional - Find a shadow model)
    print("\n5️⃣ Testing Model Archiving...")
    try:
        resp = session.get(f"{BASE_URL}/api/brain/models")
        models = resp.json()
        shadow_model = next((m for m in models if m['status'] == 'shadow'), None)
        
        if shadow_model:
            model_id = shadow_model['id']
            print(f"Found shadow model ID: {model_id}. Archiving...")
            resp = session.post(f"{BASE_URL}/api/brain/models/archive/{model_id}", headers=headers)
            if resp.status_code == 200:
                print(f"✅ Model {model_id} archived successfully.")
            else:
                print(f"❌ Archiving Failed: {resp.status_code} - {resp.text}")
        else:
            print("ℹ️ No shadow models found to test archiving.")
            
    except Exception as e:
        print(f"❌ Archiving Error: {e}")

    print("\n🛡️ Hardening Verification COMPLETE!")

if __name__ == "__main__":
    verify_hardening()
