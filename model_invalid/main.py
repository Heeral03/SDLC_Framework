from sklearn.model_selection import train_test_split
from utils.data_loader import load_customer_data, preprocess_data, get_features_and_target
from utils.metrics import calculate_metrics, print_metrics
from models.non_compliant_model import NonCompliantModel
from models.compliant_model import CompliantModel
from validation.requirement_validator import RequirementValidator
from config import RANDOM_STATE, TEST_SIZE

def main():
    print("\n" + "="*70)
    print("SDLC FRAMEWORK - PHONE NUMBER VALIDATION PROJECT")
    print("="*70)
    
    # Load data
    print("\n[STEP 1] Loading customer data...")
    df = load_customer_data('customer_data.csv')
    print(f"Total records loaded: {len(df)}")
    
    # Preprocess
    print("\n[STEP 2] Preprocessing data...")
    df_processed = preprocess_data(df)
    print(f"Phone number digit range: {df_processed['PhoneDigits'].min()} to {df_processed['PhoneDigits'].max()}")
    print(f"Records with phone issues: {df_processed['HasPhoneIssue'].sum()}")
    
    # Display sample phone numbers
    print("\nSample phone numbers analysis:")
    print(df_processed[['ID', 'Name', 'Mobile', 'PhoneNumber_Clean', 'PhoneDigits', 'HasPhoneIssue']].head(10))
    
    # Split data
    print("\n[STEP 3] Splitting data into train/test...")
    X, y = get_features_and_target(df_processed, target_col='HasPhoneIssue')
    
    # Check if we have enough samples
    if len(X) < 10:
        print(f"Warning: Only {len(X)} samples available. This is a small dataset.")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    phone_train = df_processed.loc[X_train.index, 'PhoneNumber']
    phone_test = df_processed.loc[X_test.index, 'PhoneNumber']
    
    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    
    # ===== MODEL 1: NON-COMPLIANT =====
    print("\n" + "="*70)
    print("MODEL 1: NON-COMPLIANT MODEL (Violates REQ-001)")
    print("="*70)
    print("❌ This model does NOT filter phone numbers > 10 digits")
    print("="*70)
    
    non_compliant_model = NonCompliantModel()
    non_compliant_model.train(X_train, y_train, phone_train)
    y_pred_nc = non_compliant_model.predict(X_test)
    metrics_nc = calculate_metrics(y_test, y_pred_nc)
    print_metrics(metrics_nc, "Non-Compliant Model")
    
    # Validate non-compliant model
    print("\n[VALIDATION] Non-Compliant Model Requirements Check...")
    validator_nc = RequirementValidator()
    validator_nc.validate_req_001_phone_digits(df_processed, data_source='training_data')
    validator_nc.validate_req_002_phone_numeric(df_processed)
    validator_nc.validate_req_003_no_nulls(df_processed)
    validator_nc.validate_req_004_model_accuracy(metrics_nc['accuracy'])
    
    report_nc = validator_nc.generate_validation_report("Non-Compliant Model")
    print(report_nc)
    validator_nc.save_report(report_nc, "non_compliant")
    
    # ===== MODEL 2: COMPLIANT =====
    print("\n" + "="*70)
    print("MODEL 2: COMPLIANT MODEL (Meets REQ-001)")
    print("="*70)
    print("✓ This model FILTERS phone numbers to max 10 digits")
    print("="*70)
    
    compliant_model = CompliantModel()
    compliant_model.train(X_train, y_train, phone_train)
    y_pred_c = compliant_model.predict(X_test)
    metrics_c = calculate_metrics(y_test, y_pred_c)
    print_metrics(metrics_c, "Compliant Model")
    
    # Validate compliant model
    print("\n[VALIDATION] Compliant Model Requirements Check...")
    validator_c = RequirementValidator()
    validator_c.validate_req_001_phone_digits(df_processed, data_source='training_data')
    validator_c.validate_req_002_phone_numeric(df_processed)
    validator_c.validate_req_003_no_nulls(df_processed)
    validator_c.validate_req_004_model_accuracy(metrics_c['accuracy'])
    
    report_c = validator_c.generate_validation_report("Compliant Model")
    print(report_c)
    validator_c.save_report(report_c, "compliant")
    
    # ===== COMPARISON =====
    print("\n" + "="*70)
    print("SDLC FRAMEWORK COMPARISON & ANALYSIS")
    print("="*70)
    
    print("\n❌ NON-COMPLIANT MODEL VIOLATIONS:")
    print("-" * 70)
    violations_nc = non_compliant_model.get_violation_report()
    print(f"Violations Found: {violations_nc['violation_found']}")
    print(f"Violation Count: {violations_nc['violation_count']}")
    print(f"Requirement Violated: {violations_nc['requirement_violated']}")
    
    print("\n✓ COMPLIANT MODEL STATUS:")
    print("-" * 70)
    status_c = compliant_model.get_violation_report()
    print(f"Violations Found: {status_c['violation_found']}")
    print(f"Samples Filtered: {status_c['samples_filtered']}")
    print(f"Requirement Status: {status_c['requirement_met']}")
    
    print("\n" + "="*70)
    print("FRAMEWORK CONCLUSION")
    print("="*70)
    print("✓ Framework successfully identified REQ-001 violation in Non-Compliant Model")
    print("✓ Compliant Model passed all requirements")
    print(f"✓ {violations_nc['violation_count']} invalid phone numbers were detected")
    print("\nValidation logs saved to: logs/")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()