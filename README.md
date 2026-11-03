# Projets Cloud & Sécurité — portfolio d'Ilyas

Quatre projets qui couvrent ce qu'un recruteur « Cloud Security / Cloud Architect » veut voir :
construire une infra propre, l'attaquer, la défendre, et automatiser.

| # | Dossier | Ce que tu prouves | Durée | Coût |
|---|---------|-------------------|-------|------|
| 1 | `01-aws-secure-baseline/` | Concevoir une infra AWS sécurisée en Infrastructure as Code | 3–4 jours | ~1–2 €/mois (détruire après) |
| 2 | `02-cloud-attack-defense-lab/` | Exploiter des mauvaises configs AWS puis les détecter et corriger | 3–4 jours | quelques centimes si tu détruis |
| 3 | `03-k8s-hardening/` | Sécuriser des conteneurs et un cluster Kubernetes | 2–3 jours | 0 € (local) |
| 4 | `04-internship-radar/` | Automatiser un pipeline de données utile (ta recherche de stage) | 1–2 jours | 0 € |

## Ordre conseillé

1. **Projet 4 d'abord (1 soirée)** : il tourne en local, il te sert tout de suite, et c'est un premier repo GitHub propre.
2. **Projet 1** : c'est le cœur de ton profil. Tout le reste s'appuie dessus.
3. **Projet 2** : la partie offensive, qui fait le lien avec tes CTF.
4. **Projet 3** : Kubernetes, demandé dans presque toutes les offres cloud.

En parallèle : la préparation **AWS Solutions Architect Associate (SAA-C03)**. Les projets 1 et 2 couvrent déjà une
bonne partie du programme (VPC, IAM, KMS, S3, CloudTrail).

## Avant de commencer (une seule fois)

1. **Compte AWS** à toi, avec MFA sur le compte root. Ne te sers plus jamais de root ensuite.
2. Crée un utilisateur via **IAM Identity Center** (ou un utilisateur IAM admin avec MFA) et configure `aws configure sso`
   (ou `aws configure`).
3. Installe : `terraform` (≥ 1.6), `aws` CLI v2, `python3` (≥ 3.10), `docker`, `kind`, `kubectl`, `git`.
4. **Alerte de budget** : le projet 1 en crée une, mais fais-en une à la main dès le premier jour dans
   *Billing → Budgets* (5 $).
5. Règle d'or : **`terraform destroy` à la fin de chaque session de travail.**

## Mettre chaque projet sur GitHub

Un repo par projet (c'est plus lisible pour un recruteur qu'un gros repo) :

```bash
cd 01-aws-secure-baseline
git init && git add . && git commit -m "Initial commit"
gh repo create aws-secure-baseline --public --source=. --push
```

Ajoute dans chaque README : un schéma d'architecture, des captures (findings GuardDuty, résultats Checkov…)
et une section « Ce que j'ai appris ». Un repo avec des captures de résultats réels vaut dix fois un repo de code nu.

## Sur le CV — seulement quand c'est fait

Chaque dossier contient une ligne de CV prête à l'emploi. Tu ne l'ajoutes que quand le projet tourne
et que tu sais l'expliquer sans tes notes. Test simple : peux-tu répondre à
« pourquoi tu as fait ce choix ? » pour chaque fichier ?
