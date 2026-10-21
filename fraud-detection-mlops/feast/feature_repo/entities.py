from datetime import timedelta

from feast import Entity, ValueType

transaction = Entity(
    name="transaction",
    join_keys=["transaction_id"],
    value_type=ValueType.STRING,
    description="Individual payment transaction",
)

customer = Entity(
    name="customer",
    join_keys=["customer_id"],
    value_type=ValueType.STRING,
    description="Cardholder / customer account",
)

# Convenience: default TTL used by feature views
DEFAULT_TTL = timedelta(days=7)
