#!/usr/bin/env python3
from wsgi import application

if __name__ == '__main__':
    application.run(host='127.0.0.1', port=5001, debug=False, threaded=False)
