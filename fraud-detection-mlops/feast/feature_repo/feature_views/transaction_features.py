from datetime import timedelta

from feast import FeatureView, Field
from feast.types import Float64, Int64, String

from datasources.factory import build_transaction_source
from entities import DEFAULT_TTL, customer, transaction

_source = build_transaction_source()

transaction_features = FeatureView(
    name="transaction_features",
    entities=[transaction, customer],
    ttl=DEFAULT_TTL,
    schema=[
        Field(name="amount", dtype=Float64),
        Field(name="merchant_category", dtype=String),
        Field(name="channel", dtype=String),
        Field(name="country", dtype=String),
    ],
    source=_source,
    online=True,
    description="Per-transaction raw risk signals from S3 or SQL via Feast",
)

# Label view for training only (same source; is_fraud may be null in online path)
transaction_labels = FeatureView(
    name="transaction_labels",
    entities=[transaction],
    ttl=timedelta(days=365),
    schema=[
        Field(name="is_fraud", dtype=Int64),
    ],
    source=_source,
    online=False,
    description="Fraud labels for historical training sets",
)
