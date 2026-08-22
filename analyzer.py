import re
from datetime import datetime, timezone

def _has(text, words):
    t = (text or "").lower()
    return any(w in t for w in words)

def analyze(item):
    """Rule-based baseline. Returns explainable score and flags."""
    text = " ".join([
        item.get("title",""), item.get("description",""),
        item.get("profile",""), item.get("participant_countries","")
    ])
    score = 0
    reasons = []

    if item.get("algeria_status") == "ELIGIBLE":
        score += 40; reasons.append("Algeria explicitly listed")
    elif item.get("algeria_status") == "UNKNOWN":
        score += 5; reasons.append("Eligibility needs verification")
    else:
        return {**item, "match_score": 0, "match_reasons": ["Algeria not listed"]}

    if _has(text, ["no previous experience", "experience is not required", "not required"]):
        score += 15; reasons.append("No previous experience required")
    if _has(text, ["english", "anglais"]):
        score += 5; reasons.append("English mentioned")
    if _has(text, ["accommodation", "housing", "hébergement"]):
        score += 10; reasons.append("Accommodation mentioned")
    if _has(text, ["food", "meal", "subsistence", "nourriture"]):
        score += 8; reasons.append("Food/subsistence mentioned")
    if _has(text, ["travel", "transport", "voyage"]):
        score += 8; reasons.append("Travel/transport mentioned")
    if _has(text, ["pocket money", "allowance", "argent de poche"]):
        score += 7; reasons.append("Pocket money mentioned")

    score = min(score, 100)
    return {**item, "match_score": score, "match_reasons": reasons}
