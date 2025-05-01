import sys
import os

# Add your project directory to the sys.path
path = '/home/varunjoshi84/aiyogainstructor-master'  # Updated to match your actual directory structure
if path not in sys.path:
    sys.path.insert(0, path)

# Import your app from app.py
from app import app as application

# Set environment variable for PythonAnywhere
os.environ['PYTHONANYWHERE'] = 'true'