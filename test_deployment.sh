#!/bin/bash
# Test deployed bot endpoints

echo "🧪 Testing AI Trading Bot Deployment"
echo "===================================="
echo ""

# Test main endpoint
echo "🌐 Testing main endpoint..."
curl -s -I http://151.243.171.80:5000/ | head -3

# Test API endpoint
echo ""
echo "🔌 Testing API endpoint..."
curl -s http://151.243.171.80:5000/api/market_data | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('✅ API Response OK')
    btc_price = data.get('market_data', {}).get('BTCUSDT', {}).get('price', 'N/A')
    eth_price = data.get('market_data', {}).get('ETHUSDT', {}).get('price', 'N/A')
    print(f'BTCUSDT: {btc_price}')
    print(f'ETHUSDT: {eth_price}')
except:
    print('❌ API Response Error')
" 2>/dev/null || echo "❌ API endpoint failed"

# Test metrics endpoint
echo ""
echo "📊 Testing metrics endpoint..."
curl -s http://151.243.171.80:9090/metrics | head -5 | grep -E "(HELP|TYPE|#)" || echo "❌ Metrics endpoint failed"

echo ""
echo "🎉 Testing complete!"