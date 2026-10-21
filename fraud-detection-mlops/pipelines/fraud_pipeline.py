"""Kubeflow Pipeline for fraud detection (KFP v2).

Steps: validate_sources → feast_apply → (optional materialize) → historical dataset →
train/eval → MLflow register
"""

from __future__ import annotations

from kfp import compiler, dsl

DEFAULT_IMAGE = (
    "image-registry.openshift-image-registry.svc:5000/fraud-mlops/fraud-pipeline:latest"
)


@dsl.component(base_image=DEFAULT_IMAGE)
def validate_sources_op() -> str:
    from pipelines.components.validate_sources import validate_sources

    return validate_sources()


@dsl.component(base_image=DEFAULT_IMAGE)
def feast_apply_op(repo_path: str) -> str:
    from pipelines.components.feast_ops import feast_apply

    return feast_apply(repo_path)


@dsl.component(base_image=DEFAULT_IMAGE)
def feast_materialize_op(repo_path: str, start: str, end: str) -> str:
    from pipelines.components.feast_ops import feast_materialize

    return feast_materialize(repo_path, start=start or None, end=end or None)


@dsl.component(base_image=DEFAULT_IMAGE)
def build_training_dataset_op(repo_path: str, output_path: str) -> str:
    from pipelines.components.feast_ops import build_training_dataset

    return build_training_dataset(repo_path, output_path)


@dsl.component(base_image=DEFAULT_IMAGE)
def train_eval_register_op(
    dataset_path: str,
    tracking_uri: str,
    experiment_name: str,
    model_name: str,
    min_pr_auc: float,
    min_f1: float,
    max_depth: int,
    n_estimators: int,
    learning_rate: float,
) -> str:
    from pipelines.components.train_eval_register import train_eval_register

    result = train_eval_register(
        dataset_path,
        tracking_uri=tracking_uri or None,
        experiment_name=experiment_name,
        model_name=model_name,
        min_pr_auc=min_pr_auc,
        min_f1=min_f1,
        max_depth=max_depth,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )
    return f"{result['run_id']}|promoted={result['promoted_to_staging']}"


@dsl.pipeline(
    name="fraud-detection-pipeline",
    description="Fraud detection: Feast (S3/SQL) → train → MLflow",
)
def fraud_detection_pipeline(
    feast_repo_path: str = "/opt/fraud/feast/feature_repo",
    dataset_output_path: str = "/tmp/train.parquet",
    materialize_start: str = "",
    materialize_end: str = "",
    run_materialize: bool = False,
    mlflow_tracking_uri: str = "",
    experiment_name: str = "fraud-detection",
    model_name: str = "fraud-detection-model",
    min_pr_auc: float = 0.5,
    min_f1: float = 0.3,
    max_depth: int = 4,
    n_estimators: int = 100,
    learning_rate: float = 0.1,
):
    v = validate_sources_op()
    apply = feast_apply_op(repo_path=feast_repo_path)
    apply.after(v)

    with dsl.If(run_materialize == True):  # noqa: E712
        mat = feast_materialize_op(
            repo_path=feast_repo_path,
            start=materialize_start,
            end=materialize_end,
        )
        mat.after(apply)

    ds = build_training_dataset_op(
        repo_path=feast_repo_path,
        output_path=dataset_output_path,
    )
    ds.after(apply)

    train_eval_register_op(
        dataset_path=ds.output,
        tracking_uri=mlflow_tracking_uri,
        experiment_name=experiment_name,
        model_name=model_name,
        min_pr_auc=min_pr_auc,
        min_f1=min_f1,
        max_depth=max_depth,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
    )


def compile_pipeline(output_path: str = "pipelines/fraud_detection_pipeline.yaml") -> str:
    compiler.Compiler().compile(
        pipeline_func=fraud_detection_pipeline,
        package_path=output_path,
    )
    return output_path


if __name__ == "__main__":
    print(f"Compiled pipeline -> {compile_pipeline()}")
