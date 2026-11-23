"""Historique SQLite : savoir ce qui est nouveau depuis le dernier passage."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Job


class Store:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                fingerprint TEXT PRIMARY KEY,
                title TEXT, company TEXT, location TEXT, url TEXT,
                source TEXT, score INTEGER,
                first_seen TEXT, last_seen TEXT
            )
        """)
        self.conn.commit()

    def mark_seen(self, jobs: list[Job]) -> set[str]:
        """Enregistre/actualise les offres. Renvoie les fingerprints VUS POUR LA 1re FOIS."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new: set[str] = set()
        for j in jobs:
            fp = j.fingerprint
            row = self.conn.execute(
                "SELECT fingerprint FROM jobs WHERE fingerprint = ?", (fp,)
            ).fetchone()
            if row is None:
                new.add(fp)
                self.conn.execute(
                    "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                    (fp, j.title, j.company, j.location, j.url, j.source, j.score, now, now),
                )
            else:
                self.conn.execute(
                    "UPDATE jobs SET last_seen = ?, score = ? WHERE fingerprint = ?",
                    (now, j.score, fp),
                )
        self.conn.commit()
        return new

    def close(self):
        self.conn.close()


def dedupe(jobs: list[Job]) -> list[Job]:
    """Supprime les doublons intra-session en gardant la 1re occurrence (meilleur score d'abord)."""
    seen: set[str] = set()
    out: list[Job] = []
    for j in sorted(jobs, key=lambda x: x.score, reverse=True):
        if j.fingerprint in seen:
            continue
        seen.add(j.fingerprint)
        out.append(j)
    return out
