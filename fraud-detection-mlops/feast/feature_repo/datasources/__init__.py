"""Data source selection: local samples (smoke) or S3 / SQL (production)."""

from .factory import build_transaction_source

__all__ = ["build_transaction_source"]
