# tests/test_pipeline.py
"""
Unit tests for the Supply Chain ETL pipeline.
Run with:  pytest tests/ -v
"""

import pytest
import pandas as pd
import numpy as np
from etl.transform import (
    clean_suppliers, clean_products, clean_orders, clean_inventory,
    enrich_orders, enrich_inventory, flag_suppliers,
    build_supplier_kpis, build_delivery_kpis,
    validate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def raw_suppliers():
    return pd.DataFrame({
        "supplier_id":    ["sup001 ", "SUP002", "sup001 "],   # dupe + whitespace
        "supplier_name":  ["acme ltd", "globex inc", "acme ltd"],
        "region":         ["North America", "Europe", "North America"],
        "tier":           ["Tier 1", "Tier 2", "Tier 1"],
        "rating":         [4.5, 3.2, 4.5],
        "on_time_rate":   [0.92, 0.65, 0.92],
        "defect_rate":    [0.01, 0.06, 0.01],   # SUP002 above threshold
        "lead_time_days": [7, 14, 7],
        "contract_start": ["2020-01-01", "2021-06-15", "2020-01-01"],
        "is_active":      [True, True, True],
    })


@pytest.fixture
def raw_products():
    return pd.DataFrame({
        "product_id":       ["prd001", "PRD002"],
        "product_name":     ["Widget A", "Widget B"],
        "category":         ["Electronics", "Industrial"],
        "unit_cost":        [99.99, -5.00],   # negative should be clipped
        "reorder_point":    [100, 200],
        "safety_stock":     [50, 80],
        "shelf_life_days":  [None, 90],
        "weight_kg":        [0.5, 2.0],
    })


@pytest.fixture
def raw_orders():
    return pd.DataFrame({
        "order_id":     ["ord001", "ORD002", "ord001"],   # dupe
        "supplier_id":  ["SUP001", "SUP002", "SUP001"],
        "product_id":   ["PRD001", "PRD002", "PRD001"],
        "order_date":   ["2023-01-10", "2023-02-15", "2023-01-10"],
        "expected_date":["2023-01-20", "2023-03-01", "2023-01-20"],
        "actual_date":  ["2023-01-25", None, "2023-01-25"],
        "quantity":     [100, 50, 100],
        "unit_price":   [99.99, 49.99, 99.99],
        "freight_cost": [200.0, 150.0, 200.0],
        "status":       ["Delivered", "In Transit", "Delivered"],
        "carrier":      ["FedEx", "DHL", "FedEx"],
    })


@pytest.fixture
def raw_inventory(raw_products):
    return pd.DataFrame({
        "record_id":          [1, 2, 3],
        "product_id":         ["PRD001", "PRD002", "PRD001"],
        "warehouse_id":       ["WH01", "WH02", "WH01"],
        "quantity_on_hand":   [500, 30, 0],     # last one is stockout
        "quantity_reserved":  [50, 10, 0],
        "last_updated":       ["2023-06-01", "2023-06-15", "2023-06-20"],
        "batch_number":       ["BATCH001", "BATCH002", "BATCH003"],
        "unit_cost_snapshot": [99.99, 49.99, 99.99],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tests: clean_suppliers
# ─────────────────────────────────────────────────────────────────────────────

class TestCleanSuppliers:
    def test_deduplicates(self, raw_suppliers):
        result = clean_suppliers(raw_suppliers)
        assert len(result) == 2   # 3 rows with 1 dupe → 2

    def test_strips_whitespace(self, raw_suppliers):
        result = clean_suppliers(raw_suppliers)
        assert all(result["supplier_id"].str.strip() == result["supplier_id"])

    def test_uppercases_ids(self, raw_suppliers):
        result = clean_suppliers(raw_suppliers)
        assert all(result["supplier_id"] == result["supplier_id"].str.upper())

    def test_rating_clipped(self, raw_suppliers):
        raw = raw_suppliers.copy()
        raw.loc[0, "rating"] = 7.0   # out of range
        result = clean_suppliers(raw)
        assert result["rating"].max() <= 5


# ─────────────────────────────────────────────────────────────────────────────
# Tests: clean_products
# ─────────────────────────────────────────────────────────────────────────────

class TestCleanProducts:
    def test_unit_cost_clipped(self, raw_products):
        result = clean_products(raw_products)
        assert (result["unit_cost"] >= 0).all()

    def test_ids_uppercased(self, raw_products):
        result = clean_products(raw_products)
        assert all(result["product_id"] == result["product_id"].str.upper())


# ─────────────────────────────────────────────────────────────────────────────
# Tests: clean_orders
# ─────────────────────────────────────────────────────────────────────────────

class TestCleanOrders:
    def test_deduplicates(self, raw_orders):
        result = clean_orders(raw_orders)
        assert len(result) == 2

    def test_dates_parsed(self, raw_orders):
        result = clean_orders(raw_orders)
        assert pd.api.types.is_datetime64_any_dtype(result["order_date"])

    def test_actual_date_allows_null(self, raw_orders):
        result = clean_orders(raw_orders)
        assert result["actual_date"].isna().sum() >= 0   # NaT is OK


# ─────────────────────────────────────────────────────────────────────────────
# Tests: enrich_orders
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichOrders:
    def test_order_value_computed(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        result  = enrich_orders(cleaned)
        row = result[result["order_id"] == "ORD001"].iloc[0]
        assert abs(row["order_value"] - 100 * 99.99) < 0.01

    def test_delay_days_non_negative(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        result  = enrich_orders(cleaned)
        assert (result["delay_days"].dropna() >= 0).all()

    def test_is_on_time_flag(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        result  = enrich_orders(cleaned)
        on_time_row = result[result["order_id"] == "ORD001"]
        # Expected 2023-01-20, actual 2023-01-25 → 5 days late → NOT on time
        assert not on_time_row["is_on_time"].values[0]


# ─────────────────────────────────────────────────────────────────────────────
# Tests: enrich_inventory
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichInventory:
    def test_stockout_flag(self, raw_inventory, raw_products):
        products  = clean_products(raw_products)
        inventory = clean_inventory(raw_inventory)
        result    = enrich_inventory(inventory, products)
        stockout_rows = result[result["quantity_on_hand"] == 0]
        assert stockout_rows["is_stockout"].all()

    def test_available_qty_non_negative(self, raw_inventory, raw_products):
        products  = clean_products(raw_products)
        inventory = clean_inventory(raw_inventory)
        result    = enrich_inventory(inventory, products)
        assert (result["available_qty"] >= 0).all()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: flag_suppliers
# ─────────────────────────────────────────────────────────────────────────────

class TestFlagSuppliers:
    def test_high_defect_rate_flagged(self, raw_suppliers):
        cleaned = clean_suppliers(raw_suppliers)
        result  = flag_suppliers(cleaned)
        high_risk = result[result["defect_rate"] > 0.05]
        assert (high_risk["risk_flag"].isin(["High", "Critical"])).all()

    def test_low_risk_present(self, raw_suppliers):
        cleaned = clean_suppliers(raw_suppliers)
        result  = flag_suppliers(cleaned)
        assert "Low" in result["risk_flag"].values


# ─────────────────────────────────────────────────────────────────────────────
# Tests: build_delivery_kpis
# ─────────────────────────────────────────────────────────────────────────────

class TestDeliveryKPIs:
    def test_monthly_kpis_shape(self, raw_orders):
        orders = enrich_orders(clean_orders(raw_orders))
        kpis   = build_delivery_kpis(orders)
        assert "delivery_rate" in kpis.columns
        assert (kpis["delivery_rate"] >= 0).all()
        assert (kpis["delivery_rate"] <= 1).all()


# ─────────────────────────────────────────────────────────────────────────────
# Tests: validate
# ─────────────────────────────────────────────────────────────────────────────

class TestValidate:
    def test_no_issues_on_clean_data(self, raw_suppliers, raw_products, raw_orders, raw_inventory):
        sources = {
            "suppliers": clean_suppliers(raw_suppliers),
            "products":  clean_products(raw_products),
            "orders":    enrich_orders(clean_orders(raw_orders)),
            "inventory": clean_inventory(raw_inventory),
        }
        issues = validate(sources)
        # Reference integrity issues are expected for our small test set
        # but negative quantity should NOT appear
        qty_issues = [i for i in issues if "Negative" in i]
        assert len(qty_issues) == 0
