"""
llm_engine.py — Groq LLM backend for WorkForceIQ
Uses the FREE Groq API (llama-3.1-8b-instant).

Setup:
  1. Create free account at https://console.groq.com
  2. Generate API key (free, no credit card)
  3. Add to .env:  GROQ_API_KEY=gsk_...

Free tier limits:
  - 14,400 requests / day
  - 6,000 tokens / minute
  - Model: llama-3.1-8b-instant (fastest, free)

Why Groq over other options:
  - Faster than OpenAI free tier (usually <1 sec)
  - No token cost on free plan
  - JSON mode supported (structured output)
  - Works locally once you have the key
"""

import os, json, re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get('GROQ_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Get a free key at https://console.groq.com "
                "and add GROQ_API_KEY=gsk_... to your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client

MODEL = "llama-3.1-8b-instant"   # free, fast (~200 tok/sec on Groq)

def _chat(system: str, user: str, max_tokens: int = 512) -> str:
    """Raw chat call — returns content string."""
    client = _get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.1,       # low temp = deterministic/factual output
    )
    return resp.choices[0].message.content.strip()

def _parse_json(text: str) -> dict | list:
    """Extract JSON from LLM response (handles markdown fences)."""
    # Strip markdown fences
    text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
    return json.loads(text)

# ── Public API ────────────────────────────────────────────────────────────────

KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "React", "Node.js",
    "Django", "Flask", "SQL", "MySQL", "PostgreSQL", "MongoDB",
    "AWS", "Docker", "Kubernetes", "Git", "Machine Learning",
    "TensorFlow", "Data Analysis", "Tableau", "UI/UX Design",
    "Project Management", "Agile / Scrum", "Communication",
]

def extract_skills_from_resume(resume_text: str) -> list[dict]:
    """
    Send resume text to Groq → get back list of matched skills with confidence.
    Returns: [{"skill": str, "confidence": "High"|"Medium"|"Low", "evidence": str}, ...]
    """
    system = (
        "You are a technical recruiter AI. "
        "Extract technical skills from resume text. "
        "Only return skills that appear in the provided skill list. "
        "Respond ONLY with valid JSON — no explanation, no markdown, no extra text."
    )
    user = f"""
Resume text:
\"\"\"
{resume_text[:3000]}
\"\"\"

Known skill list: {json.dumps(KNOWN_SKILLS)}

Return JSON array like:
[
  {{"skill": "Python", "confidence": "High", "evidence": "5 years Python development"}},
  {{"skill": "Docker", "confidence": "Medium", "evidence": "containerisation mentioned"}}
]

Only include skills clearly evidenced in the resume. Max 12 skills.
"""
    try:
        raw = _chat(system, user, max_tokens=600)
        data = _parse_json(raw)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        # Fallback: simple keyword scan
        found = []
        text_lower = resume_text.lower()
        for skill in KNOWN_SKILLS:
            if skill.lower() in text_lower or skill.lower().replace('/', ' ') in text_lower:
                found.append({"skill": skill, "confidence": "Medium", "evidence": "keyword match"})
        return found


def predict_attrition_llm(emp: dict) -> dict:
    """
    Ask Groq to assess attrition risk from employee profile data.
    Returns: {"risk": "High"|"Medium"|"Low", "probability": int, "explanation": [...], "suggestion": str}
    """
    system = (
        "You are an expert HR analytics AI. "
        "Assess employee attrition risk based on their profile data. "
        "Be analytical and specific. "
        "Respond ONLY with valid JSON — no explanation, no markdown."
    )
    user = f"""
Employee profile:
- Years of experience: {emp.get('years_experience', 'N/A')}
- Satisfaction score: {emp.get('satisfaction_score', 'N/A')} / 5.0
- Monthly working hours: {emp.get('monthly_hours', 'N/A')} hrs
- Current project allocation: {emp.get('total_allocation', 0)}%
- Number of active projects: {emp.get('num_projects', 0)}
- Department: {emp.get('department', 'Unknown')}
- Approved skill count: {emp.get('skill_count', 0)}

Analyze and respond with this exact JSON:
{{
  "risk": "High",
  "probability": 72,
  "explanation": [
    {{"factor": "Low satisfaction score", "direction": "increases risk", "impact": "High"}},
    {{"factor": "Overworked (>200 hrs/month)", "direction": "increases risk", "impact": "Medium"}},
    {{"factor": "Strong skill portfolio", "direction": "reduces risk", "impact": "Low"}}
  ],
  "suggestion": "Schedule a 1:1 check-in to understand dissatisfaction. Consider redistributing project load."
}}

Risk levels: High (>60% likely to leave in 6 months), Medium (30-60%), Low (<30%).
Probability should be an integer 0-100.
Limit explanation to top 3-5 factors.
"""
    try:
        raw = _chat(system, user, max_tokens=500)
        data = _parse_json(raw)
        # Validate structure
        if 'risk' not in data:
            raise ValueError("Missing risk field")
        return data
    except Exception:
        # Deterministic fallback if API fails
        sat   = float(emp.get('satisfaction_score', 3.0))
        hours = int(emp.get('monthly_hours', 160))
        alloc = int(emp.get('total_allocation', 0))
        score = int(
            max(0, (3.0 - sat) / 3.0 * 40) +
            max(0, (hours - 160) / 100 * 30) +
            max(0, (alloc - 80) / 50 * 20)
        )
        risk = 'High' if score > 55 else 'Medium' if score > 25 else 'Low'
        return {
            'risk': risk,
            'probability': min(score, 95),
            'explanation': [{'factor': 'Combined metrics', 'direction': 'assessed', 'impact': 'Medium'}],
            'suggestion': 'Review employee workload and satisfaction.'
        }


def suggest_training(skill_gaps: list[str], department: str) -> str:
    """
    Given a list of skill gaps, suggest training resources.
    Returns a short markdown string.
    """
    if not skill_gaps:
        return "No skill gaps identified."
    system = "You are an HR training advisor. Be concise and practical."
    user = (
        f"Department: {department}\n"
        f"Skill gaps identified: {', '.join(skill_gaps)}\n\n"
        "Suggest 3 specific, free or low-cost training resources (with course names and platforms). "
        "Keep it under 120 words."
    )
    try:
        return _chat(system, user, max_tokens=200)
    except Exception:
        return f"Suggested training for: {', '.join(skill_gaps)}. Check Coursera, Udemy, or freeCodeCamp."
