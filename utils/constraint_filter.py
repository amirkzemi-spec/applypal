# utils/constraint_filter.py
"""
Constraint-based country filtering logic for Nika Visa AI.
This module narrows down study destinations based on user profile:
- budget (USD/EUR equivalent)
- IELTS score
- age
Each country has approximate minimum thresholds and living cost ranges.
"""

import json, os

# -----------------------------
# Country rules
# -----------------------------
DEFAULT_RULES = {
    "Netherlands":  {"min_budget": 12000, "min_ielts": 6.5, "max_age": 40},
    "Germany":      {"min_budget": 8000,  "min_ielts": 6.0, "max_age": 45},
    "Switzerland":  {"min_budget": 15000, "min_ielts": 6.5, "max_age": 40},
    "Italy":        {"min_budget": 7000,  "min_ielts": 5.5, "max_age": 45},
    "Canada":       {"min_budget": 18000, "min_ielts": 6.0, "max_age": 40},
    "USA":          {"min_budget": 20000, "min_ielts": 6.5, "max_age": 38},
    "United Kingdom": {"min_budget": 16000, "min_ielts": 6.0, "max_age": 40},
    "Sweden":       {"min_budget": 12000, "min_ielts": 6.0, "max_age": 40},
    "Finland":      {"min_budget": 10000, "min_ielts": 6.0, "max_age": 45},
    "Norway":       {"min_budget": 11000, "min_ielts": 6.0, "max_age": 45},
    "Austria":      {"min_budget": 9500,  "min_ielts": 5.5, "max_age": 45},
    "France":       {"min_budget": 12000, "min_ielts": 6.0, "max_age": 40},
}

RULES_PATH = os.path.join(os.path.dirname(__file__), "constraint_rules.json")


# -----------------------------
# Optional: Load external JSON overrides
# -----------------------------
def load_rules():
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read {RULES_PATH}: {e}")
    return DEFAULT_RULES


# -----------------------------
# Core filter function
# -----------------------------
def filter_countries(profile: dict):
    """
    Given a user profile (budget, IELTS, age),
    return a list of suitable countries.
    """
    rules = load_rules()
    budget = float(profile.get("budget", 0) or 0)
    ielts = float(profile.get("ielts", 0) or 0)
    age = float(profile.get("age", 0) or 0)

    recommendations = []
    for country, r in rules.items():
        if (
            budget >= r["min_budget"] * 0.9  # tolerate slight under-budget
            and ielts >= r["min_ielts"] - 0.5  # allow small margin
            and age <= r["max_age"]
        ):
            recommendations.append(country)

    # Fallback: if nothing fits, return cheapest + easiest
    if not recommendations:
        recommendations = sorted(rules.keys(), key=lambda c: rules[c]["min_budget"])[:2]

    return recommendations


# -----------------------------
# Quick test (run manually)
# -----------------------------
if __name__ == "__main__":
    test_user = {"budget": 8000, "ielts": 6.0, "age": 28}
    recs = filter_countries(test_user)
    print(f"🧭 Recommended countries for {test_user}: {recs}")
