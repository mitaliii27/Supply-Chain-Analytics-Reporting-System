# etl/load.py – Load layer: writes transformed data to SQLite + CSV exports
"""
Supports two sinks:
  1. SQLite database  (supply_chain.db)  – queryable via SQL scripts
  2. CSV exports      (data/exports/)    – for Power BI / Tableau
"""

from __future__ import annotations

import os
import pandas as pd
from sqlalchemy import create_engine, text
from etl.config import DB_DSN, PROCESSED_DIR, EXPORTS_DIR
from etl.logger import get_logger

log = get_logger(__name__)


def get_engine():
    return create_engine(DB_DSN, echo=False)


def load_to_db(transformed: dict[str, pd.DataFrame]) -> None:
    """Write all fact/dim tables to the database (replace strategy for idempotency)."""
    log.info("Loading to database …")
    engine = get_engine()
    tables = {k: v for k, v in transformed.items() if not k.startswith("_")}

    with engine.begin() as conn:
        for name, df in tables.items():
            df_copy = df.copy()
            # Convert datetime columns to ISO strings for SQLite compatibility
            for col in df_copy.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
                df_copy[col] = df_copy[col].astype(str)

            df_copy.to_sql(name, conn, if_exists="replace", index=False)
            log.info(f"  ✓ {name:<25} → {len(df_copy):,} rows")

    log.info("Database load complete")


def export_to_csv(transformed: dict[str, pd.DataFrame]) -> None:
    """Export KPI tables to CSV for use in Power BI / Tableau."""
    log.info("Exporting KPI CSVs …")
    kpi_tables = ["supplier_kpis", "inventory_kpis", "delivery_kpis",
                  "suppliers", "products", "orders"]
    for name in kpi_tables:
        if name in transformed:
            path = os.path.join(EXPORTS_DIR, f"{name}.csv")
            transformed[name].to_csv(path, index=False)
            log.info(f"  ✓ {path}")


def export_to_processed(transformed: dict[str, pd.DataFrame]) -> None:
    """Save processed DataFrames as Parquet (fast re-read for downstream tasks)."""
    log.info("Saving processed Parquet files …")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    for name, df in transformed.items():
        if name.startswith("_"):
            continue
        path = os.path.join(PROCESSED_DIR, f"{name}.parquet")
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include=["datetime64[ns]"]).columns:
            df_copy[col] = df_copy[col].astype("datetime64[us]")
        df_copy.to_parquet(path, index=False)
    log.info("Parquet export complete")


def load_all(transformed: dict[str, pd.DataFrame]) -> None:
    log.info("=" * 60)
    log.info("LOAD phase starting")
    load_to_db(transformed)
    export_to_csv(transformed)
    export_to_processed(transformed)
    log.info("LOAD phase complete")


def query_db(sql: str) -> pd.DataFrame:
    """Convenience helper to run a SQL query and return a DataFrame."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)
