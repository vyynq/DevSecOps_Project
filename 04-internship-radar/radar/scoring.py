"""Scoring d'une offre par rapport au profil. Pur (pas d'I/O) : facile à tester."""
from __future__ import annotations

from .models import Job

EXCLUDED_LOCATION_PENALTY = 15


def score_job(job: Job, profile: dict) -> Job:
    score = 0
    reasons: list[str] = []
    hay = job.haystack

    # 1. Filtre d'entrée : le titre/résumé doit matcher au moins un terme requis.
    must = [t.lower() for t in profile.get("titles_must_match_any", [])]
    if must and not any(t in hay for t in must):
        job.score = 0
        job.reasons = ["hors sujet (aucun terme requis trouvé)"]
        return job

    # 2. Mots-clés techniques.
    for kw, weight in profile.get("keywords", {}).items():
        if kw.lower() in hay:
            score += weight
            reasons.append(f"+{weight} {kw}")

    # 3. Localisation.
    loc = f"{job.location} {job.summary}".lower()
    for place, weight in profile.get("locations_preferred", {}).items():
        if place.lower() in loc:
            score += weight
            reasons.append(f"+{weight} lieu:{place}")
            break  # on ne compte le bonus de lieu qu'une fois
    for bad in profile.get("locations_excluded", []):
        if bad.lower() in loc:
            score -= EXCLUDED_LOCATION_PENALTY
            reasons.append(f"-{EXCLUDED_LOCATION_PENALTY} lieu exclu:{bad}")

    # 4. Durée / type de contrat.
    for kw, weight in profile.get("duration_keywords", {}).items():
        if kw.lower() in hay:
            score += weight
            reasons.append(f"+{weight} durée:{kw}")
            break

    # 5. Signaux de rémunération.
    for sig in profile.get("pay_signals", []):
        if sig.lower() in hay:
            score += 3
            reasons.append("+3 rémunération mentionnée")
            break

    job.score = score
    job.reasons = reasons
    return job


def rank(jobs: list[Job], profile: dict) -> list[Job]:
    scored = [score_job(j, profile) for j in jobs]
    threshold = profile.get("min_score_to_show", 0)
    kept = [j for j in scored if j.score >= threshold]
    kept.sort(key=lambda j: j.score, reverse=True)
    return kept
