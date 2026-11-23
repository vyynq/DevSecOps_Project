#!/usr/bin/env python3
"""
cloudtrail_hunter — détection de comportements suspects dans des logs CloudTrail.

Usage :
    python3 cloudtrail_hunter.py <fichier_ou_dossier> [--since ISO8601] [--json] [--burst 10]

Entrée : fichiers CloudTrail tels que livrés dans S3 ({"Records": [...]}),
en .json ou .json.gz, ou un dossier contenant ces fichiers (récursif).

Chaque règle est une fonction qui reçoit la liste des événements (triés par date)
et renvoie une liste de Finding. Pour ajouter une règle : écrire la fonction,
l'ajouter à RULES, et écrire un test dans tests/.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

# --------------------------------------------------------------------------- #
# Modèle
# --------------------------------------------------------------------------- #

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


@dataclass
class Finding:
    rule: str
    severity: str
    mitre: str
    time: str
    actor: str
    summary: str


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def actor_of(event: dict) -> str:
    ident = event.get("userIdentity", {}) or {}
    return ident.get("arn") or ident.get("principalId") or ident.get("type", "unknown")


def succeeded(event: dict) -> bool:
    return not event.get("errorCode")


def params(event: dict) -> dict:
    return event.get("requestParameters") or {}


# --------------------------------------------------------------------------- #
# Chargement
# --------------------------------------------------------------------------- #

def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*")):
        if p.is_file() and (p.name.endswith(".json") or p.name.endswith(".json.gz")):
            yield p


def load_events(path: Path, since: datetime | None = None) -> list[dict]:
    events: list[dict] = []
    for f in iter_files(path):
        opener = gzip.open if f.name.endswith(".gz") else open
        try:
            with opener(f, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[!] fichier ignoré {f}: {exc}", file=sys.stderr)
            continue
        # Les fichiers "digest" (validation d'intégrité) n'ont pas de clé Records.
        for rec in data.get("Records", []) if isinstance(data, dict) else []:
            if "eventTime" not in rec:
                continue
            if since and parse_time(rec["eventTime"]) < since:
                continue
            events.append(rec)
    events.sort(key=lambda e: e["eventTime"])
    return events


# --------------------------------------------------------------------------- #
# Règles
# --------------------------------------------------------------------------- #

def rule_policy_version_tampering(events: list[dict]) -> list[Finding]:
    """Changement de version par défaut d'une policy : technique de rollback de privilèges."""
    out = []
    for e in events:
        name = e.get("eventName")
        if succeeded(e) and name == "SetDefaultPolicyVersion":
            p = params(e)
            out.append(Finding(
                "policy_version_tampering", "HIGH", "TA0004 Privilege Escalation",
                e["eventTime"], actor_of(e),
                f"version par défaut de {p.get('policyArn')} -> {p.get('versionId')}",
            ))
        elif succeeded(e) and name == "CreatePolicyVersion" and params(e).get("setAsDefault"):
            out.append(Finding(
                "policy_version_tampering", "HIGH", "TA0004 Privilege Escalation",
                e["eventTime"], actor_of(e),
                f"nouvelle version par défaut créée pour {params(e).get('policyArn')}",
            ))
    return out


ADMIN_POLICY_SUFFIX = "/AdministratorAccess"


def _policy_document_is_wildcard(doc) -> bool:
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except json.JSONDecodeError:
            return False
    stmts = doc.get("Statement", []) if isinstance(doc, dict) else []
    if isinstance(stmts, dict):
        stmts = [stmts]
    for s in stmts:
        if s.get("Effect") != "Allow":
            continue
        actions = s.get("Action", [])
        resources = s.get("Resource", [])
        actions = [actions] if isinstance(actions, str) else actions
        resources = [resources] if isinstance(resources, str) else resources
        if "*" in actions and "*" in resources:
            return True
    return False


def rule_admin_policy_attached(events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        if not succeeded(e):
            continue
        name, p = e.get("eventName"), params(e)
        target = p.get("userName") or p.get("roleName") or p.get("groupName")
        if name in ("AttachUserPolicy", "AttachRolePolicy", "AttachGroupPolicy") \
                and str(p.get("policyArn", "")).endswith(ADMIN_POLICY_SUFFIX):
            out.append(Finding(
                "admin_policy_attached", "CRITICAL", "TA0004 Privilege Escalation",
                e["eventTime"], actor_of(e), f"AdministratorAccess attachée à {target}",
            ))
        elif name in ("PutUserPolicy", "PutRolePolicy", "PutGroupPolicy") \
                and _policy_document_is_wildcard(p.get("policyDocument")):
            out.append(Finding(
                "admin_policy_attached", "CRITICAL", "TA0004 Privilege Escalation",
                e["eventTime"], actor_of(e), f"policy inline Allow *:* posée sur {target}",
            ))
    return out


COMPUTE_CREATION = {
    "CreateFunction20150331", "CreateFunction", "UpdateFunctionConfiguration20150331v2",
    "RunInstances", "CreateStack", "CreateJob", "CreateDevEndpoint",
}


def rule_passrole_compute(events: list[dict], window_minutes: int = 30) -> list[Finding]:
    """
    PassRole n'apparaît pas toujours comme événement séparé : on regarde aussi
    les créations de compute qui portent un rôle dans leurs paramètres.
    Sévérité plus haute si le principal n'avait jamais créé ce type de ressource.
    """
    out = []
    for e in events:
        if not succeeded(e) or e.get("eventName") not in COMPUTE_CREATION:
            continue
        p = params(e)
        role = p.get("role") or (p.get("iamInstanceProfile") or {}).get("arn") \
            or (p.get("iamInstanceProfile") or {}).get("name") or p.get("roleARN")
        if not role:
            continue
        out.append(Finding(
            "passrole_compute", "MEDIUM", "TA0004 Privilege Escalation",
            e["eventTime"], actor_of(e),
            f"{e['eventName']} avec le rôle {role} (vérifier que ce principal peut légitimement le passer)",
        ))
    # Corrélation : une invocation de la fonction juste après sa création -> HIGH
    created = {}
    for e in events:
        if succeeded(e) and e.get("eventName", "").startswith("CreateFunction"):
            created[(actor_of(e), params(e).get("functionName"))] = parse_time(e["eventTime"])
    for e in events:
        if e.get("eventName", "").startswith("Invoke") and succeeded(e):
            key = (actor_of(e), params(e).get("functionName"))
            t0 = created.get(key)
            if t0 and parse_time(e["eventTime"]) - t0 <= timedelta(minutes=window_minutes):
                out.append(Finding(
                    "passrole_compute", "HIGH", "TA0004 Privilege Escalation",
                    e["eventTime"], actor_of(e),
                    f"fonction {key[1]} créée puis invoquée en moins de {window_minutes} min",
                ))
    return out


def rule_access_key_for_other_user(events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        if not succeeded(e) or e.get("eventName") != "CreateAccessKey":
            continue
        target = params(e).get("userName")
        actor = actor_of(e)
        actor_name = actor.rsplit("/", 1)[-1]
        if target and target != actor_name:
            out.append(Finding(
                "access_key_for_other_user", "HIGH", "TA0003 Persistence",
                e["eventTime"], actor, f"clé d'accès créée pour l'utilisateur {target}",
            ))
    return out


EVASION_EVENTS = {
    "StopLogging", "DeleteTrail", "UpdateTrail", "PutEventSelectors",
    "DeleteDetector", "UpdateDetector", "DisassociateFromMasterAccount",
    "DeleteFlowLogs", "DeleteConfigurationRecorder", "StopConfigurationRecorder",
}


def rule_defense_evasion(events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        if e.get("eventName") in EVASION_EVENTS:
            status = "réussi" if succeeded(e) else f"échoué ({e.get('errorCode')})"
            out.append(Finding(
                "defense_evasion", "CRITICAL" if succeeded(e) else "HIGH", "TA0005 Defense Evasion",
                e["eventTime"], actor_of(e), f"{e['eventName']} {status}",
            ))
    return out


def rule_console_login_no_mfa(events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        if e.get("eventName") != "ConsoleLogin":
            continue
        ok = (e.get("responseElements") or {}).get("ConsoleLogin") == "Success"
        mfa = (e.get("additionalEventData") or {}).get("MFAUsed")
        if ok and mfa != "Yes":
            out.append(Finding(
                "console_login_no_mfa", "MEDIUM", "TA0001 Initial Access",
                e["eventTime"], actor_of(e), f"connexion console sans MFA depuis {e.get('sourceIPAddress')}",
            ))
    return out


DENIED_CODES = {"AccessDenied", "AccessDeniedException", "Client.UnauthorizedOperation", "UnauthorizedOperation"}


def rule_enumeration_burst(events: list[dict], threshold: int = 10, window_minutes: int = 5) -> list[Finding]:
    """Fenêtre glissante : >= threshold refus pour un même principal en window_minutes."""
    out = []
    per_actor: dict[str, list[datetime]] = defaultdict(list)
    for e in events:
        if e.get("errorCode") in DENIED_CODES:
            per_actor[actor_of(e)].append(parse_time(e["eventTime"]))
    win = timedelta(minutes=window_minutes)
    for actor, times in per_actor.items():
        start = 0
        for end in range(len(times)):
            while times[end] - times[start] > win:
                start += 1
            if end - start + 1 >= threshold:
                out.append(Finding(
                    "enumeration_burst", "MEDIUM", "TA0007 Discovery",
                    times[start].isoformat(), actor,
                    f"{end - start + 1} refus en moins de {window_minutes} min",
                ))
                break  # un finding par principal suffit
    return out


def _is_aws_service_ip(ip: str) -> bool:
    return not ip or ip.endswith(".amazonaws.com") or ip == "AWS Internal"


def rule_key_multi_ip(events: list[dict]) -> list[Finding]:
    """Une clé (surtout temporaire ASIA…) vue depuis plusieurs IP : vol probable."""
    ips: dict[str, set[str]] = defaultdict(set)
    first: dict[str, dict] = {}
    for e in events:
        key = (e.get("userIdentity") or {}).get("accessKeyId")
        ip = e.get("sourceIPAddress", "")
        if not key or _is_aws_service_ip(ip):
            continue
        ips[key].add(ip)
        first.setdefault(key, e)
    out = []
    for key, seen in ips.items():
        if len(seen) > 1:
            temp = key.startswith("ASIA")
            out.append(Finding(
                "key_multi_ip", "HIGH" if temp else "MEDIUM", "TA0006 Credential Access",
                first[key]["eventTime"], actor_of(first[key]),
                f"clé {'temporaire ' if temp else ''}{key[:8]}… utilisée depuis {len(seen)} IP : {', '.join(sorted(seen))}",
            ))
    return out


RULES: list[Callable[[list[dict]], list[Finding]]] = [
    rule_policy_version_tampering,
    rule_admin_policy_attached,
    rule_passrole_compute,
    rule_access_key_for_other_user,
    rule_defense_evasion,
    rule_console_login_no_mfa,
    rule_enumeration_burst,
    rule_key_multi_ip,
]


def hunt(events: list[dict], burst_threshold: int = 10) -> list[Finding]:
    findings: list[Finding] = []
    for rule in RULES:
        if rule is rule_enumeration_burst:
            findings += rule(events, threshold=burst_threshold)
        else:
            findings += rule(events)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.time))
    return findings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path)
    ap.add_argument("--since", help="ignorer les événements antérieurs (ISO 8601)")
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    ap.add_argument("--burst", type=int, default=10, help="seuil de la règle enumeration_burst")
    args = ap.parse_args(argv)

    since = parse_time(args.since) if args.since else None
    if since and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    events = load_events(args.path, since)
    findings = hunt(events, burst_threshold=args.burst)

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        print(f"{len(events)} événements analysés, {len(findings)} findings\n")
        for f in findings:
            print(f"[{f.severity:8}] {f.time}  {f.rule}  ({f.mitre})")
            print(f"           acteur : {f.actor}")
            print(f"           {f.summary}\n")
    return 1 if any(f.severity in ("CRITICAL", "HIGH") for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
