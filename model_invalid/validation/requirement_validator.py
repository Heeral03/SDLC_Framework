import json
from datetime import datetime
from config import LOG_FILE, MAX_PHONE_DIGITS, MIN_ACCURACY

class RequirementValidator:
    """SDLC Framework to validate model requirements"""
    
    def __init__(self):
        self.validation_results = []
        self.log_file = LOG_FILE
        
    def validate_req_001_phone_digits(self, df, data_source='input'):
        """REQ-001: Phone numbers should not exceed 10 digits"""
        phone_col = 'PhoneNumber'
        
        if phone_col not in df.columns:
            return {
                'requirement_id': 'REQ-001',
                'requirement': 'Phone numbers should not exceed 10 digits',
                'status': 'FAILED',
                'reason': 'PhoneNumber column not found',
                'data_source': data_source
            }
        
        violations = (df[phone_col].astype(str).str.len() > MAX_PHONE_DIGITS).sum()
        total_records = len(df)
        violation_percentage = (violations / total_records) * 100
        
        status = 'PASSED' if violations == 0 else 'FAILED'
        
        result = {
            'requirement_id': 'REQ-001',
            'requirement': 'Phone numbers should not exceed 10 digits',
            'status': status,
            'violations_found': violations,
            'total_records': total_records,
            'violation_percentage': round(violation_percentage, 2),
            'data_source': data_source,
            'details': f"{violations} out of {total_records} records have phone numbers exceeding {MAX_PHONE_DIGITS} digits"
        }
        
        self.validation_results.append(result)
        return result
    
    def validate_req_002_phone_numeric(self, df):
        """REQ-002: Phone numbers should contain only numeric values"""
        phone_col = 'PhoneNumber'
        
        if phone_col not in df.columns:
            return {
                'requirement_id': 'REQ-002',
                'requirement': 'Phone numbers should be numeric only',
                'status': 'FAILED',
                'reason': 'PhoneNumber column not found'
            }
        
        non_numeric = df[phone_col].astype(str).str.contains('[^0-9]', regex=True).sum()
        status = 'PASSED' if non_numeric == 0 else 'FAILED'
        
        result = {
            'requirement_id': 'REQ-002',
            'requirement': 'Phone numbers should be numeric only',
            'status': status,
            'non_numeric_count': int(non_numeric),
            'details': f"{non_numeric} records contain non-numeric characters"
        }
        
        self.validation_results.append(result)
        return result
    
    def validate_req_003_no_nulls(self, df):
        """REQ-003: No null values in phone number field"""
        phone_col = 'PhoneNumber'
        
        if phone_col not in df.columns:
            return {
                'requirement_id': 'REQ-003',
                'requirement': 'No null values in phone number field',
                'status': 'FAILED',
                'reason': 'PhoneNumber column not found'
            }
        
        null_count = df[phone_col].isnull().sum()
        total_records = len(df)
        null_percentage = (null_count / total_records) * 100
        
        status = 'PASSED' if null_count == 0 else 'FAILED'
        
        result = {
            'requirement_id': 'REQ-003',
            'requirement': 'No null values in phone number field',
            'status': status,
            'null_count': int(null_count),
            'null_percentage': round(null_percentage, 2),
            'details': f"{null_count} null values found ({null_percentage:.2f}%)"
        }
        
        self.validation_results.append(result)
        return result
    
    def validate_req_004_model_accuracy(self, accuracy, threshold=MIN_ACCURACY):
        """REQ-004: Model accuracy should be >= threshold"""
        status = 'PASSED' if accuracy >= threshold else 'FAILED'
        
        result = {
            'requirement_id': 'REQ-004',
            'requirement': f'Model accuracy should be >= {threshold}',
            'status': status,
            'actual_accuracy': round(accuracy, 4),
            'required_accuracy': threshold,
            'details': f"Accuracy: {accuracy:.4f} vs Required: {threshold}"
        }
        
        self.validation_results.append(result)
        return result
    
    def generate_validation_report(self, model_name):
        """Generate comprehensive validation report"""
        report = f"\n{'='*70}\n"
        report += f"SDLC VALIDATION REPORT - {model_name}\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"{'='*70}\n\n"
        
        passed = sum(1 for r in self.validation_results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.validation_results if r['status'] == 'FAILED')
        
        report += f"SUMMARY: {passed} PASSED | {failed} FAILED\n"
        report += f"{'-'*70}\n\n"
        
        for result in self.validation_results:
            report += f"Requirement ID: {result['requirement_id']}\n"
            report += f"Description: {result['requirement']}\n"
            report += f"Status: {'✓ PASSED' if result['status'] == 'PASSED' else '✗ FAILED'}\n"
            report += f"Details: {result.get('details', 'N/A')}\n"
            report += f"{'-'*70}\n"
        
        return report
    
    def save_report(self, report, model_name):
        """Save validation report to file"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nValidation report saved to: {self.log_file}")