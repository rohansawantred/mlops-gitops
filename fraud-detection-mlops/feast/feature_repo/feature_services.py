from feast import FeatureService

from feature_views.transaction_features import transaction_features

fraud_scoring_v1 = FeatureService(
    name="fraud_scoring_v1",
    features=[transaction_features],
    description="Online features for fraud scoring inference",
)
