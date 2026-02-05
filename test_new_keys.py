import os
from dotenv import load_dotenv

load_dotenv()

print("🔐 Testing Environment Variables")
print("=" * 40)

# Check for required variables
required_vars = [
    'DEEPSEEK_API_KEY',
    'BINANCE_API_KEY',
    'BINANCE_API_SECRET',
    'FINAL_HAMMER'
]

all_good = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Mask the value for security
        masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
        print(f"✅ {var}: {masked}")
        
        # Check if it's a placeholder
        if 'your_' in value.lower() or 'example' in value.lower():
            print(f"   ⚠️  This appears to be a placeholder!")
            all_good = False
    else:
        print(f"❌ {var}: NOT SET")
        all_good = False

print("\n" + "=" * 40)
if all_good:
    print("🎉 All required variables are set!")
    print("💡 Remember to keep them secure and never commit to git.")
else:
    print("⚠️  Some variables are missing or appear to be placeholders.")
    print("   Update your .env file with actual values for production.")
#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

print("🔐 Testing Environment Variables")
print("=" * 40)

required_vars = [
    'DEEPSEEK_API_KEY',
    'BINANCE_API_KEY',
    'BINANCE_API_SECRET',
    'FINAL_HAMMER'
]

all_good = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
        print(f"✅ {var}: {masked}")
        if 'your_' in value.lower() or 'example' in value.lower():
            print(f"   ⚠️  This appears to be a placeholder!")
            all_good = False
    else:
        print(f"❌ {var}: NOT SET")
        all_good = False

print("\n" + "=" * 40)
if all_good:
    print("🎉 All required variables are set!")
    print("💡 Remember to keep them secure and never commit to git.")
else:
    print("⚠️  Some variables are missing or appear to be placeholders.")
    print("   Update your .env file with actual values for production.")
