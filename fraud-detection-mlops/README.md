# Fraud detection MLOps (OpenShift GitOps)

End-to-end **credit-card fraud detection** app that integrates with **existing** operators:

| Platform | Role | This repo installs it? |
|---|---|---|
| Kubeflow (KFP) | Training pipeline | **No** |
| MLflow | Experiment tracking / model registry | **No** |
| Feast | Feature store (S3 or SQL sources) | **No** |
| Argo CD / OpenShift GitOps | Deploys this Helm chart | **No** |

```mermaid
flowchart LR
  S3["S3 / MinIO / ODF"] --> Feast
  DB["PostgreSQL"] --> Feast
  Feast -->|historical features| KFP["Kubeflow Pipeline"]
  KFP -->|train / eval| MLflow
  MLflow -->|Staging model| Infer["Inference API"]
  Feast -->|online features| Infer
  ArgoCD["Argo CD"] -->|Helm sync| App["fraud-mlops namespace"]
```

## Directory tree

```text
fraud-detection-mlops/
  docs/DATA_SCHEMA.md          # S3 + SQL contracts
  samples/transactions.csv     # local smoke only
  feast/feature_repo/          # entities, views, dual datasources
  training/                    # XGBoost train/eval + MLflow helpers
  pipelines/                   # KFP v2 pipeline + components
  inference/                   # FastAPI scorer (Feast online + MLflow)
  charts/fraud-detection-mlops # Helm chart for Argo CD
  argocd/application-*.yaml
  scripts/local_smoke.sh
  Dockerfile
```

## Data sources (production)

Set **exactly one**:

```yaml
dataSource:
  type: s3   # or sql
```

- **S3**: Parquet under `s3://<bucket>/<prefix>/` — see `docs/DATA_SCHEMA.md`
- **SQL**: PostgreSQL table `fraud.transactions` — see schema in the same doc

Pipelines use Feast historical retrieval / materialization. They do **not** bake production data into the image.

### Secrets (do not commit credentials)

```bash
# S3 / S3-compatible
oc -n fraud-mlops create secret generic feast-s3-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=... \
  --from-literal=AWS_SECRET_ACCESS_KEY=... \
  --from-literal=AWS_ENDPOINT_URL=https://s3.example.com

# PostgreSQL
oc -n fraud-mlops create secret generic feast-jdbc-credentials \
  --from-literal=JDBC_URL='postgresql+psycopg2://user:pass@host:5432/fraud' \
  --from-literal=PGHOST=... --from-literal=PGPORT=5432 \
  --from-literal=PGDATABASE=fraud --from-literal=PGUSER=... \
  --from-literal=PGPASSWORD=...
```

## Values to point at existing operators

| Value | Example | Points to |
|---|---|---|
| `mlflow.trackingUri` | `http://mlflow.mlflow.svc.cluster.local:5000` | MLflow operator Service |
| `kubeflow.pipelineApi` | `http://ml-pipeline.kubeflow.svc.cluster.local:8888` | KFP API |
| `kubeflow.namespace` | `kubeflow` | Kubeflow namespace |
| `feast.redisConnectionString` | `feast-redis.feast:6379` | Feast online store |
| `dataSource.s3.*` / `dataSource.sql.*` | see examples | Existing raw data |

Examples:

- `charts/fraud-detection-mlops/examples/values-s3.yaml`
- `charts/fraud-detection-mlops/examples/values-sql.yaml`

## Helm + Argo CD

```bash
# Render (acceptance check)
helm template fraud ./charts/fraud-detection-mlops \
  -f charts/fraud-detection-mlops/examples/values-s3.yaml >/dev/null

helm template fraud ./charts/fraud-detection-mlops \
  -f charts/fraud-detection-mlops/examples/values-sql.yaml >/dev/null
```

1. Edit `argocd/application-fraud-detection.yaml` → set `repoURL` to this Git repo.
2. Pick `values-s3.yaml` or `values-sql.yaml` in `helm.valueFiles`.
3. Apply: `oc apply -f argocd/application-fraud-detection.yaml`
4. Sync the Application in OpenShift GitOps.

Destination namespace: **`fraud-mlops`**.

## Build & push pipeline/inference image

```bash
oc -n fraud-mlops new-build --binary --name=fraud-pipeline -l app=fraud-pipeline || true
oc -n fraud-mlops start-build fraud-pipeline --from-dir=. --follow
# Or: podman build -t <registry>/fraud-mlops/fraud-pipeline:latest .
```

Update `image.repository` / `image.tag` in values.

## Compile / upload Kubeflow pipeline

```bash
pip install -r requirements.txt
export PYTHONPATH=$PWD
./scripts/compile_pipeline.sh
# Upload pipelines/fraud_detection_pipeline.yaml via KFP UI or:
# kfp pipeline create -p fraud-detection -f pipelines/fraud_detection_pipeline.yaml
```

Pipeline steps: `validate_sources` → `feast_apply` → optional `materialize` → `build_training_dataset` → `train_eval_register` (MLflow experiment `fraud-detection`, model `fraud-detection-model`).

Default model: **sklearn `HistGradientBoostingClassifier`** with balanced sample weights (portable on OpenShift; no OpenMP/XGBoost dependency).

## Inference

FastAPI service: entity ids → Feast online features → XGBoost probability.

```bash
curl -s https://<route>/score -H 'Content-Type: application/json' \
  -d @inference/sample_request.json
```

## Local smoke (no cluster)

```bash
./scripts/local_smoke.sh
```

Uses `samples/` only + local MLflow file store.

## OpenShift notes

- Containers run non-root (`runAsNonRoot`, drop ALL caps) for restricted SCC.
- Prefer Services; Route is optional for inference.
- Image pull: use internal registry or `image.pullSecrets`.
- Platform operators (KF / MLflow / Feast / Argo CD) must already be healthy.
