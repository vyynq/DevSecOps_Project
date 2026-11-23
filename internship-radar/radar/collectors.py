"""Collecte des offres depuis des flux RSS ou des API JSON publics."""
from __future__ import annotations

import json
import time
from typing import Any

from .models import Job

USER_AGENT = "internship-radar/1.0 (+personal job search; contact via application)"
REQUEST_TIMEOUT = 15
PAUSE_BETWEEN_SOURCES = 1.0  # politesse : on ne martèle pas les serveurs


def _get(path: str, obj: Any) -> Any:
    """Résout un chemin JSON pointé façon 'company.name'. Pas de '[]' ici."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _resolve_list(spec: str, data: Any) -> list:
    """'results[]' -> data['results'] (une liste)."""
    key = spec.replace("[]", "")
    val = _get(key, data) if key else data
    return val if isinstance(val, list) else []


def parse_json_payload(text: str, mapping: dict, source_name: str) -> list[Job]:
    """Séparé de la requête réseau pour être testable hors-ligne."""
    data = json.loads(text) if isinstance(text, str) else text
    jobs = []
    for item in _resolve_list(mapping.get("list", ""), data):
        jobs.append(Job(
            title=_get(mapping.get("title", "title"), item) or "",
            company=_get(mapping.get("company", "company"), item) or "",
            location=_get(mapping.get("location", "location"), item) or "",
            url=_get(mapping.get("url", "url"), item) or "",
            summary=_get(mapping.get("summary", "summary"), item) or "",
            posted=str(_get(mapping.get("posted", "posted"), item) or ""),
            source=source_name,
        ))
    return jobs


def parse_rss_bytes(content: bytes, source_name: str) -> list[Job]:
    import feedparser
    feed = feedparser.parse(content)
    jobs = []
    for e in feed.entries:
        jobs.append(Job(
            title=getattr(e, "title", ""),
            company=getattr(e, "author", ""),
            location="",  # souvent dans le titre/résumé pour un flux RSS
            url=getattr(e, "link", ""),
            summary=getattr(e, "summary", ""),
            posted=getattr(e, "published", getattr(e, "updated", "")),
            source=source_name,
        ))
    return jobs


def fetch_source(source: dict) -> list[Job]:
    """Effectue la requête réseau puis délègue au parseur adapté."""
    import requests
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(source["url"], headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if source["type"] == "json":
        return parse_json_payload(resp.text, source.get("mapping", {}), source["name"])
    if source["type"] == "rss":
        return parse_rss_bytes(resp.content, source["name"])
    raise ValueError(f"type de source inconnu : {source['type']}")


def collect(sources: list[dict]) -> list[Job]:
    jobs: list[Job] = []
    for src in sources:
        if not src.get("enabled", True):
            continue
        try:
            found = fetch_source(src)
            print(f"  [{src['name']}] {len(found)} offres")
            jobs.extend(found)
        except Exception as exc:  # une source en panne ne doit pas tout bloquer
            print(f"  [{src['name']}] ERREUR : {exc}")
        time.sleep(PAUSE_BETWEEN_SOURCES)
    return jobs
