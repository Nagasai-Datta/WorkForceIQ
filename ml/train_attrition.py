"""
train_attrition.py — LLM-based attrition analysis via Groq.
Replaces the XGBoost model entirely. No training needed, no .pkl files.

The LLM reasons about the employee profile exactly as an experienced HR analyst
would — it understands context, not just numbers.
"""
from ml.llm_engine import predict_attrition_llm

def predict_attrition(emp: dict) -> dict:
    """
    Drop-in replacement for the old XGBoost predict_attrition.
    emp: dict with employee profile fields.
    Returns: {"risk": str, "probability": float, "explanation": list, "suggestion": str}
    """
    result = predict_attrition_llm(emp)
    # Ensure probability is a float for template compatibility
    result['probability'] = float(result.get('probability', 0))
    return result

def load_model():
    """No-op — LLM needs no pre-training or loading."""
    print("  ✓ LLM attrition engine ready (Groq / llama-3.1-8b-instant).")
    return None
