# Parcours de scénarios CloudGoat

Vérifie les noms exacts avec `./cloudgoat.py list` : la liste évolue selon les versions.
Pour chaque scénario, le dépôt fournit un `README` (objectif) et une `cheat_sheet` (solution).
**Ne lis la solution qu'après au moins 1 h de recherche** : l'intérêt est de développer le réflexe.

## Méthode pour chaque scénario (la même qu'en mission)

1. **Recon** : qui suis-je ? (`aws sts get-caller-identity`) Quelles policies me concernent ?
   (`aws iam list-attached-user-policies`, `list-user-policies`, `get-policy-version`…)
2. **Hypothèse** : quelle permission pourrait m'élever ? Note-la avant d'essayer.
3. **Exploitation** : une commande à la fois, chacune notée dans le rapport.
4. **Détection** : récupère les logs, lance le hunter. Qu'est-ce qui a sonné ? Qu'est-ce qui n'a rien vu ?
5. **Remédiation** : écris le correctif (souvent quelques lignes de policy JSON) et explique pourquoi il suffit.

## Ordre conseillé

### 1. `iam_privesc_by_rollback` — débutant
- **Notion** : une policy IAM peut avoir jusqu'à 5 versions ; une ancienne version peut être plus permissive.
- **À détecter** : `policy_version_tampering`.
- **Remédiation à réfléchir** : qui devrait avoir `iam:SetDefaultPolicyVersion` ? Comment nettoyer les vieilles versions ?

### 2. `lambda_privesc` — débutant/intermédiaire
- **Notion** : `iam:PassRole` permet de « prêter » un rôle puissant à un service que tu contrôles.
- **À détecter** : `passrole_compute`.
- **Remédiation** : condition `iam:PassedToService` et restriction de `Resource` sur PassRole.

### 3. `cloud_breach_s3` — intermédiaire
- **Notion** : SSRF vers le service de métadonnées EC2 (IMDSv1) → vol des credentials du rôle → accès S3.
- **À détecter** : `key_multi_ip` (les clés `ASIA…` du rôle utilisées hors de l'instance).
  Bonus : la détection GuardDuty `InstanceCredentialExfiltration` du projet 1 a-t-elle sonné ?
- **Remédiation** : IMDSv2 obligatoire (`http_tokens = "required"` en Terraform), moindre privilège sur le rôle.

### 4. `vulnerable_lambda` — intermédiaire
- **Notion** : injection dans le code d'une Lambda qui manipule des policies IAM.
- **À détecter** : `admin_policy_attached`.
- **Remédiation** : validation d'entrée + rôle d'exécution Lambda minimal.

Ensuite, choisis 2 scénarios « difficiles » de la liste selon tes envies.
Quatre scénarios bien documentés valent mieux que dix bâclés.
