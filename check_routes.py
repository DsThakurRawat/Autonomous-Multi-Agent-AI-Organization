import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from api.main import app

print("Registered Routes:")
for route in app.routes:
    methods = getattr(route, "methods", None)
    path = getattr(route, "path", None)
    if path:
        print(f"{list(methods) if methods else 'WS'} -> {path}")
