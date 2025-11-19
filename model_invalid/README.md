# SDLC Framework - Phone Number Validation Project

This project demonstrates an SDLC framework that validates whether ML models meet specified business requirements.

## Quick Start

### Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements/requirements.txt
```

### Run the Project
```bash
python main.py
```

## Project Structure

- **data/**: Customer datasets
- **models/**: Non-compliant and compliant models
- **validation/**: SDLC requirement validator framework
- **utils/**: Helper functions for data loading and metrics
- **logs/**: Validation reports

## Key Requirements

1. **REQ-001**: Phone numbers should not exceed 10 digits
2. **REQ-002**: Phone numbers should be numeric only
3. **REQ-003**: No null values in phone number field
4. **REQ-004**: Model accuracy should be ≥ 75%

## Models

### Non-Compliant Model
- Does NOT filter phone numbers
- Violates REQ-001
- Framework detects violation

### Compliant Model
- Filters phone numbers to max 10 digits
- Meets all requirements
- Framework validates success

## Output

The framework generates validation reports showing:
- Which requirements passed/failed
- Violation details
- Model performance metrics
- Data quality issues