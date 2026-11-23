from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict


def _clean(text: str) -> str:
    """Enlève les balises HTML et normalise les espaces."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class Job:
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    summary: str = ""
    posted: str = ""
    source: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.title = _clean(self.title)
        self.company = _clean(self.company)
        self.location = _clean(self.location)
        self.summary = _clean(self.summary)

    @property
    def fingerprint(self) -> str:
        """Identifiant stable pour la déduplication et l'historique.

        On se base sur l'URL si présente, sinon sur titre+entreprise normalisés.
        """
        basis = self.url.strip().lower()
        if not basis:
            basis = f"{self.title.lower()}|{self.company.lower()}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()

    @property
    def haystack(self) -> str:
        """Texte sur lequel le scoring cherche ses mots-clés."""
        return f"{self.title} {self.location} {self.summary}".lower()

    def to_dict(self) -> dict:
        return asdict(self)
