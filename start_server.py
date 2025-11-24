import sys
sys.path.insert(0, '.')
from ai_ml_auto_bot_final import app
app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
