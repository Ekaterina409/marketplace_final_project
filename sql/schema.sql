
-- Marketplace Database Schema
-- Author: Катя
-- Date: 2026-05-27

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- Таблица клиентов

CREATE TABLE IF NOT EXISTS customers (
    client_id BIGINT PRIMARY KEY,
    gender CHAR(1) CHECK (gender IN ('M', 'F')),
    first_seen DATE,
    last_seen DATE,
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0
);


-- Таблица товаров

CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT PRIMARY KEY,
    first_sale DATE,
    last_sale DATE,
    total_quantity_sold BIGINT DEFAULT 0,
    avg_price DECIMAL(10,2),
    avg_discount DECIMAL(10,2)
);


-- Таблица продаж (основная)

CREATE TABLE IF NOT EXISTS sales (
    sale_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES customers(client_id),
    product_id BIGINT REFERENCES products(product_id),
    purchase_date DATE NOT NULL,
    purchase_time_sec INT,
    quantity INT NOT NULL CHECK (quantity >= 0),
    price_per_item DECIMAL(10,2) NOT NULL,
    discount_per_item DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    CONSTRAINT valid_total CHECK (
        ABS(total_price - quantity * (price_per_item - discount_per_item)) < 0.01
    )
);


-- Индексы для ускорения запросов

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(purchase_date);
CREATE INDEX IF NOT EXISTS idx_sales_client ON sales(client_id);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_date_client ON sales(purchase_date, client_id);


-- Материализованное представление для дашборда

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_metrics AS
SELECT 
    purchase_date,
    COUNT(DISTINCT client_id) as unique_customers,
    COUNT(*) as total_transactions,
    SUM(quantity) as total_items,
    SUM(total_price) as revenue,
    AVG(total_price) as avg_check,
    SUM(CASE WHEN discount_per_item > 0 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) as discount_rate
FROM sales
WHERE quantity > 0
GROUP BY purchase_date;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_metrics_date ON mv_daily_metrics(purchase_date);


-- Комментарии к таблицам

COMMENT ON TABLE customers IS 'Справочник клиентов';
COMMENT ON TABLE products IS 'Справочник товаров';
COMMENT ON TABLE sales IS 'Факт продаж';
COMMENT ON MATERIALIZED VIEW mv_daily_metrics IS 'Агрегированные метрики по дням для дашборда';