# VIOLATION: This model violates REQ-001 by NOT filtering phone numbers > 10 digits
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class NonCompliantModel:
    """Model that VIOLATES requirement: Phone numbers should not exceed 10 digits"""
    
    def __init__(self, random_state=42):
        self.model = RandomForestClassifier(n_estimators=100, random_state=random_state)
        self.scaler = StandardScaler()
        self.violation_count = 0
        
    def train(self, X_train, y_train, phone_numbers_train):
        """Train model WITHOUT filtering phone numbers"""
        # VIOLATION: NOT filtering phone numbers
        X_train_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_train_scaled, y_train)
        
        # Count violations
        self.violation_count = (phone_numbers_train.str.len() > 10).sum()
        
        return self
    
    def predict(self, X_test):
        """Make predictions"""
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.predict(X_test_scaled)
    
    def get_violation_report(self):
        """Report violations"""
        return {
            'violation_found': self.violation_count > 0,
            'violation_count': self.violation_count,
            'requirement_violated': 'REQ-001: Phone numbers should not exceed 10 digits'
        }