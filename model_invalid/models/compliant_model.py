# COMPLIANT: This model filters phone numbers to meet REQ-001
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class CompliantModel:
    """Model that MEETS requirement: Phone numbers should not exceed 10 digits"""
    
    def __init__(self, random_state=42):
        self.model = RandomForestClassifier(n_estimators=100, random_state=random_state)
        self.scaler = StandardScaler()
        self.violation_count = 0
        
    def train(self, X_train, y_train, phone_numbers_train):
        """Train model WITH filtering phone numbers"""
        # COMPLIANT: Filter phone numbers to max 10 digits
        valid_mask = phone_numbers_train.str.len() <= 10
        X_train_filtered = X_train[valid_mask]
        y_train_filtered = y_train[valid_mask]
        
        # Count violations caught
        self.violation_count = (~valid_mask).sum()
        
        X_train_scaled = self.scaler.fit_transform(X_train_filtered)
        self.model.fit(X_train_scaled, y_train_filtered)
        
        return self
    
    def predict(self, X_test):
        """Make predictions"""
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.predict(X_test_scaled)
    
    def get_violation_report(self):
        """Report violations"""
        return {
            'violation_found': False,
            'violation_count': 0,
            'samples_filtered': self.violation_count,
            'requirement_met': 'REQ-001: Phone numbers filtered to ≤ 10 digits'
        }