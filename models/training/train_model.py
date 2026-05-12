import pickle
import os
import numpy as np
from sklearn.linear_model import LogisticRegression

# Create models directory if it doesn't exist
models_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(models_dir, exist_ok=True)

def generate_synthetic_data(num_samples=1000):
    """
    Generate very simple synthetic data to train the LogisticRegression model.
    Features: [amount_zscore, recipient_is_new, country_is_new, velocity, account_age_days]
    Target: 0 = legitimate, 1 = anomaly/fraud
    """
    X = []
    y = []
    
    for _ in range(num_samples):
        is_fraud = np.random.rand() > 0.9  # 10% fraud base rate
        
        if is_fraud:
            # High amount, often new recipient or new country, high velocity, new account
            amount_zscore = np.random.normal(5, 2)
            recipient_new = 1.0 if np.random.rand() > 0.2 else 0.0
            country_new = 1.0 if np.random.rand() > 0.4 else 0.0
            velocity = np.random.normal(10, 3)
            age = np.random.exponential(5)
            y.append(1)
        else:
            # Normal amount, existing recipient mostly, existing country, low velocity, older account
            amount_zscore = np.random.normal(0, 1)
            recipient_new = 1.0 if np.random.rand() > 0.9 else 0.0
            country_new = 1.0 if np.random.rand() > 0.95 else 0.0
            velocity = np.random.normal(1, 1)
            age = np.random.exponential(100)
            y.append(0)
            
        X.append([amount_zscore, recipient_new, country_new, velocity, age])
        
    return np.array(X), np.array(y)

def train_model():
    print("Generating synthetic data for ML layer...")
    X_train, y_train = generate_synthetic_data(2000)
    
    print("Training LogisticRegression (brutally simple)...")
    clf = LogisticRegression(random_state=42, class_weight='balanced')
    clf.fit(X_train, y_train)
    
    accuracy = clf.score(X_train, y_train)
    print(f"Training absolute accuracy: {accuracy:.2f}")
    
    model_path = os.path.join(models_dir, 'ml_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(clf, f)
    print(f"Model safely saved to {model_path}")

if __name__ == "__main__":
    train_model()
