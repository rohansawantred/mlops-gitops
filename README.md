# mlops-gitops

GitOps repository for MLOps workloads on OpenShift.

## Applications

| Path | Description |
|---|---|
| [`fraud-detection-mlops/`](./fraud-detection-mlops/) | Fraud detection: Kubeflow + MLflow + Feast (S3/SQL) + Helm/Argo CD |

Platform operators (**Kubeflow, MLflow, Feast, Argo CD**) are assumed already installed. This repo only ships application GitOps.

See [`fraud-detection-mlops/README.md`](./fraud-detection-mlops/README.md) for architecture, values, and smoke tests.
