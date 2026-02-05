"""
Quick diagnostic script to check if the real bot or fallback is being used.
Run this after starting your bot to see which market_data_service is active.
"""

import requests

def check_bot_status():
    """Check if the real bot or fallback is being used."""
    try:
        # Try to access the API
        response = requests.get("http://localhost:5000/api/status", timeout=5)
        data = response.json()
        
        print("=" * 60)
        print("BOT STATUS CHECK")
        print("=" * 60)
        
        # Check system status
        system_status = data.get("system_status", {})
        
        if system_status:
            print("✅ Bot Context: REAL BOT (Full Runtime)")
            print(f"   - Trading Enabled: {system_status.get('trading_enabled', False)}")
            print(f"   - Paper Trading: {system_status.get('paper_trading', True)}")
            print(f"   - Real Trading Ready: {system_status.get('real_trading_ready', False)}")
            print(f"   - Futures Trading Ready: {system_status.get('futures_trading_ready', False)}")
        else:
            print("⚠️  Bot Context: FALLBACK MODE (Test/Minimal)")
            print("   - This means the full bot hasn't initialized yet")
        
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Bot is not running. Start it with: python run.py")
    except Exception as e:
        print(f"❌ Error checking bot status: {e}")

if __name__ == "__main__":
    check_bot_status()
