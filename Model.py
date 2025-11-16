import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix, accuracy_score
import joblib

print("Loading dataset...")

# Load dataset
heart_disease_data = pd.read_csv("heart.csv")
print("Dataset Loaded Successfully!")
print(heart_disease_data.head(), "\n")

# Separate target
y = heart_disease_data['target']

# One-hot encode ALL categorical columns like Kaggle
X_encoded = pd.get_dummies(
    heart_disease_data.drop(['target'], axis=1),
    columns=['sex','cp','fbs','restecg','exang','slope','ca','thal']
)

print("\nAfter Encoding:")
print(X_encoded.head(), "\n")
print(f"Total Features After Encoding: {X_encoded.shape[1]}\n")

# Train-test split (same as Kaggle)
X_train, X_test, y_train, y_test = train_test_split(
    X_encoded, y, test_size=0.2, random_state=1
)

# Scale data (same as Kaggle)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Train SVM model (exact Kaggle config)
svc = SVC(kernel='linear', random_state=0)
svc.fit(X_train, y_train)

# Predictions
y_pred = svc.predict(X_test)

# Results
cm = confusion_matrix(y_test, y_pred)
acc = accuracy_score(y_test, y_pred)

print("\nConfusion Matrix:")
print(cm)

print(f"\nAccuracy: {acc}")

# Save model + scaler
joblib.dump(svc, "heart_model.pkl")
joblib.dump(scaler, "scaler.pkl")

print("\nModel and Scaler saved successfully!")
print("Files generated: heart_model.pkl, scaler.pkl")
