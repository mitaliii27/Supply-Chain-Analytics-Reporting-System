"""
Generates realistic synthetic supply chain data (~800K+ records).
Run once before executing the ETL pipeline:
    python data/generate_data.py
"""

import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(RAW_DIR, exist_ok=True)


def gen_suppliers(n=200):
    regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
    tiers = ["Tier 1", "Tier 2", "Tier 3"]
    df = pd.DataFrame({
        "supplier_id":    [f"SUP{str(i).zfill(4)}" for i in range(1, n+1)],
        "supplier_name":  [f"Supplier_{i} Ltd" for i in range(1, n+1)],
        "region":         np.random.choice(regions, n),
        "tier":           np.random.choice(tiers, n, p=[0.2, 0.5, 0.3]),
        "rating":         np.round(np.random.uniform(2.5, 5.0, n), 2),
        "on_time_rate":   np.round(np.random.uniform(0.60, 0.99, n), 3),
        "defect_rate":    np.round(np.random.uniform(0.001, 0.05, n), 4),
        "lead_time_days": np.random.randint(3, 45, n),
        "contract_start": pd.date_range("2018-01-01", periods=n, freq="3D").strftime("%Y-%m-%d"),
        "is_active":      np.random.choice([True, False], n, p=[0.9, 0.1]),
    })
    df.to_csv(f"{RAW_DIR}/suppliers.csv", index=False)
    print(f"  suppliers.csv          → {len(df):,} rows")
    return df


def gen_products(n=500):
    categories = ["Electronics", "Apparel", "Food & Beverage", "Industrial", "Pharmaceuticals"]
    df = pd.DataFrame({
        "product_id":       [f"PRD{str(i).zfill(5)}" for i in range(1, n+1)],
        "product_name":     [f"Product_{i}" for i in range(1, n+1)],
        "category":         np.random.choice(categories, n),
        "unit_cost":        np.round(np.random.uniform(5, 2000, n), 2),
        "reorder_point":    np.random.randint(50, 500, n),
        "safety_stock":     np.random.randint(20, 200, n),
        "shelf_life_days":  np.random.choice([None, 30, 90, 180, 365], n),
        "weight_kg":        np.round(np.random.uniform(0.1, 50, n), 2),
    })
    df.to_csv(f"{RAW_DIR}/products.csv", index=False)
    print(f"  products.csv           → {len(df):,} rows")
    return df


def gen_inventory(products, n=300_000):
    warehouses = [f"WH{str(i).zfill(2)}" for i in range(1, 21)]
    base_date = datetime(2023, 1, 1)
    df = pd.DataFrame({
        "record_id":          range(1, n+1),
        "product_id":         np.random.choice(products["product_id"].values, n),
        "warehouse_id":       np.random.choice(warehouses, n),
        "quantity_on_hand":   np.random.randint(0, 5000, n),
        "quantity_reserved":  np.random.randint(0, 500, n),
        "last_updated":       [base_date + timedelta(days=int(d)) for d in np.random.randint(0, 365, n)],
        "batch_number":       [f"BATCH{str(i).zfill(7)}" for i in np.random.randint(1, 9999999, n)],
        "unit_cost_snapshot": np.round(np.random.uniform(5, 2000, n), 2),
    })
    df.to_csv(f"{RAW_DIR}/inventory.csv", index=False)
    print(f"  inventory.csv          → {len(df):,} rows")
    return df


def gen_orders(suppliers, products, n=500_000):
    statuses = ["Delivered", "In Transit", "Pending", "Cancelled", "Delayed"]
    base_date = datetime(2022, 1, 1)
    order_dates   = [base_date + timedelta(days=int(d)) for d in np.random.randint(0, 730, n)]
    expected_days = np.random.randint(3, 45, n)
    delay_days    = np.where(np.random.random(n) < 0.15, np.random.randint(1, 20, n), 0)

    df = pd.DataFrame({
        "order_id":    [f"ORD{str(i).zfill(8)}" for i in range(1, n+1)],
        "supplier_id": np.random.choice(suppliers["supplier_id"].values, n),
        "product_id":  np.random.choice(products["product_id"].values, n),
        "order_date":  order_dates,
        "expected_date": [order_dates[i] + timedelta(days=int(expected_days[i])) for i in range(n)],
        "actual_date": [
            order_dates[i] + timedelta(days=int(expected_days[i]) + int(delay_days[i]))
            if random.random() > 0.05 else None
            for i in range(n)
        ],
        "quantity":     np.random.randint(10, 1000, n),
        "unit_price":   np.round(np.random.uniform(5, 2000, n), 2),
        "status":       np.random.choice(statuses, n, p=[0.65, 0.15, 0.08, 0.05, 0.07]),
        "freight_cost": np.round(np.random.uniform(50, 5000, n), 2),
        "carrier":      np.random.choice(["FedEx", "DHL", "UPS", "BlueDart", "Maersk"], n),
    })
    df.to_csv(f"{RAW_DIR}/orders.csv", index=False)
    print(f"  orders.csv             → {len(df):,} rows")
    return df


def gen_warehouses():
    wh_ids = [f"WH{str(i).zfill(2)}" for i in range(1, 21)]
    cities = [
        "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad",
        "Pune", "Ahmedabad", "Surat", "Jaipur", "New York", "London",
        "Shanghai", "Singapore", "Dubai", "Sydney", "Frankfurt", "Paris", "Tokyo", "Toronto",
    ]
    df = pd.DataFrame({
        "warehouse_id":    wh_ids,
        "city":            cities,
        "capacity_units":  np.random.randint(50_000, 500_000, 20),
        "utilization_pct": np.round(np.random.uniform(0.40, 0.95, 20), 3),
        "manager":         [f"Manager_{i}" for i in range(1, 21)],
    })
    df.to_csv(f"{RAW_DIR}/warehouses.csv", index=False)
    print(f"  warehouses.csv         → {len(df):,} rows")
    return df


if __name__ == "__main__":
    print("Generating synthetic supply chain data …\n")
    sup  = gen_suppliers()
    prod = gen_products()
    gen_inventory(prod)
    gen_orders(sup, prod)
    gen_warehouses()
    print(f"\n✅ Done — raw CSV files saved to data/raw/")
