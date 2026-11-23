# Vérifications (toutes en lecture seule, sans danger)

Lance-les côté `secure` et note le résultat. Compare mentalement avec ce que donnerait la version non sécurisée.

## 1. L'utilisateur n'est pas root
```bash
kubectl -n secure exec deploy/web -- id
# attendu : uid=10001 ... (et non uid=0)
```

## 2. Le système de fichiers racine est en lecture seule
```bash
kubectl -n secure exec deploy/web -- sh -c 'touch /root/x 2>&1 || echo "écriture refusée (attendu)"'
```

## 3. Le token d'API n'est pas monté
```bash
kubectl -n secure exec deploy/web -- sh -c \
  'ls /var/run/secrets/kubernetes.io/serviceaccount 2>&1 || echo "pas de token monté (attendu)"'
```

## 4. Les droits RBAC du service account sont minimaux
```bash
kubectl auth can-i --list --as=system:serviceaccount:secure:web -n secure
kubectl auth can-i delete pods --as=system:serviceaccount:secure:web -n secure   # -> no
```

## 5. La NetworkPolicy bloque le trafic non autorisé
```bash
# Un pod de test SANS le label role=frontend ne doit PAS joindre web :
kubectl -n secure run probe --image=busybox --labels=role=other --restart=Never -it --rm -- \
  sh -c 'wget -T 3 -qO- http://web:8080 || echo "bloqué par la NetworkPolicy (attendu)"'

# Avec le bon label, ça passe :
kubectl -n secure run probe --image=busybox --labels=role=frontend --restart=Never -it --rm -- \
  sh -c 'wget -T 3 -qO- http://web:8080 >/dev/null && echo "autorisé (attendu)"'
```

## 6. Le Pod Security Standard "restricted" est actif
```bash
kubectl get ns secure -o jsonpath='{.metadata.labels}' ; echo
# essaie d'appliquer manifests/insecure/ DANS le namespace secure : refusé par Pod Security
```
