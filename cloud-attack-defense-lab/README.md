# Projet 2 — Lab attaque / défense cloud (CloudGoat + détection maison)

## Ce que fait le projet

Tu joues **les deux rôles**, dans **ton propre compte AWS** :

1. **Red team** — tu déploies des scénarios volontairement vulnérables avec **CloudGoat** (outil open source
   de Rhino Security Labs) et tu les exploites, comme un CTF mais sur du vrai AWS.
2. **Blue team** — tu analyses les logs CloudTrail générés par **ta propre attaque** et tu écris un détecteur
   (`detect/cloudtrail_hunter.py`) qui l'aurait repérée.
3. **Remédiation** — tu écris la correction (politique IAM, config) et tu prouves que l'attaque ne marche plus.
4. **Rapport** — un rapport de pentest par scénario (`report/TEMPLATE.md`), comme en mission réelle.

C'est exactement le pont entre ton profil CTF et un poste cloud security : peu d'étudiants savent faire les trois.

## Ce que tu dois comprendre

- **Le modèle IAM d'AWS en profondeur** : utilisateurs, rôles, policies attachées vs inline, versions de policies,
  `iam:PassRole`, trust policies. 80 % des compromissions AWS passent par IAM, pas par le réseau.
- **Les chemins d'escalade de privilèges IAM** : une permission en apparence anodine
  (`iam:SetDefaultPolicyVersion`, `iam:PassRole` + `lambda:CreateFunction`) peut mener à admin.
  Référence : la liste des méthodes de privesc IAM publiée par Rhino Security Labs.
- **CloudTrail comme source de vérité** : structure d'un événement (`eventName`, `userIdentity`,
  `sourceIPAddress`, `errorCode`, `requestParameters`). Différence événements de *gestion* / *données*.
- **Credentials temporaires** : clés `AKIA…` (longue durée) vs `ASIA…` (STS, temporaires) et pourquoi
  le vol de clés de rôle EC2 via SSRF / métadonnées (IMDSv1 vs IMDSv2) est un classique.

## Comment le faire

### Prérequis
- Avoir fait le **projet 1** (le CloudTrail qu'il crée enregistre tes attaques).
- Un **utilisateur IAM admin dédié** pour CloudGoat (jamais root).
- Installer CloudGoat en suivant le README de son dépôt GitHub (`RhinoSecurityLabs/cloudgoat`) ; en résumé :
  ```bash
  git clone https://github.com/RhinoSecurityLabs/cloudgoat.git && cd cloudgoat
  pip3 install -r ./requirements.txt
  ./cloudgoat.py config profile          # profil AWS CLI à utiliser
  ./cloudgoat.py config whitelist --auto # n'expose les ressources qu'à TON IP
  ```
  La commande exacte peut avoir changé : suis toujours la doc à jour du dépôt.

### Pour chaque scénario (voir `SCENARIOS.md` pour l'ordre et les objectifs)
```bash
./cloudgoat.py create <scenario>
# ... tu attaques (en notant chaque commande dans ton rapport) ...
# attendre ~15 min que CloudTrail livre les logs, puis :
aws s3 sync s3://<bucket-logs>/cloudtrail/ ./logs/<scenario>/
python3 detect/cloudtrail_hunter.py ./logs/<scenario>/ --since 2026-11-10T00:00:00Z
./cloudgoat.py destroy <scenario>       # TOUJOURS, le jour même
```

### Le détecteur (`detect/`)
`cloudtrail_hunter.py` lit des fichiers CloudTrail (`.json` ou `.json.gz`) et applique des règles :

| Règle | Ce qu'elle repère | Tactique MITRE ATT&CK |
|-------|-------------------|-----------------------|
| `policy_version_tampering` | `CreatePolicyVersion` / `SetDefaultPolicyVersion` | Privilege Escalation |
| `admin_policy_attached` | Attachement de `AdministratorAccess` ou policy inline `*:*` | Privilege Escalation |
| `passrole_compute` | `PassRole` puis création de Lambda/EC2 par le même principal | Privilege Escalation |
| `access_key_for_other_user` | Un principal crée une clé d'accès pour quelqu'un d'autre | Persistence |
| `defense_evasion` | `StopLogging`, `DeleteTrail`, `DeleteDetector`… | Defense Evasion |
| `console_login_no_mfa` | Connexion console réussie sans MFA | Initial Access |
| `enumeration_burst` | ≥ N erreurs `AccessDenied` en quelques minutes | Discovery |
| `key_multi_ip` | Même clé d'accès utilisée depuis plusieurs IP | Credential Access |

Les tests (`python3 -m unittest discover -s detect/tests`) passent sur des logs synthétiques.
**Ton travail** : après chaque scénario, vérifier si une règle a sonné. Si non, écrire la règle manquante
et un test. C'est ça, le livrable intéressant.

### Requêtes Athena (`athena/queries.sql`)
Pour interroger des mois de logs en SQL directement dans S3. Plus réaliste en entreprise que le script Python ;
les deux sont complémentaires.

## Règles du jeu (important)
- Uniquement **ton** compte AWS et les ressources créées par CloudGoat.
- `whitelist` sur ton IP, et `destroy` le jour même : certains scénarios exposent volontairement des services.
- Jamais de clés d'accès dans Git (`git-secrets` ou `gitleaks` en pre-commit).

## Ligne de CV (une fois terminé)
> **Cloud Attack & Detection Lab (AWS)** — Exploited IAM privilege-escalation and data-exposure scenarios
> (CloudGoat) in an isolated account, then built a Python CloudTrail detection engine mapped to MITRE ATT&CK
> and wrote remediations and pentest reports for each scenario.
