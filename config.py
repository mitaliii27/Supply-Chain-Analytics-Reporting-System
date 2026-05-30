# config.py – Central configuration for the Supply Chain ETL pipeline

import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR        = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR  = os.path.join(BASE_DIR, "data", "processed")
EXPORTS_DIR    = os.path.join(BASE_DIR, "data", "exports")
LOGS_DIR       = os.path.join(BASE_DIR, "logs")

for d in [PROCESSED_DIR, EXPORTS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Database (SQLite for portability; swap DSN for Postgres/SQL Server) ───────
DB_PATH = os.path.join(BASE_DIR, "supply_chain.db")
DB_DSN  = f"sqlite:///{DB_PATH}"

# ── ETL thresholds ────────────────────────────────────────────────────────────
MAX_DEFECT_RATE      = 0.05   # flag suppliers above this
MIN_ON_TIME_RATE     = 0.70   # flag suppliers below this
LOW_STOCK_MULTIPLIER = 1.2    # flag if on_hand < safety_stock * multiplier
DELAY_THRESHOLD_DAYS = 3      # orders delayed > N days flagged as critical

# ── KPI targets ───────────────────────────────────────────────────────────────
TARGET_OTIF          = 0.90   # On-Time-In-Full target
TARGET_INVENTORY_TURNOVER = 6.0
TARGET_FILL_RATE     = 0.95

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FILE   = os.path.join(LOGS_DIR, "etl_pipeline.log")
