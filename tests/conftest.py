import pytest
import os
import sys

# Ensure the database models and tools are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))

# Import all fixtures so they are available to all test files
from fixtures.db_fixtures import *
