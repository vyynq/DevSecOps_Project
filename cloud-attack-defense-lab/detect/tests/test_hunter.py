"""Tests sur des logs CloudTrail synthétiques. Lancer : python3 -m unittest discover -s detect/tests"""
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloudtrail_hunter as h  # noqa: E402

ACCOUNT = "111122223333"


def ev(name, minute=0, user="raynor", error=None, ip="203.0.113.10", key="AKIAEXAMPLE0001", **extra):
    e = {
        "eventTime": f"2026-11-10T10:{minute:02d}:00Z",
        "eventName": name,
        "eventSource": "iam.amazonaws.com",
        "sourceIPAddress": ip,
        "userIdentity": {
            "type": "IAMUser",
            "arn": f"arn:aws:iam::{ACCOUNT}:user/{user}",
            "accessKeyId": key,
        },
    }
    if error:
        e["errorCode"] = error
    e.update(extra)
    return e


def rules_hit(events):
    return {f.rule for f in h.hunt(events)}


class TestRules(unittest.TestCase):
    def test_benign_activity_is_quiet(self):
        events = [ev("ListUsers", 1), ev("GetUser", 2), ev("CreateAccessKey", 3, requestParameters={"userName": "raynor"})]
        self.assertEqual(h.hunt(events), [])

    def test_rollback(self):
        e = ev("SetDefaultPolicyVersion", requestParameters={"policyArn": "arn:aws:iam::1:policy/p", "versionId": "v3"})
        self.assertIn("policy_version_tampering", rules_hit([e]))

    def test_failed_rollback_not_reported_as_tampering(self):
        e = ev("SetDefaultPolicyVersion", error="AccessDenied", requestParameters={"policyArn": "p", "versionId": "v3"})
        self.assertNotIn("policy_version_tampering", rules_hit([e]))

    def test_admin_attached(self):
        e = ev("AttachUserPolicy", requestParameters={
            "userName": "raynor", "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"})
        self.assertIn("admin_policy_attached", rules_hit([e]))

    def test_inline_wildcard(self):
        doc = json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]})
        e = ev("PutUserPolicy", requestParameters={"userName": "raynor", "policyDocument": doc})
        self.assertIn("admin_policy_attached", rules_hit([e]))

    def test_passrole_lambda_then_invoke(self):
        create = ev("CreateFunction20150331", 1, requestParameters={
            "functionName": "f", "role": f"arn:aws:iam::{ACCOUNT}:role/admin-role"})
        invoke = ev("Invoke", 3, requestParameters={"functionName": "f"})
        findings = [f for f in h.hunt([create, invoke]) if f.rule == "passrole_compute"]
        self.assertEqual({f.severity for f in findings}, {"MEDIUM", "HIGH"})

    def test_key_for_other_user(self):
        e = ev("CreateAccessKey", requestParameters={"userName": "admin"})
        self.assertIn("access_key_for_other_user", rules_hit([e]))

    def test_stop_logging(self):
        self.assertIn("defense_evasion", rules_hit([ev("StopLogging")]))

    def test_console_no_mfa(self):
        e = ev("ConsoleLogin", responseElements={"ConsoleLogin": "Success"}, additionalEventData={"MFAUsed": "No"})
        self.assertIn("console_login_no_mfa", rules_hit([e]))

    def test_enumeration_burst(self):
        events = [ev("ListRoles", minute=i // 3, error="AccessDenied") for i in range(12)]
        self.assertIn("enumeration_burst", rules_hit(events))

    def test_enumeration_spread_out_is_quiet(self):
        events = [ev("ListRoles", minute=i * 5, error="AccessDenied") for i in range(11)]
        self.assertNotIn("enumeration_burst", rules_hit(events))

    def test_stolen_temp_key(self):
        events = [
            ev("ListBuckets", 1, key="ASIATEMPKEY00001", ip="10.0.1.25"),
            ev("ListBuckets", 2, key="ASIATEMPKEY00001", ip="198.51.100.7"),
        ]
        f = [x for x in h.hunt(events) if x.rule == "key_multi_ip"]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "HIGH")


class TestLoading(unittest.TestCase):
    def test_load_gz_and_skip_digest(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with gzip.open(d / "a.json.gz", "wt") as fh:
                json.dump({"Records": [ev("StopLogging", 5), ev("ListUsers", 1)]}, fh)
            (d / "digest.json").write_text(json.dumps({"digestStartTime": "x"}))
            events = h.load_events(d)
            self.assertEqual([e["eventName"] for e in events], ["ListUsers", "StopLogging"])
            self.assertEqual(h.main([str(d), "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
