# Projet 4 — Radar à offres de stage

## Ce que fait le projet

Un petit pipeline de données en Python qui :

1. **Collecte** des offres depuis plusieurs sources (flux RSS/JSON publics ; voir `sources.yaml`).
2. **Normalise** chaque offre dans un format commun.
3. **Score** chaque offre par rapport à TON profil (mots-clés cloud/sécurité, localisation Europe,
   durée 6 mois, mention de rémunération, bonus zone germanophone pour ton allemand B1).
4. **Déduplique** (une même offre republiée plusieurs fois ne ressort qu'une fois).
5. **Produit** un tableau de bord HTML trié par score (`output/dashboard.html`) et un `output/offres.csv`.
6. **Garde l'historique** dans une base SQLite, pour ne te montrer que les **nouveautés** à chaque passage.

C'est à la fois utile tout de suite et un vrai projet « data engineering » pour ton GitHub :
sources multiples, modèle de données propre, tests, planification.

## Pourquoi c'est aussi un bon projet technique

- Architecture en modules (collecte / normalisation / scoring / rendu) → tu sais expliquer un pipeline.
- Testé (`python3 -m pytest` ou `unittest`) → tu montres que tu testes ton code.
- Planifiable (cron local, GitHub Actions, ou extension en Lambda + EventBridge) → lien direct avec le cloud.
- **Extension cloud (le vrai bonus CV)** : déployer le collecteur en AWS Lambda déclenché par EventBridge,
  stocker dans DynamoDB, publier le dashboard sur S3. Tu réutilises tout ce que tu auras appris au projet 1.

## Comment le faire

```bash
cd 04-internship-radar
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp profile.example.yaml profile.yaml   # ajuste tes mots-clés et préférences
python3 -m radar.run                     # collecte + score + rapport
open output/dashboard.html               # (xdg-open sous Linux)
```

Sans accès réseau ou pour développer les règles de scoring, un jeu d'offres d'exemple est fourni :
```bash
python3 -m radar.run --fixtures fixtures/sample_jobs.json
```

### Étapes d'apprentissage
1. **Jour 1** : fais tourner la démo sur les fixtures, lis `scoring.py`, ajuste les poids dans `profile.yaml`.
   Lance les tests.
2. **Jour 2** : ajoute une vraie source dans `sources.yaml` (beaucoup de sites d'emploi offrent un flux RSS :
   cherche « <site> rss » ou une page `/feed`). Écris son parseur si le format diffère.
3. **Bonus** : branche une notification (email via le SNS du projet 1, ou un webhook) quand une offre dépasse
   un score seuil. Puis tente le déploiement Lambda.

## Important — rester correct vis-à-vis des sources
- On lit **des flux publics prévus pour être lus par des machines** (RSS/JSON), on respecte leurs conditions.
- Le collecteur HTTP met un `User-Agent` générique, limite sa cadence (un appel par source, pause entre deux)
  et met en cache, pour ne pas marteler les serveurs.
- Pas de scraping agressif de sites qui l'interdisent, pas de contournement de connexion. Si une plateforme
  propose une **API officielle**, c'est toujours la bonne porte d'entrée (certaines demandent une clé gratuite).
- Postuler reste **ta** décision, offre par offre : l'outil trie et prépare, il n'envoie rien tout seul.

## Ligne de CV (une fois en ligne)
> **Internship Radar** — Python data pipeline aggregating job postings from multiple public feeds, with
> profile-based scoring, deduplication, SQLite history and an auto-generated HTML dashboard; unit-tested and
> schedulable (cron / GitHub Actions), with an AWS serverless deployment path (Lambda + EventBridge + S3).
