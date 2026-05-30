# etl/transform.py – Transformation & business-logic layer
"""
Each function is a pure transformation: takes DataFrames, returns DataFrames.
Order matters; call via transform_all() which chains them correctly.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from etl.config import (
    MAX_DEFECT_RATE, MIN_ON_TIME_RATE,
    LOW_STOCK_MULTIPLIER, DELAY_THRESHOLD_DAYS,
)
from etl.logger import get_logger

log = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CLEAN
# ─────────────────────────────────────────────────────────────────────────────

def clean_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Cleaning suppliers …")
    before = len(df)
    df = df.copy()
    df["supplier_id"]   = df["supplier_id"].str.strip().str.upper()
    df["supplier_name"] = df["supplier_name"].str.strip().str.title()
    df["is_active"]     = df["is_active"].astype(bool)
    df = df.drop_duplicates(subset=["supplier_id"])
    df["rating"]       = df["rating"].clip(0, 5)
    df["on_time_rate"] = df["on_time_rate"].clip(0, 1)
    df["defect_rate"]  = df["defect_rate"].clip(0, 1)
    log.info(f"  suppliers: {before:,} → {len(df):,} rows (dropped {before - len(df):,} dupes)")
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Cleaning products …")
    df = df.copy()
    df["product_id"]   = df["product_id"].str.strip().str.upper()
    df["product_name"] = df["product_name"].str.strip()
    df["unit_cost"]    = pd.to_numeric(df["unit_cost"], errors="coerce").fillna(0).clip(lower=0)
    df = df.drop_duplicates(subset=["product_id"])
    return df


def clean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Cleaning inventory …")
    df = df.copy()
    df["product_id"]   = df["product_id"].str.strip().str.upper()
    df["warehouse_id"] = df["warehouse_id"].str.strip().str.upper()
    df["quantity_on_hand"]   = df["quantity_on_hand"].clip(lower=0)
    df["quantity_reserved"]  = df["quantity_reserved"].clip(lower=0)
    df["last_updated"]       = pd.to_datetime(df["last_updated"], errors="coerce")
    return df


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Cleaning orders …")
    df = df.copy()
    for col in ["order_id", "supplier_id", "product_id"]:
        df[col] = df[col].str.strip().str.upper()
    for col in ["order_date", "expected_date", "actual_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["quantity"]    = df["quantity"].clip(lower=0)
    df["unit_price"]  = df["unit_price"].clip(lower=0)
    df["freight_cost"]= df["freight_cost"].clip(lower=0)
    df = df.drop_duplicates(subset=["order_id"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. ENRICH / DERIVE
# ─────────────────────────────────────────────────────────────────────────────

def enrich_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns: order_value, delay_days, is_on_time, is_delayed_critical."""
    log.info("Enriching orders …")
    df = orders.copy()
    df["order_value"]          = df["quantity"] * df["unit_price"]
    df["total_cost"]           = df["order_value"] + df["freight_cost"]
    df["delay_days"]           = (df["actual_date"] - df["expected_date"]).dt.days.clip(lower=0)
    df["is_on_time"]           = df["delay_days"].fillna(0) == 0
    df["is_delayed_critical"]  = df["delay_days"] > DELAY_THRESHOLD_DAYS
    df["order_year"]           = df["order_date"].dt.year
    df["order_month"]          = df["order_date"].dt.month
    df["order_quarter"]        = df["order_date"].dt.quarter
    return df


def enrich_inventory(inventory: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Flag low-stock items by joining with product safety_stock."""
    log.info("Enriching inventory …")
    df = inventory.merge(
        products[["product_id", "safety_stock", "reorder_point", "unit_cost"]],
        on="product_id", how="left"
    )
    df["available_qty"] = (df["quantity_on_hand"] - df["quantity_reserved"]).clip(lower=0)
    df["stock_value"]   = df["available_qty"] * df["unit_cost"].fillna(0)
    df["is_low_stock"]  = df["available_qty"] < (df["safety_stock"] * LOW_STOCK_MULTIPLIER)
    df["is_stockout"]   = df["available_qty"] == 0
    return df


def flag_suppliers(suppliers: pd.DataFrame) -> pd.DataFrame:
    """Apply risk flags to suppliers."""
    log.info("Flagging supplier risk …")
    df = suppliers.copy()
    df["risk_flag"] = "Low"
    df.loc[df["defect_rate"] > MAX_DEFECT_RATE, "risk_flag"] = "High"
    df.loc[df["on_time_rate"] < MIN_ON_TIME_RATE, "risk_flag"] = "Medium"
    df.loc[
        (df["defect_rate"] > MAX_DEFECT_RATE) & (df["on_time_rate"] < MIN_ON_TIME_RATE),
        "risk_flag"
    ] = "Critical"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. AGGREGATE – KPI FACT TABLES
# ─────────────────────────────────────────────────────────────────────────────

def build_supplier_kpis(orders: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
    """Monthly supplier performance KPI table."""
    log.info("Building supplier KPIs …")
    agg = (
        orders.groupby(["supplier_id", "order_year", "order_month"])
        .agg(
            total_orders     = ("order_id", "count"),
            total_value      = ("order_value", "sum"),
            avg_delay_days   = ("delay_days", "mean"),
            on_time_orders   = ("is_on_time", "sum"),
            critical_delays  = ("is_delayed_critical", "sum"),
            total_freight    = ("freight_cost", "sum"),
        )
        .reset_index()
    )
    agg["otif_rate"] = (agg["on_time_orders"] / agg["total_orders"]).round(4)
    agg = agg.merge(
        suppliers[["supplier_id", "supplier_name", "region", "tier", "risk_flag"]],
        on="supplier_id", how="left"
    )
    return agg


def build_inventory_kpis(inventory_enriched: pd.DataFrame) -> pd.DataFrame:
    """Warehouse-level inventory KPI summary."""
    log.info("Building inventory KPIs …")
    kpi = (
        inventory_enriched.groupby("warehouse_id")
        .agg(
            total_skus          = ("product_id", "nunique"),
            total_stock_value   = ("stock_value", "sum"),
            low_stock_items     = ("is_low_stock", "sum"),
            stockout_items      = ("is_stockout", "sum"),
            avg_qty_on_hand     = ("quantity_on_hand", "mean"),
        )
        .reset_index()
    )
    kpi["stockout_pct"] = (kpi["stockout_items"] / kpi["total_skus"]).round(4)
    return kpi


def build_delivery_kpis(orders: pd.DataFrame) -> pd.DataFrame:
    """Monthly delivery performance trends."""
    log.info("Building delivery KPIs …")
    return (
        orders.groupby(["order_year", "order_month"])
        .agg(
            total_orders      = ("order_id", "count"),
            delivered         = ("status", lambda x: (x == "Delivered").sum()),
            delayed           = ("status", lambda x: (x == "Delayed").sum()),
            cancelled         = ("status", lambda x: (x == "Cancelled").sum()),
            avg_delay_days    = ("delay_days", "mean"),
            total_order_value = ("order_value", "sum"),
        )
        .reset_index()
        .assign(
            delivery_rate   = lambda d: (d["delivered"] / d["total_orders"]).round(4),
            cancellation_rate = lambda d: (d["cancelled"] / d["total_orders"]).round(4),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. VALIDATE
# ─────────────────────────────────────────────────────────────────────────────

def validate(sources: dict[str, pd.DataFrame]) -> list[str]:
    """Return a list of validation warning strings. Empty list = all clear."""
    log.info("Running data validation …")
    issues = []

    # Referential integrity: all orders must reference a known supplier & product
    valid_sup  = set(sources["suppliers"]["supplier_id"])
    valid_prod = set(sources["products"]["product_id"])
    bad_sup  = ~sources["orders"]["supplier_id"].isin(valid_sup)
    bad_prod = ~sources["orders"]["product_id"].isin(valid_prod)
    if bad_sup.any():
        issues.append(f"Orders with unknown supplier_id: {bad_sup.sum():,}")
    if bad_prod.any():
        issues.append(f"Orders with unknown product_id:  {bad_prod.sum():,}")

    # Nulls in critical fields
    for table, col in [
        ("orders", "order_date"), ("orders", "quantity"),
        ("inventory", "product_id"), ("inventory", "quantity_on_hand"),
    ]:
        null_count = sources[table][col].isna().sum()
        if null_count:
            issues.append(f"NULL in {table}.{col}: {null_count:,} rows")

    # Business-rule checks
    neg_qty = (sources["inventory"]["quantity_on_hand"] < 0).sum()
    if neg_qty:
        issues.append(f"Negative quantity_on_hand: {neg_qty:,} rows")

    for issue in issues:
        log.warning(f"  ⚠ {issue}")
    if not issues:
        log.info("  ✅ All validation checks passed")
    return issues


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def transform_all(sources: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    log.info("=" * 60)
    log.info("TRANSFORM phase starting")

    # Clean
    suppliers  = clean_suppliers(sources["suppliers"])
    products   = clean_products(sources["products"])
    inventory  = clean_inventory(sources["inventory"])
    orders     = clean_orders(sources["orders"])

    # Enrich
    orders     = enrich_orders(orders)
    inventory  = enrich_inventory(inventory, products)
    suppliers  = flag_suppliers(suppliers)

    # Validate (post-clean)
    cleaned_sources = {
        "suppliers": suppliers, "products": products,
        "inventory": inventory, "orders": orders,
    }
    issues = validate(cleaned_sources)

    # Build KPI tables
    supplier_kpis  = build_supplier_kpis(orders, suppliers)
    inventory_kpis = build_inventory_kpis(inventory)
    delivery_kpis  = build_delivery_kpis(orders)

    log.info("TRANSFORM phase complete")
    return {
        "suppliers":      suppliers,
        "products":       products,
        "inventory":      inventory,
        "orders":         orders,
        "supplier_kpis":  supplier_kpis,
        "inventory_kpis": inventory_kpis,
        "delivery_kpis":  delivery_kpis,
        "_validation_issues": issues,
    }
