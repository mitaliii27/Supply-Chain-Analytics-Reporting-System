# 🔗 Enterprise ETL Pipeline – Supply Chain Analytics & Reporting System

> End-to-end ETL pipeline that ingests, transforms, and surfaces KPIs for a global supply chain spanning 1M+ inventory, logistics, and supplier records.

---

## 📌 Project Overview

| Dimension | Details |
|---|---|
| **Data Volume** | ~800K+ records across 5 source datasets |
| **Tech Stack** | Python · SQL · SQLAlchemy · Streamlit · Plotly · Power BI |
| **Database** | SQLite (dev) → swap DSN for PostgreSQL / SQL Server |
| **KPIs tracked** | OTIF Rate · Inventory Turnover · Stockout % · Supplier Risk · Delivery Delays · Freight Cost |

---

## 🗂️ Repository Structure

```
supply_chain_etl/
│
├── data/
│   ├── generate_data.py      # Synthetic data generator (800K+ rows)
│   ├── raw/                  # Source CSVs (git-ignored)
│   ├── processed/            # Parquet cache (git-ignored)
│   └── exports/              # CSVs for Power BI / Tableau (git-ignored)
│
├── etl/
│   ├── config.py             # Paths, thresholds, DB DSN
│   ├── logger.py             # Centralised logging
│   ├── extract.py            # E – CSV / API ingestion
│   ├── transform.py          # T – Clean, enrich, validate, aggregate
│   └── load.py               # L – SQLite + Parquet + CSV export
│
├── sql/
│   ├── schema.sql            # Production DDL (PostgreSQL / SQL Server)
│   └── kpi_queries.sql       # 7 ready-to-run KPI queries
│
├── dashboards/
│   └── app.py                # Streamlit interactive KPI dashboard
│
├── tests/
│   ├── conftest.py
│   └── test_pipeline.py      # 20+ pytest unit tests
│
├── run_pipeline.py           # Pipeline entry-point
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

```bash
# 1. Clone & install
git clone https://github.com/<your-username>/supply-chain-etl.git
cd supply-chain-etl
pip install -r requirements.txt

# 2. Generate synthetic data (~800K rows; takes ~30s)
python data/generate_data.py

# 3. Run the full ETL pipeline
python run_pipeline.py

# 4. Launch the interactive dashboard
streamlit run dashboards/app.py

# 5. Run unit tests
pytest tests/ -v --cov=etl
```

---

## ⚙️ Pipeline Architecture

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│   EXTRACT    │───▶│    TRANSFORM     │───▶│         LOAD            │
│              │    │                  │    │                         │
│ CSV files    │    │ • Clean & dedupe │    │ SQLite / PostgreSQL DB  │
│ (suppliers,  │    │ • Enrich (KPIs,  │    │ Parquet (processed/)    │
│  products,   │    │   risk flags,    │    │ CSV exports (Power BI)  │
│  inventory,  │    │   delay calc)    │    │                         │
│  orders,     │    │ • Validate       │    │                         │
│  warehouses) │    │ • Aggregate      │    │                         │
└──────────────┘    └──────────────────┘    └─────────────────────────┘
```

---

## 📊 KPIs & Business Metrics

| KPI | Definition | Target |
|---|---|---|
| **OTIF Rate** | On-Time-In-Full delivery % | ≥ 90% |
| **Inventory Turnover** | Units ordered / avg qty on hand | ≥ 6× |
| **Stockout %** | SKUs with 0 available qty / total SKUs | < 5% |
| **Avg Delay Days** | Mean (actual − expected) for late orders | < 3 days |
| **Supplier Risk** | Flagged as Critical / High / Medium / Low | < 10% Critical |
| **Fill Rate** | Orders filled without stockout | ≥ 95% |

---

## 🏗️ Extending the Pipeline

**Swap to PostgreSQL:**
```python
# etl/config.py
DB_DSN = "postgresql+psycopg2://user:pass@localhost:5432/supply_chain"
```

**Add an API source in extract.py:**
```python
def load_from_api(endpoint: str) -> pd.DataFrame:
    import requests
    resp = requests.get(endpoint, headers={"Authorization": "Bearer <token>"})
    return pd.DataFrame(resp.json()["data"])
```

**Schedule with cron / Airflow:**
```bash
# Daily at 2 AM
0 2 * * * cd /path/to/supply-chain-etl && python run_pipeline.py
```

---

## 🧪 Testing

```bash
pytest tests/ -v                    # all tests
pytest tests/ --cov=etl             # with coverage
pytest tests/ -k "TestClean"        # specific class
```

The test suite covers:
- Deduplication and whitespace stripping
- Numeric clipping (no negative costs / quantities)
- Date parsing and null handling
- Derived column correctness (delay_days, order_value, OTIF)
- Stockout and low-stock flagging
- Supplier risk classification
- Referential integrity validation

---

## 📈 Sample Dashboard Screenshots

> Run `streamlit run dashboards/app.py` after the pipeline to see:
> - Monthly order volume vs delivery rate (dual-axis chart)
> - Supplier risk pie chart (Critical / High / Medium / Low)
> - Warehouse stockout heatmap
> - Top-10 suppliers by OTIF rate
> - Interactive table explorer for all KPI datasets

---

## 🛠️ Key Design Decisions

- **Idempotent loads** — `if_exists="replace"` ensures re-runs are safe
- **Modular ETL** — each phase (E/T/L) is independently testable
- **Config-driven thresholds** — change KPI targets in `config.py` without touching business logic
- **Dual output** — DB for querying, CSV for BI tools, Parquet for fast re-reads
- **Validation layer** — referential integrity and null checks logged as warnings, not hard failures

---

## 👩‍💻 Author

**Mitali Tornekar** — NIT Warangal, CSE · [LinkedIn](#) · [GitHub](#)
