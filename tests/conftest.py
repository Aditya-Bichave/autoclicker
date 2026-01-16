import sys
import os

# Add the project root directory to sys.path
# This assumes tests/ is one level deep from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
