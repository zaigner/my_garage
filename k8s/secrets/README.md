# Secrets — Never Commit Real Values

Secrets are created manually on the cluster and are never stored in git.

## Create the Secret

SSH to `aignerpi-2` (192.168.50.124) and run:

```bash
kubectl create secret generic my-garage-secrets \
  --namespace=my-garage \
  --from-literal=DJANGO_SECRET_KEY='<your-secret-key>' \
  --from-literal=DB_PASSWORD='<postgres-password>' \
  --from-literal=GOOGLE_API_KEY='<your-google-api-key>' \
  --from-literal=MARKETCHECK_API_KEY='<your-marketcheck-key>'
```

Generate a Django secret key if you don't have one:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Verify

```bash
kubectl get secret my-garage-secrets -n my-garage
kubectl describe secret my-garage-secrets -n my-garage
```

## Upgrade Path: Sealed Secrets

Once the manual setup is working, install the Sealed Secrets operator to encrypt
secrets and commit them safely to git:

```bash
# Install operator
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml

# Install kubeseal CLI
# https://github.com/bitnami-labs/sealed-secrets#installation

# Seal the secret
kubeseal --format yaml < my-secret.yaml > sealed-secret.yaml
# sealed-secret.yaml is safe to commit
```
