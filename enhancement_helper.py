#!/usr/bin/env python3
"""
Quick integration for enhancing existing AI Trading Bot
"""
import sys
sys.path.append('.')

from audit_agent import TradingBotAuditor
import os

def quick_enhance():
    """Quick enhancement mode for your bot"""
    print("🤖 AI Trading Bot Enhancement Helper")
    print("-" * 40)
    
    # 1. Check critical safety flags
    print("\n🔒 Checking safety flags...")
    if os.getenv("FINAL_HAMMER", "FALSE") == "TRUE":
        print("⚠️  WARNING: FINAL_HAMMER=TRUE - Live trading enabled!")
    else:
        print("✅ FINAL_HAMMER=FALSE - Safe mode")
    
    # 2. Quick audit of risk management
    print("\n📊 Quick risk management check...")
    # Add your checks here
    
    # 3. Offer to run specific audits
    print("\n🎯 Select audit type:")
    print("1. Security audit (API keys, error handling)")
    print("2. Performance audit (parallel processing, memory)")
    print("3. Trading logic audit (indicators, signals)")
    
    choice = input("\nSelect (1-3) or Enter to skip: ")
    
    if choice == "1":
        print("Running security audit...")
        # Your security audit logic
    
if __name__ == "__main__":
    quick_enhance()
