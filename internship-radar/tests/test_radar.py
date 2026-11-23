"""Tests du pipeline. Lancer : python3 -m unittest discover -s tests"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar.models import Job            # noqa: E402
from radar.scoring import rank, score_job  # noqa: E402
from radar.collectors import parse_json_payload  # noqa: E402
from radar.store import Store, dedupe   # noqa: E402

PROFILE = {
    "titles_must_match_any": ["cloud", "security", "sécurité"],
    "keywords": {"aws": 6, "terraform": 6, "cloud security": 8, "kubernetes": 5},
    "locations_preferred": {"germany": 8, "europe": 3},
    "locations_excluded": ["united states", "usa"],
    "duration_keywords": {"6 month": 6, "internship": 3},
    "pay_signals": ["paid", "vergütung"],
    "min_score_to_show": 10,
}


class TestModels(unittest.TestCase):
    def test_html_is_stripped(self):
        j = Job(title="  <b>Cloud</b>  Eng ", summary="<p>AWS &amp; more</p>")
        self.assertEqual(j.title, "Cloud Eng")
        self.assertIn("AWS", j.summary)

    def test_fingerprint_prefers_url(self):
        a = Job(title="X", company="A", url="https://e.com/1")
        b = Job(title="Y", company="B", url="https://e.com/1")
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_fingerprint_without_url(self):
        a = Job(title="Cloud Eng", company="Siemens")
        b = Job(title="cloud eng", company="siemens")
        self.assertEqual(a.fingerprint, b.fingerprint)


class TestScoring(unittest.TestCase):
    def test_relevant_job_scores_high(self):
        j = Job(title="Cloud Security Engineer", location="Munich, Germany",
                summary="AWS Terraform Kubernetes, 6 month internship, paid")
        score_job(j, PROFILE)
        self.assertGreater(j.score, 20)

    def test_off_topic_filtered(self):
        j = Job(title="Marketing Intern", summary="social media content")
        score_job(j, PROFILE)
        self.assertEqual(j.score, 0)

    def test_excluded_location_penalised(self):
        j = Job(title="Cloud Engineer", location="Seattle, United States",
                summary="AWS terraform internship")
        score_job(j, PROFILE)
        off = Job(title="Cloud Engineer", location="Berlin, Germany",
                  summary="AWS terraform internship")
        score_job(off, PROFILE)
        self.assertLess(j.score, off.score)

    def test_threshold_applied(self):
        jobs = [
            Job(title="Cloud Security Engineer", location="Germany",
                summary="aws terraform kubernetes 6 month paid"),
            Job(title="Cloud thing", location="", summary="vague"),
        ]
        kept = rank(jobs, PROFILE)
        self.assertEqual(len(kept), 1)


class TestCollectorParsing(unittest.TestCase):
    def test_parse_json_with_fixture_mapping(self):
        payload = '{"jobs":[{"title":"Cloud Sec","company":"X","location":"DE","url":"u","summary":"aws"}]}'
        mapping = {"list": "jobs[]", "title": "title", "company": "company",
                   "location": "location", "url": "url", "summary": "summary"}
        jobs = parse_json_payload(payload, mapping, "test")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "X")

    def test_nested_json_path(self):
        payload = '{"results":[{"title":"T","company":{"name":"Acme"}}]}'
        mapping = {"list": "results[]", "title": "title", "company": "company.name"}
        jobs = parse_json_payload(payload, mapping, "test")
        self.assertEqual(jobs[0].company, "Acme")


class TestStore(unittest.TestCase):
    def test_dedupe_keeps_best(self):
        a = Job(title="T", url="https://e/1", score=5)
        b = Job(title="T", url="https://e/1", score=9)
        out = dedupe([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].score, 9)

    def test_new_then_not_new(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "h.db"
            jobs = [Job(title="Cloud", url="https://e/1", score=20)]
            s = Store(db)
            self.assertEqual(len(s.mark_seen(jobs)), 1)   # 1re fois : nouveau
            self.assertEqual(len(s.mark_seen(jobs)), 0)   # 2e fois : connu
            s.close()


if __name__ == "__main__":
    unittest.main()
