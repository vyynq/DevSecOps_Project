# Rapport — Scénario `<nom>`

**Date** : AAAA-MM-JJ · **Auteur** : Ilyas Bakchiche · **Périmètre** : compte AWS de lab `<id>`, ressources CloudGoat uniquement

## 1. Résumé exécutif (3 lignes, pour un manager)
Point de départ, ce qui a été obtenu, gravité, correctif principal.

## 2. Gravité
| Vulnérabilité | Impact | Probabilité | Gravité |
|---------------|--------|-------------|---------|
| ex. Version de policy IAM permissive réactivable | Admin complet | Élevée | **Critique** |

## 3. Chemin d'attaque
| # | Commande / action | Résultat | Événement CloudTrail |
|---|-------------------|----------|----------------------|
| 1 | `aws sts get-caller-identity` | Identité `raynor` | `GetCallerIdentity` |
| 2 | … | … | … |

Schéma : point de départ → étapes → objectif.

## 4. Détection
- Règles du hunter déclenchées : …
- GuardDuty : …
- Ce qui n'a **pas** été détecté et pourquoi : …
- Nouvelle règle écrite : nom, logique, test associé.

## 5. Remédiation
Policy / config corrigée (bloc de code) + preuve que l'attaque échoue ensuite (sortie `AccessDenied`).

## 6. Ce que j'ai appris
2 à 4 points.
