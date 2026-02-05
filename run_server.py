
from dotenv import load_dotenv
load_dotenv()

import os
os.environ["SKIP_RUNTIME_BOOTSTRAP"] = "true"

from app import create_app

if __name__ == "__main__":
    app = create_app()
    # Explicitly set host to 0.0.0.0 or 127.0.0.1
    print("Starting temporary server on port 5001...")
    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=False)
