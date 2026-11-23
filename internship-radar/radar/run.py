"""Point d'entrée : python3 -m radar.run [--fixtures fichier.json]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .collectors import collect, parse_json_payload
from .models import Job
from .render import render_csv, render_html
from .scoring import rank
from .store import Store, dedupe

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_profile() -> dict:
    for name in ("profile.yaml", "profile.example.yaml"):
        p = ROOT / name
        if p.exists():
            return load_yaml(p)
    raise FileNotFoundError("aucun profile.yaml ni profile.example.yaml")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Radar à offres de stage")
    ap.add_argument("--fixtures", help="fichier JSON d'offres d'exemple (mode hors-ligne)")
    ap.add_argument("--db", default=str(ROOT / "output" / "history.db"))
    ap.add_argument("--outdir", default=str(ROOT / "output"))
    args = ap.parse_args(argv)

    profile = load_profile()

    if args.fixtures:
        print(f"Chargement des fixtures {args.fixtures}")
        raw = Path(args.fixtures).read_text(encoding="utf-8")
        jobs = parse_json_payload(raw, {"list": "jobs[]", "title": "title", "company": "company",
                                        "location": "location", "url": "url", "summary": "summary",
                                        "posted": "posted"}, "fixtures")
    else:
        print("Collecte des sources...")
        sources = load_yaml(ROOT / "sources.yaml").get("sources", [])
        jobs = collect(sources)

    print(f"{len(jobs)} offres collectées")
    ranked = rank(jobs, profile)
    ranked = dedupe(ranked)
    print(f"{len(ranked)} offres retenues après scoring et déduplication")

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    store = Store(args.db)
    new_fps = store.mark_seen(ranked)
    store.close()
    print(f"{len(new_fps)} nouvelle(s) offre(s) depuis le dernier passage")

    html_path = render_html(ranked, new_fps, Path(args.outdir) / "dashboard.html")
    csv_path = render_csv(ranked, Path(args.outdir) / "offres.csv")
    print(f"Tableau de bord : {html_path}")
    print(f"CSV            : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
