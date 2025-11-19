from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

def calculate_metrics(y_true, y_pred):
    """Calculate model performance metrics"""
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0)
    }
    return metrics

def print_metrics(metrics, model_name):
    """Print metrics in formatted manner"""
    print(f"\n{'='*50}")
    print(f"Metrics for {model_name}")
    print(f"{'='*50}")
    for key, value in metrics.items():
        print(f"{key.upper():<15}: {value:.4f}")
    print(f"{'='*50}")