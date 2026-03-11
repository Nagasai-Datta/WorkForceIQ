"""
TF-IDF based skill extractor.
Takes free-form resume text, returns matched skill names from our DB.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re

# Canonical skill list (maps to skill_name in DB)
SKILL_ALIASES = {
    'python':             ['python', 'py', 'python3'],
    'react':              ['react', 'reactjs', 'react.js'],
    'sql':                ['sql', 'mysql', 'postgresql', 'postgres', 'sqlite'],
    'java':               ['java', 'jvm'],
    'machine learning':   ['machine learning', 'ml', 'deep learning', 'neural network'],
    'django':             ['django'],
    'flask':              ['flask'],
    'node.js':            ['node', 'nodejs', 'node.js', 'express'],
    'aws':                ['aws', 'amazon web services', 'ec2', 's3', 'lambda'],
    'docker':             ['docker', 'dockerfile', 'containerisation', 'containerization'],
    'kubernetes':         ['kubernetes', 'k8s', 'kubectl'],
    'data analysis':      ['data analysis', 'data analytics', 'pandas', 'numpy', 'matplotlib'],
    'ui/ux design':       ['ui', 'ux', 'figma', 'wireframe', 'prototype', 'user experience'],
    'project management': ['project management', 'agile', 'scrum', 'jira', 'kanban', 'sprint'],
    'javascript':         ['javascript', 'js', 'typescript', 'ts', 'es6'],
    'git':                ['git', 'github', 'gitlab', 'version control'],
    'tableau':            ['tableau', 'power bi', 'powerbi', 'data visualization'],
    'tensorflow':         ['tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn'],
}

def extract_skills_tfidf(resume_text: str) -> list[str]:
    """
    1. Lowercase and clean the resume text
    2. Build a TF-IDF corpus (resume + one doc per skill alias group)
    3. Score each canonical skill: any alias found → score its TF-IDF weight
    4. Return skills with non-zero score, sorted by relevance
    """
    if not resume_text or len(resume_text.strip()) < 15:
        return []

    text = resume_text.lower()
    text = re.sub(r'[^a-z0-9\s\.\+\#]', ' ', text)

    # Build corpus: [resume, skill_doc_1, skill_doc_2, ...]
    canonical = list(SKILL_ALIASES.keys())
    skill_docs = [' '.join(aliases) for aliases in SKILL_ALIASES.values()]
    corpus = [text] + skill_docs

    try:
        vec = TfidfVectorizer(
            ngram_range=(1, 3),
            stop_words='english',
            min_df=1,
            max_features=3000
        )
        tfidf = vec.fit_transform(corpus)
        feature_names = vec.get_feature_names_out()
        resume_row = np.asarray(tfidf[0]).ravel()   # Dense TF-IDF vector for resume

        matched = []
        for skill_name, aliases in SKILL_ALIASES.items():
            score = 0.0
            for alias in aliases:
                alias_tokens = alias.lower().split()
                for token in alias_tokens:
                    if token in feature_names:
                        idx = list(feature_names).index(token)
                        score += resume_row[idx]
                # Also do raw substring match as safety net
                if alias in text:
                    score += 0.15
            if score > 0.05:
                matched.append((skill_name, score))

        matched.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in matched[:12]]

    except Exception:
        # Fallback: simple keyword match
        found = []
        for skill_name, aliases in SKILL_ALIASES.items():
            if any(alias in text for alias in aliases):
                found.append(skill_name)
        return found
