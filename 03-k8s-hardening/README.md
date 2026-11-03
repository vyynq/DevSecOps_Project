# Projet 3 — Durcissement Kubernetes (local, 0 €)

## Ce que fait le projet

Tu déploies la **même application deux fois** dans un cluster Kubernetes local (`kind`) :

- `manifests/insecure/` : la version « telle qu'on la trouve souvent en vrai » — conteneur root, privilégié,
  image `latest`, token de service account monté, aucun filtrage réseau.
- `manifests/secure/` : la version durcie — non-root, système de fichiers en lecture seule, capacités Linux
  retirées, seccomp, limites de ressources, NetworkPolicy *default deny*, RBAC minimal.

Puis tu **prouves** la différence avec des outils, sans avoir à reproduire une attaque toi-même :
1. **Garde-fou à l'admission** : un *policy engine* (**Kyverno**) refuse d'admettre dans le cluster tout pod
   qui a les défauts de la version non sécurisée. Tu le vois refuser le mauvais manifest et accepter le bon.
2. **Scan** : **Trivy** analyse les manifests et les images et liste les écarts entre les deux versions.
3. **Vérification du confinement** : une checklist (`CHECKS.md`) de commandes `kubectl`/`kubectl auth can-i`
   qui montrent, côté pod sécurisé, que l'utilisateur est non-root, que le token d'API n'est pas monté,
   et que la NetworkPolicy bloque le trafic non autorisé.

> Sur la partie offensive (comprendre *pourquoi* un pod privilégié est dangereux), on reste au niveau des
> mécanismes dans ce dossier. Si tu veux pratiquer l'exploitation guidée, fais-le dans un environnement
> prévu pour ça — par exemple les scénarios « container escape » de **kind** documentés par le projet, ou
> les labs **Kubernetes Goat** — et range tes notes dans le projet 2.

## Ce que tu dois comprendre

| Notion | Pourquoi c'est important |
|--------|--------------------------|
| Un conteneur n'est **pas** une VM : namespaces + cgroups + capabilities sur le **même noyau** | C'est pour ça qu'un pod `privileged` donne un accès de niveau hôte |
| `securityContext` : `runAsNonRoot`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem`, `seccompProfile` | Les quelques réglages qui coupent l'immense majorité des évasions |
| **Pod Security Standards** (privileged / baseline / restricted) et le label `pod-security.kubernetes.io/enforce` | Le mécanisme intégré à Kubernetes depuis la 1.25 |
| **NetworkPolicy** : par défaut, *tout pod parle à tout pod* | Sans *default deny*, un pod compromis atteint toute la base de données du cluster |
| **RBAC** : Role/RoleBinding, ServiceAccount, `automountServiceAccountToken` | Un token volé dans un pod peut donner accès à l'API du cluster |
| **Admission control** (Kyverno / OPA Gatekeeper) | « Shift left » côté cluster : refuser au lieu de corriger après coup |

Ressources : la doc officielle Kubernetes (*Pod Security Standards*, *Network Policies*) ;
le guide de durcissement Kubernetes de la NSA/CISA ; le benchmark CIS Kubernetes.

## Comment le faire

### Installation (1 h)
```bash
# Docker, kind, kubectl, helm et trivy installés au préalable
kind create cluster --name lab --config kind-config.yaml
# Le CNI par défaut est désactivé : on installe Calico, qui applique les NetworkPolicies
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml
kubectl -n kube-system rollout status ds/calico-node --timeout=180s
```
(Vérifie la dernière version de Calico dans sa doc et adapte l'URL.)

### Étape 1 — Observer la version non sécurisée
```bash
kubectl apply -f manifests/insecure/
```
Dans `NOTES.md`, pour chaque réglage dangereux du manifest (`privileged: true`, `hostPath`, root…),
écris **une phrase** expliquant ce qu'il permettrait à un attaquant. Tu n'as pas besoin de réaliser l'évasion :
l'important est de savoir l'expliquer en entretien. `CHECKS.md` te donne des commandes `kubectl` sûres
(lecture seule) qui rendent le risque visible.

### Étape 2 — Déployer la version durcie
```bash
kubectl apply -f manifests/secure/
```
Puis déroule `CHECKS.md` côté `secure` : utilisateur non-root, pas de token monté, écriture refusée sur le
système de fichiers racine, trafic non autorisé bloqué par la NetworkPolicy. Capture chaque résultat.

### Étape 3 — Le garde-fou Kyverno
```bash
helm repo add kyverno https://kyverno.github.io/kyverno/ && helm repo update
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
kubectl apply -f policies/           # policies Kyverno (require-non-root, disallow-privileged...)
kubectl apply -f manifests/insecure/ # doit être REFUSÉ à l'admission -> lis le message
kubectl apply -f manifests/secure/   # doit être ACCEPTÉ
```
C'est le moment « waouh » du projet : le cluster refuse lui-même les mauvaises configs.

### Étape 4 — Scan Trivy
```bash
trivy config manifests/insecure/    # liste les mauvaises configs
trivy config manifests/secure/      # bien plus propre : compare les deux
trivy k8s --report summary cluster  # vue d'ensemble du cluster
```

### Nettoyage
```bash
kind delete cluster --name lab
```

## Ligne de CV (une fois terminé)
> **Kubernetes Hardening Lab** — Built insecure vs. hardened deployments of the same app on kind; enforced
> Pod Security (non-root, dropped capabilities, read-only FS, seccomp), default-deny NetworkPolicies and least-
> privilege RBAC; blocked non-compliant workloads at admission with Kyverno and scanned manifests/images with Trivy.
