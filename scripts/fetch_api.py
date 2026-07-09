#!/usr/bin/env python3
"""
Скрипт для сбора данных из API маркетплейса
Запускается ежедневно в 7:00 для загрузки данных за предыдущий день
"""

import sys
import os

# 🔧 Добавляем корень проекта в путь поиска модулей
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from config.settings import settings
from scripts.utils import validate_dataframe, upsert_sales, get_db_engine
from sqlalchemy import text

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/api_fetch.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def fetch_day_data(target_date: str) -> pd.DataFrame:
    """
    Загрузка данных за один день с обработкой ошибок
    
    Args:
        target_date: Дата в формате YYYY-MM-DD
    
    Returns:
        DataFrame с данными или пустой DataFrame при ошибке
    """
    params = {"date": target_date}
    
    for attempt in range(3):  # Пробуем 3 раза при ошибке
        try:
            logger.info(f"Запрос данных за {target_date} (попытка {attempt+1}/3)")
            
            response = requests.get(
                settings.API_URL, 
                params=params, 
                timeout=60,
                headers={"User-Agent": "Marketplace-Analytics-Bot/1.0"}
            )
            
            # Проверяем статус код
            if response.status_code == 429:  # Rate limit
                wait = int(response.headers.get("Retry-After", 30))
                logger.warning(f"Rate limit. Ожидание {wait} сек...")
                import time
                time.sleep(wait)
                continue
            
            response.raise_for_status()
            
            # Парсим JSON
            data = response.json()
            
            if not isinstance(data, list) or len(data) == 0:
                logger.warning(f"Пустой ответ за {target_date}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            logger.info(f" Получено {len(df)} записей за {target_date}")
            return df
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка {response.status_code}: {e}")
            break
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            break
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            break
    
    return pd.DataFrame()

def main(target_date: str = None):
    """
    Основная функция загрузки данных
    
    Args:
        target_date: Дата для загрузки (по умолчанию - вчера)
    """
    if target_date is None:
        # По умолчанию загружаем данные за вчера
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    logger.info(f"=== Начало загрузки за {target_date} ===")
    
    # 1. Получаем данные из API
    df_raw = fetch_day_data(target_date)
    
    if df_raw.empty:
        logger.warning(" Нет данных для обработки")
        return
    
    # 2. Валидируем и очищаем данные
    df_clean = validate_dataframe(df_raw)
    
    if df_clean.empty:
        logger.warning(" Все записи отфильтрованы после валидации")
        return
    
    # 3. Загружаем в базу данных
    upsert_sales(df_clean)
    
    # 4. Обновляем материализованное представление
    try:
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_metrics"))
        logger.info(" Материализованное представление обновлено")
    except Exception as e:
        logger.warning(f" Не удалось обновить представление: {e}")
    
    logger.info(f"=== Загрузка за {target_date} завершена ===")

if __name__ == "__main__":
    # Если передана дата как аргумент командной строки - используем её
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(date_arg)