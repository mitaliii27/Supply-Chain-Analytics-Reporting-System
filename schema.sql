-- sql/schema.sql
-- Reference DDL for a production SQL Server / PostgreSQL deployment.
-- The pipeline uses SQLAlchemy (auto schema), but this gives you
-- an explicit typed schema for production use.

-- ─────────────────────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_suppliers (
    supplier_id      VARCHAR(10)    PRIMARY KEY,
    supplier_name    VARCHAR(200)   NOT NULL,
    region           VARCHAR(50),
    tier             VARCHAR(20),
    rating           DECIMAL(3, 2)  CHECK (rating BETWEEN 0 AND 5),
    on_time_rate     DECIMAL(5, 4)  CHECK (on_time_rate BETWEEN 0 AND 1),
    defect_rate      DECIMAL(6, 4)  CHECK (defect_rate BETWEEN 0 AND 1),
    lead_time_days   INT,
    contract_start   DATE,
    is_active        BOOLEAN        DEFAULT TRUE,
    risk_flag        VARCHAR(20)    DEFAULT 'Low',
    created_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id       VARCHAR(10)    PRIMARY KEY,
    product_name     VARCHAR(200)   NOT NULL,
    category         VARCHAR(100),
    unit_cost        DECIMAL(10, 2) CHECK (unit_cost >= 0),
    reorder_point    INT            DEFAULT 100,
    safety_stock     INT            DEFAULT 50,
    shelf_life_days  INT,
    weight_kg        DECIMAL(8, 2),
    created_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_warehouses (
    warehouse_id     VARCHAR(10)    PRIMARY KEY,
    city             VARCHAR(100),
    capacity_units   INT,
    utilization_pct  DECIMAL(4, 3)  CHECK (utilization_pct BETWEEN 0 AND 1),
    manager          VARCHAR(100),
    updated_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- FACT TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id            VARCHAR(15)    PRIMARY KEY,
    supplier_id         VARCHAR(10)    REFERENCES dim_suppliers(supplier_id),
    product_id          VARCHAR(10)    REFERENCES dim_products(product_id),
    order_date          DATE           NOT NULL,
    expected_date       DATE,
    actual_date         DATE,
    quantity            INT            CHECK (quantity > 0),
    unit_price          DECIMAL(10, 2) CHECK (unit_price >= 0),
    freight_cost        DECIMAL(10, 2) CHECK (freight_cost >= 0),
    order_value         DECIMAL(12, 2),
    total_cost          DECIMAL(12, 2),
    status              VARCHAR(20),
    carrier             VARCHAR(50),
    delay_days          INT            DEFAULT 0,
    is_on_time          BOOLEAN,
    is_delayed_critical BOOLEAN,
    order_year          INT,
    order_month         INT,
    order_quarter       INT,
    etl_loaded_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_inventory (
    record_id            BIGINT         PRIMARY KEY,
    product_id           VARCHAR(10)    REFERENCES dim_products(product_id),
    warehouse_id         VARCHAR(10)    REFERENCES dim_warehouses(warehouse_id),
    quantity_on_hand     INT            DEFAULT 0,
    quantity_reserved    INT            DEFAULT 0,
    available_qty        INT,
    stock_value          DECIMAL(14, 2),
    last_updated         TIMESTAMP,
    batch_number         VARCHAR(20),
    unit_cost_snapshot   DECIMAL(10, 2),
    safety_stock         INT,
    reorder_point        INT,
    is_low_stock         BOOLEAN,
    is_stockout          BOOLEAN,
    etl_loaded_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- KPI AGGREGATE TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kpi_supplier_monthly (
    supplier_id      VARCHAR(10),
    order_year       INT,
    order_month      INT,
    total_orders     INT,
    total_value      DECIMAL(14, 2),
    avg_delay_days   DECIMAL(6, 2),
    on_time_orders   INT,
    critical_delays  INT,
    total_freight    DECIMAL(12, 2),
    otif_rate        DECIMAL(5, 4),
    supplier_name    VARCHAR(200),
    region           VARCHAR(50),
    tier             VARCHAR(20),
    risk_flag        VARCHAR(20),
    PRIMARY KEY (supplier_id, order_year, order_month)
);

CREATE TABLE IF NOT EXISTS kpi_delivery_monthly (
    order_year         INT,
    order_month        INT,
    total_orders       INT,
    delivered          INT,
    delayed            INT,
    cancelled          INT,
    avg_delay_days     DECIMAL(6, 2),
    total_order_value  DECIMAL(14, 2),
    delivery_rate      DECIMAL(5, 4),
    cancellation_rate  DECIMAL(5, 4),
    PRIMARY KEY (order_year, order_month)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_orders_supplier  ON fact_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_orders_product   ON fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_date      ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status    ON fact_orders(status);
CREATE INDEX IF NOT EXISTS idx_inventory_wh     ON fact_inventory(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_inventory_prod   ON fact_inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_low    ON fact_inventory(is_low_stock);
