"""Rendu du tableau de bord HTML et export CSV."""
from __future__ import annotations

import csv
import html
from datetime import datetime, timezone
from pathlib import Path

from .models import Job

_TEMPLATE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar à offres — {generated}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#e2e2e2; --chip:#eef2ff; --chipfg:#3730a3; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#15171c; --fg:#e8e8e8; --muted:#9aa0aa; --line:#2a2d35; --chip:#1e2a4a; --chipfg:#a6c0ff; }} }}
  body {{ font-family: system-ui, -apple-system, sans-serif; margin:0; background:var(--bg); color:var(--fg); }}
  header {{ padding:24px 20px; border-bottom:1px solid var(--line); }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); font-size:14px; }}
  .wrap {{ padding:16px 20px; max-width:900px; margin:0 auto; }}
  .job {{ border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin:12px 0; }}
  .job.new {{ border-left:4px solid #4f46e5; }}
  .top {{ display:flex; justify-content:space-between; gap:12px; align-items:baseline; }}
  .title {{ font-weight:600; font-size:16px; }}
  .title a {{ color:inherit; text-decoration:none; }}
  .title a:hover {{ text-decoration:underline; }}
  .score {{ font-variant-numeric:tabular-nums; font-weight:700; white-space:nowrap; }}
  .meta {{ color:var(--muted); font-size:13px; margin:4px 0 8px; }}
  .badge {{ background:#4f46e5; color:#fff; border-radius:6px; font-size:11px; padding:1px 6px; margin-left:6px; }}
  .reasons span {{ display:inline-block; background:var(--chip); color:var(--chipfg); border-radius:6px;
                   font-size:11px; padding:2px 7px; margin:2px 3px 0 0; }}
</style></head><body>
<header><h1>Radar à offres — stage cloud / cybersécurité</h1>
<div class="sub">{count} offres · généré le {generated} · {new_count} nouvelle(s)</div></header>
<div class="wrap">
{rows}
</div></body></html>"""

_ROW = """<div class="job {new}">
  <div class="top">
    <div class="title"><a href="{url}" target="_blank" rel="noopener">{title}</a>{badge}</div>
    <div class="score">{score}</div>
  </div>
  <div class="meta">{company}{sep}{location}{srcsep}<em>{source}</em></div>
  <div class="reasons">{reasons}</div>
</div>"""


def render_html(jobs: list[Job], new_fps: set[str], out: str | Path) -> Path:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows = []
    for j in jobs:
        is_new = j.fingerprint in new_fps
        reasons = "".join(f"<span>{html.escape(r)}</span>" for r in j.reasons)
        rows.append(_ROW.format(
            new="new" if is_new else "",
            url=html.escape(j.url or "#"),
            title=html.escape(j.title or "(sans titre)"),
            badge='<span class="badge">NOUVEAU</span>' if is_new else "",
            score=j.score,
            company=html.escape(j.company),
            sep=" · " if j.company and j.location else "",
            location=html.escape(j.location),
            srcsep=" · " if (j.company or j.location) else "",
            source=html.escape(j.source),
            reasons=reasons,
        ))
    doc = _TEMPLATE.format(
        count=len(jobs), new_count=len(new_fps), generated=generated, rows="\n".join(rows),
    )
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


def render_csv(jobs: list[Job], out: str | Path) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["score", "title", "company", "location", "source", "url"])
        for j in jobs:
            w.writerow([j.score, j.title, j.company, j.location, j.source, j.url])
    return out
