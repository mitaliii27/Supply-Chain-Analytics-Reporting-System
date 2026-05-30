# etl/extract.py – Data acquisition layer
"""
Reads raw CSV files from data/raw/ and returns validated DataFrames.
Extend load_source() to support S3, databases, or APIs.
"""

from __future__ import annotations

import os
import pandas as pd
from etl.config import RAW_DIR
from etl.logger import get_logger

log = get_logger(__name__)

# Map logical name → filename
SOURCE_FILES: dict[str, str] = {
    "suppliers":  "suppliers.csv",
    "products":   "products.csv",
    "inventory":  "inventory.csv",
    "orders":     "orders.csv",
    "warehouses": "warehouses.csv",
}


def load_source(name: str, **read_kwargs) -> pd.DataFrame:
    """Load a single source CSV.  Raises FileNotFoundError with a helpful message."""
    path = os.path.join(RAW_DIR, SOURCE_FILES[name])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Source '{name}' not found at {path}.\n"
            "Run  python data/generate_data.py  first."
        )
    log.info(f"Loading {name} from {path} …")
    df = pd.read_csv(path, **read_kwargs)
    log.info(f"  → {len(df):,} rows, {df.shape[1]} columns")
    return df


def extract_all() -> dict[str, pd.DataFrame]:
    """Extract every source and return as a named dict."""
    log.info("=" * 60)
    log.info("EXTRACT phase starting")
    sources = {}
    for name in SOURCE_FILES:
        sources[name] = load_source(name)
    log.info(f"EXTRACT complete — {len(sources)} sources loaded")
    return sources
