# Projet 1 — AWS Secure Baseline en Terraform

## Ce que fait le projet

Il déploie, en une commande, le **socle de sécurité** d'un compte AWS, ce qu'on appelle une *landing zone* minimale :

```
                    ┌──────────────────── VPC 10.0.0.0/16 (2 zones) ───────────────────┐
 Internet ── IGW ── │ Subnets publics (pas d'IP publique auto)                          │
                    │ Subnets privés (aucune route vers Internet)                       │
                    │ Security group par défaut : vidé (deny all)                       │
                    │ VPC Flow Logs ───────────────┐                                    │
                    └──────────────────────────────┼────────────────────────────────────┘
                                                   ▼
 CloudTrail (toutes régions) ──────────► Bucket S3 de logs (chiffré KMS, versionné,
                                          public bloqué, HTTPS obligatoire)
 GuardDuty ─► EventBridge (sévérité ≥ 7) ─► SNS (chiffré KMS) ─► ton email
 IAM : politique de mots de passe, rôle "auditor" (lecture seule, MFA obligatoire), Access Analyzer
 Budget : alerte email à 80 % de 5 $
 CI GitHub : terraform fmt/validate + scan Checkov à chaque push
```

## Ce que tu dois comprendre (et savoir expliquer en entretien)

| Fichier | Notion clé | La question qu'on te posera |
|---------|------------|-----------------------------|
| `vpc.tf` | Segmentation réseau, subnets publics/privés, route tables | « Comment une instance privée sort-elle sur Internet ? » (NAT Gateway ou VPC endpoints — ici volontairement aucun, pour le coût et la sécurité) |
| `vpc.tf` | Default security group vidé | « Pourquoi ? » Parce que toute ressource créée sans SG explicite tomberait dedans |
| `logging.tf` | **KMS** : clé gérée par toi, rotation, *key policy* | « Différence entre key policy et IAM policy ? » |
| `logging.tf` | Bucket policy : principe du moindre privilège pour un **service** (CloudTrail), condition `aws:SourceArn` | « Qu'est-ce que le *confused deputy problem* ? » |
| `logging.tf` | CloudTrail multi-région + *log file validation* | « Comment prouver qu'un attaquant n'a pas effacé ses traces ? » |
| `iam.tf` | Rôle assumable seulement avec MFA (`aws:MultiFactorAuthPresent`) | « Rôle vs utilisateur IAM : pourquoi préférer les rôles ? » |
| `detection.tf` | Détection managée, EventBridge, SNS | « Comment être alerté d'une compromission en moins de 15 min ? » |
| `.github/workflows/` | *Shift-left security* : scanner l'IaC avant le déploiement | « Qu'est-ce que Checkov a trouvé, qu'as-tu corrigé, qu'as-tu accepté et pourquoi ? » |

À lire avant de coder (1 soirée) :
- AWS Well-Architected, pilier **Security** (les 7 principes de design).
- La doc AWS « Security best practices in IAM ».
- Le tutoriel officiel Terraform « Get Started – AWS ».

## Comment le faire, étape par étape

### Jour 1 — Prise en main
```bash
cd 01-aws-secure-baseline
cp terraform.tfvars.example terraform.tfvars   # mets ton email
terraform init
terraform fmt -check && terraform validate
terraform plan        # LIS le plan en entier : chaque ressource doit avoir une raison d'être
```
Exercice : pour chaque ressource du plan, écris en une phrase dans `NOTES.md` à quoi elle sert.

### Jour 2 — Déploiement et vérification
```bash
terraform apply
```
Puis vérifie à la main que la sécurité marche vraiment (c'est ça qui fait la différence) :
- Essaie de lire le bucket sans HTTPS ou de le rendre public → refusé ?
- `aws cloudtrail get-trail-status --name <trail>` → `IsLogging: true` ?
- `aws cloudtrail validate-logs ...` → intégrité OK ?
- Assume le rôle `auditor` **sans** MFA → refusé ? Puis avec MFA → OK ?
- GuardDuty → *Generate sample findings* dans la console → tu reçois l'email (après avoir confirmé l'abonnement SNS) ?

Fais des captures d'écran de chaque test : elles iront dans le README GitHub.

### Jour 3 — CI et scan
1. Pousse sur GitHub. La CI (`.github/workflows/security.yml`) lance Checkov.
2. Lis chaque finding. Pour chacun : **corriger** ou **accepter avec justification** dans `.checkov.yaml`.
   J'en ai déjà justifié 10 (testé avec Checkov 3.4 : 80 contrôles OK, 0 échec).
   **Exercice clé** : commente le bloc `skip-check`, relance, et pour chaque échec, retrouve toi-même
   pourquoi il est accepté. Il y a un vrai faux positif dedans (la key policy KMS) : comprends pourquoi.
3. Lance aussi en local : `pip install checkov && checkov --config-file .checkov.yaml`

### Jour 4 — Aller plus loin (choisis-en au moins un)
- Découper en **modules** (`modules/network`, `modules/logging`) : c'est ce qu'on fait en entreprise.
- **Backend distant** : state dans S3 avec verrouillage (`use_lockfile = true`, Terraform ≥ 1.10).
- **AWS Config** + 3 règles managées (bucket public, MFA root, CloudTrail actif).
- Une petite instance EC2 dans un subnet privé, accessible par **SSM Session Manager** sans SSH ni IP publique
  (il faudra des VPC endpoints : calcule leur coût avant).

### À la fin de chaque session
```bash
terraform destroy
```
Le bucket de logs a `force_destroy = true` pour que ce soit possible. En production, on ne ferait jamais ça :
sache l'expliquer.

## Coûts
- CloudTrail (1er trail, événements de gestion) : gratuit. S3 : quelques centimes.
- KMS : ~1 $/mois par clé (au prorata).
- GuardDuty : 30 jours d'essai gratuit, puis payant au volume (faible sur un compte vide).
  `enable_guardduty = false` pour le couper.
- **Aucune NAT Gateway** (≈ 35 $/mois) : volontaire.

## Ligne de CV (une fois terminé et compris)
> **AWS Secure Baseline (Terraform)** — Designed and deployed a security baseline for an AWS account as code:
> segmented multi-AZ VPC with flow logs, KMS-encrypted multi-region CloudTrail with integrity validation,
> GuardDuty alerting via EventBridge/SNS, MFA-enforced least-privilege IAM roles; CI pipeline with Checkov IaC scanning.
