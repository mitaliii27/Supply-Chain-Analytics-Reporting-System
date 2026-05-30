-- sql/kpi_queries.sql
-- Run these against supply_chain.db after the ETL pipeline executes.
-- Compatible with SQLite, PostgreSQL, and SQL Server (minor syntax tweaks for MSSQL).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. TOP 10 SUPPLIERS BY TOTAL ORDER VALUE (YTD)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    s.supplier_name,
    s.region,
    s.tier,
    s.risk_flag,
    COUNT(o.order_id)            AS total_orders,
    ROUND(SUM(o.order_value), 2) AS total_order_value,
    ROUND(AVG(o.delay_days), 2)  AS avg_delay_days,
    ROUND(AVG(CAST(o.is_on_time AS REAL)), 4) AS otif_rate
FROM orders o
JOIN suppliers s ON o.supplier_id = s.supplier_id
WHERE o.order_year = 2023
GROUP BY s.supplier_id, s.supplier_name, s.region, s.tier, s.risk_flag
ORDER BY total_order_value DESC
LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. MONTHLY DELIVERY PERFORMANCE TREND
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_year,
    order_month,
    total_orders,
    delivered,
    delayed,
    cancelled,
    ROUND(delivery_rate * 100, 2)      AS delivery_rate_pct,
    ROUND(cancellation_rate * 100, 2)  AS cancellation_rate_pct,
    ROUND(avg_delay_days, 2)           AS avg_delay_days,
    ROUND(total_order_value, 2)        AS total_order_value
FROM delivery_kpis
ORDER BY order_year, order_month;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. WAREHOUSE STOCK HEALTH DASHBOARD
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ik.warehouse_id,
    w.city,
    ik.total_skus,
    ROUND(ik.total_stock_value, 2)   AS total_stock_value,
    ik.low_stock_items,
    ik.stockout_items,
    ROUND(ik.stockout_pct * 100, 2)  AS stockout_pct,
    ROUND(w.utilization_pct * 100, 2) AS utilization_pct
FROM inventory_kpis ik
LEFT JOIN warehouses w ON ik.warehouse_id = w.warehouse_id
ORDER BY stockout_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. SUPPLIER RISK SUMMARY
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    risk_flag,
    COUNT(*)                          AS supplier_count,
    ROUND(AVG(on_time_rate) * 100, 2) AS avg_on_time_pct,
    ROUND(AVG(defect_rate) * 100, 4)  AS avg_defect_rate_pct,
    ROUND(AVG(lead_time_days), 1)     AS avg_lead_time_days
FROM suppliers
WHERE is_active = 1
GROUP BY risk_flag
ORDER BY
    CASE risk_flag
        WHEN 'Critical' THEN 1
        WHEN 'High'     THEN 2
        WHEN 'Medium'   THEN 3
        ELSE 4
    END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. INVENTORY TURNOVER RATE BY PRODUCT CATEGORY
--    (Approximation: total units ordered / avg qty on hand)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    p.category,
    COUNT(DISTINCT p.product_id)               AS product_count,
    ROUND(SUM(o.quantity), 0)                  AS total_units_ordered,
    ROUND(AVG(i.quantity_on_hand), 0)          AS avg_qty_on_hand,
    ROUND(
        CAST(SUM(o.quantity) AS REAL) /
        NULLIF(AVG(i.quantity_on_hand), 0), 2
    )                                          AS inventory_turnover
FROM products p
LEFT JOIN orders o    ON p.product_id = o.product_id
LEFT JOIN inventory i ON p.product_id = i.product_id
GROUP BY p.category
ORDER BY inventory_turnover DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. CRITICAL DELAYED ORDERS (OPERATIONAL ALERT)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    o.order_id,
    o.supplier_id,
    s.supplier_name,
    o.product_id,
    p.product_name,
    p.category,
    o.order_date,
    o.expected_date,
    o.actual_date,
    o.delay_days,
    o.status,
    ROUND(o.order_value, 2) AS order_value
FROM orders o
JOIN suppliers s ON o.supplier_id = s.supplier_id
JOIN products  p ON o.product_id  = p.product_id
WHERE o.is_delayed_critical = 1
  AND o.status NOT IN ('Cancelled', 'Delivered')
ORDER BY o.delay_days DESC
LIMIT 50;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. QUARTERLY SPEND BY CARRIER
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_year,
    order_quarter,
    carrier,
    COUNT(order_id)                AS total_shipments,
    ROUND(SUM(freight_cost), 2)    AS total_freight_cost,
    ROUND(AVG(freight_cost), 2)    AS avg_freight_cost,
    ROUND(AVG(delay_days), 2)      AS avg_delay_days
FROM orders
GROUP BY order_year, order_quarter, carrier
ORDER BY order_year, order_quarter, total_freight_cost DESC;
