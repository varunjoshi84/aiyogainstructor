import sys
import os

# Add your project directory to the sys.path
path = '/home/YOUR_PYTHONANYWHERE_USERNAME/aiyogainstructor'
if path not in sys.path:
    sys.path.insert(0, path)

# Import your app from app.py
from app import app as application

# Set environment variable for PythonAnywhere
os.environ['PYTHONANYWHERE'] = 'true'