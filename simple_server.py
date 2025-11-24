import os
os.environ['FLASK_ENV'] = 'development'
from ai_ml_auto_bot_final import app
print('Starting simple Flask server...')
app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)