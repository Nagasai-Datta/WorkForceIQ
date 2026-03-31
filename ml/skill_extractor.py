"""
skill_extractor.py — Thin wrapper that delegates to the Groq LLM engine.
Falls back to keyword matching if GROQ_API_KEY is not set.
"""
from ml.llm_engine import extract_skills_from_resume, KNOWN_SKILLS
import re

def extract_skills_from_text(resume_text: str, top_n: int = 12) -> list[dict]:
    """
    Returns list of dicts: {"skill": str, "confidence": str, "evidence": str}
    Compatible with existing route code.
    """
    if not resume_text or len(resume_text.strip()) < 20:
        return []
    results = extract_skills_from_resume(resume_text)
    # Normalize confidence to a score for sorting
    order = {"High": 3, "Medium": 2, "Low": 1}
    results.sort(key=lambda x: order.get(x.get("confidence", "Low"), 0), reverse=True)
    return results[:top_n]

def extract_skill_names(resume_text: str) -> list[str]:
    """Convenience: just the skill name strings."""
    return [r["skill"] for r in extract_skills_from_text(resume_text)]
