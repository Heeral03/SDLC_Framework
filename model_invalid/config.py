import os
from datetime import datetime

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
VALIDATION_DIR = os.path.join(PROJECT_ROOT, 'validation')

# Model configuration
RANDOM_STATE = 42
TEST_SIZE = 0.2
RANDOM_SEED = 42

# Phone number requirements
MAX_PHONE_DIGITS = 10
MIN_PHONE_DIGITS = 5

# Validation thresholds
MIN_ACCURACY = 0.75
MAX_NULL_PERCENTAGE = 0.0

# Logging
LOG_FILE = os.path.join(LOGS_DIR, f'validation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(VALIDATION_DIR, exist_ok=True)