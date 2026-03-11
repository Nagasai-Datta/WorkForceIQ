import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib, os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'attrition_model.pkl')

def generate_synthetic_data(n=1000):
    np.random.seed(42)
    years_exp      = np.random.randint(0, 20, n)
    satisfaction   = np.random.uniform(1.0, 5.0, n)
    monthly_hours  = np.random.randint(100, 260, n)
    allocation     = np.random.randint(0, 130, n)
    num_projects   = np.random.randint(0, 8, n)

    # Realistic attrition logic:
    # low satisfaction + high hours + high allocation + junior = more likely to quit
    attrition_score = (
        (5.0 - satisfaction) / 4.0 * 0.40 +
        np.clip((monthly_hours - 160) / 100, 0, 1) * 0.25 +
        np.clip(allocation / 100, 0, 1.3) * 0.20 +
        np.clip(1.0 / (years_exp + 1), 0, 1) * 0.15
    )
    noise = np.random.normal(0, 0.08, n)
    attrition = ((attrition_score + noise) > 0.42).astype(int)

    return pd.DataFrame({
        'years_experience': years_exp,
        'satisfaction_score': satisfaction,
        'monthly_hours': monthly_hours,
        'total_allocation': allocation,
        'num_projects': num_projects,
        'attrition': attrition
    })

def train_model():
    print("Training attrition model on synthetic data...")
    df = generate_synthetic_data(1000)
    X = df.drop('attrition', axis=1)
    y = df['attrition']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            random_state=42,
            class_weight='balanced'
        ))
    ])
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"  Attrition model accuracy: {acc:.2%}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model

def load_model():
    if not os.path.exists(MODEL_PATH):
        return train_model()
    return joblib.load(MODEL_PATH)

def predict_attrition(emp):
    """
    emp: dict with keys years_experience, satisfaction_score,
         monthly_hours, total_allocation, num_projects
    Returns: (risk_label, probability_percent)
    """
    model = load_model()
    features = [[
        emp.get('years_experience', 2),
        emp.get('satisfaction_score', 3.0),
        emp.get('monthly_hours', 160),
        emp.get('total_allocation', 0),
        emp.get('num_projects', 0),
    ]]
    prob = model.predict_proba(features)[0][1]  # probability of attrition=1
    if prob >= 0.65:
        risk = 'High'
    elif prob >= 0.35:
        risk = 'Medium'
    else:
        risk = 'Low'
    return risk, round(prob * 100, 1)
