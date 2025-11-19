import pandas as pd
import numpy as np
import os
from config import DATA_DIR

def load_customer_data(filename='customer_data.csv'):
    """Load customer dataset"""
    filepath = os.path.join(DATA_DIR, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset not found at {filepath}")
    
    df = pd.read_csv(filepath)
    
    # Remove trailing spaces from column names
    df.columns = df.columns.str.strip()
    
    # Rename PhoneNumber to Mobile if needed (handle both cases)
    if 'PhoneNumber' in df.columns:
        df.rename(columns={'PhoneNumber': 'Mobile'}, inplace=True)
    
    print(f"Dataset loaded: {filepath}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    return df

def preprocess_data(df):
    """Preprocess the data"""
    df_processed = df.copy()
    
    # Rename Mobile column to PhoneNumber for consistency
    if 'Mobile' in df_processed.columns:
        df_processed['PhoneNumber'] = df_processed['Mobile'].astype(str)
    elif 'PhoneNumber' in df_processed.columns:
        df_processed['PhoneNumber'] = df_processed['PhoneNumber'].astype(str)
    else:
        raise ValueError("Neither 'Mobile' nor 'PhoneNumber' column found in dataset")
    
    # Convert phone number to string and remove spaces
    df_processed['PhoneNumber'] = df_processed['PhoneNumber'].str.strip()
    
    # Remove non-numeric characters from phone numbers
    df_processed['PhoneNumber_Clean'] = df_processed['PhoneNumber'].str.replace(r'\D', '', regex=True)
    
    # Calculate phone digits (from cleaned version)
    df_processed['PhoneDigits'] = df_processed['PhoneNumber_Clean'].apply(lambda x: len(x) if pd.notna(x) else 0)
    
    # Create target variable for classification (1 if phone has issues, 0 if valid)
    # Issues: > 10 digits, < 5 digits, or contains non-numeric characters, or empty
    df_processed['HasPhoneIssue'] = (
        (df_processed['PhoneDigits'] > 10) | 
        (df_processed['PhoneDigits'] < 5) |
        (df_processed['PhoneDigits'] == 0) |
        (df_processed['PhoneNumber'] != df_processed['PhoneNumber_Clean'])
    ).astype(int)
    
    return df_processed

def get_features_and_target(df, target_col='HasPhoneIssue'):
    """Extract features and target from dataset"""
    import numpy as np
    
    # Create features from available data
    X = pd.DataFrame(index=df.index)
    
    # Add age feature if available
    if 'Registered_Age' in df.columns:
        X['Age'] = df['Registered_Age'].fillna(df['Registered_Age'].mean())
    
    # Add phone digits feature
    if 'PhoneDigits' in df.columns:
        X['Phone_Digits'] = df['PhoneDigits']
    
    # Add a random feature for model training (since dataset is small)
    X['Random_Feature'] = np.random.RandomState(42).rand(len(df))
    
    # If still empty, create synthetic features
    if len(X.columns) == 0:
        X['Feature1'] = np.random.RandomState(42).rand(len(df))
        X['Feature2'] = np.random.RandomState(42).rand(len(df))
    
    # Get target
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataframe")
    
    y = df[target_col]
    
    return X, y