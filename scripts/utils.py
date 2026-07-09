import logging
import pandas as pd
from sqlalchemy import create_engine, text
from config.settings import settings

logger = logging.getLogger(__name__)

def get_db_engine():
    """Создаёт движок SQLAlchemy для подключения к БД"""
    return create_engine(settings.db_url, pool_pre_ping=True)

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Очистка и валидация данных из API"""
    
    # Удаляем дубликаты
    df = df.drop_duplicates(
        subset=['client_id', 'product_id', 'purchase_datetime', 'purchase_time_as_seconds_from_midnight']
    )
    
    # Фильтруем отменённые заказы (quantity = 0)
    df = df[df['quantity'] > 0].copy()
    
    # Пересчитываем total_price для проверки
    df['calculated_total'] = df['quantity'] * (df['price_per_item'] - df['discount_per_item'])
    mismatch = (df['total_price'] - df['calculated_total']).abs() > 0.01
    
    if mismatch.any():
        logger.warning(f"Найдено {mismatch.sum()} записей с несоответствием total_price")
        df = df[~mismatch].copy()
    
    # Приводим типы данных
    df['purchase_datetime'] = pd.to_datetime(df['purchase_datetime'])
    df['client_id'] = df['client_id'].astype(int)
    df['product_id'] = df['product_id'].astype(int)
    
    return df.drop(columns=['calculated_total'])

def upsert_sales(df: pd.DataFrame, table: str = 'sales'):
    """Загружает данные в БД с обновлением справочников"""
    
    engine = get_db_engine()
    
    # 🔧 ПЕРЕИМЕНОВЫВАЕМ КОЛОНКИ под структуру БД
    df = df.rename(columns={
        'purchase_datetime': 'purchase_date',
        'purchase_time_as_seconds_from_midnight': 'purchase_time_sec'
    })
    
    # Агрегируем данные для обновления справочников
    customers_agg = df.groupby('client_id').agg({
        'gender': 'first',
        'purchase_date': ['min', 'max'],
        'client_id': 'count',
        'total_price': 'sum'
    }).reset_index()
    customers_agg.columns = ['client_id', 'gender', 'first_seen', 'last_seen', 'total_orders', 'total_spent']
    
    products_agg = df.groupby('product_id').agg({
        'product_id': 'count',
        'quantity': 'sum',
        'price_per_item': 'mean',
        'discount_per_item': 'mean',
        'purchase_date': ['min', 'max']
    }).reset_index()
    products_agg.columns = ['product_id', 'sales_count', 'total_quantity_sold', 'avg_price', 'avg_discount', 'first_sale', 'last_sale']
    
    with engine.begin() as conn:
        # Обновляем справочник клиентов
        for _, row in customers_agg.iterrows():
            conn.execute(text("""
                INSERT INTO customers (client_id, gender, first_seen, last_seen, total_orders, total_spent)
                VALUES (:client_id, :gender, :first_seen, :last_seen, :total_orders, :total_spent)
                ON CONFLICT (client_id) DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    total_orders = customers.total_orders + EXCLUDED.total_orders,
                    total_spent = customers.total_spent + EXCLUDED.total_spent
            """), parameters=row.to_dict())
        
        # Обновляем справочник товаров
        for _, row in products_agg.iterrows():
            conn.execute(text("""
                INSERT INTO products (product_id, first_sale, last_sale, total_quantity_sold, avg_price, avg_discount)
                VALUES (:product_id, :first_sale, :last_sale, :total_quantity_sold, :avg_price, :avg_discount)
                ON CONFLICT (product_id) DO UPDATE SET
                    last_sale = EXCLUDED.last_sale,
                    total_quantity_sold = products.total_quantity_sold + EXCLUDED.total_quantity_sold
            """), parameters=row.to_dict())
        
        # Вставляем факты продаж (только нужные колонки)
        df_to_insert = df[[
            'client_id', 'product_id', 'purchase_date', 'purchase_time_sec',
            'quantity', 'price_per_item', 'discount_per_item', 'total_price'
        ]]
        df_to_insert.to_sql('sales', conn, if_exists='append', index=False, method='multi', chunksize=1000)
    
    logger.info(f"Загружено {len(df)} записей в {table}")