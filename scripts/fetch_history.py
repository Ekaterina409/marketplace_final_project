#!/usr/bin/env python3
"""
Скрипт для исторической загрузки данных из API
Загружает все доступные данные за указанный период
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Добавляем корень проекта в путь
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.fetch_api import main as fetch_main

def fetch_range(start_date: str, end_date: str, delay_sec: float = 1.0):
    """
    Последовательная загрузка диапазона дат
    
    Args:
        start_date: Начальная дата (YYYY-MM-DD)
        end_date: Конечная дата (YYYY-MM-DD)
        delay_sec: Задержка между запросами (секунды)
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    
    total_days = (end - start).days + 1
    day_count = 0
    
    print(f" Начинаем историческую загрузку")
    print(f" Период: {start_date} → {end_date}")
    print(f" Всего дней: {total_days}")
    print("-" * 60)
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_count += 1
        
        print(f"\n[{day_count}/{total_days}] Загрузка за {date_str}...")
        
        try:
            # Вызываем основную функцию загрузки
            fetch_main(date_str)
        except Exception as e:
            print(f"❌ Ошибка при загрузке {date_str}: {e}")
        
        # Небольшая задержка, чтобы не перегружать API
        if current < end:
            time.sleep(delay_sec)
        
        current += timedelta(days=1)
    
    print("\n" + "=" * 60)
    print(" Историческая загрузка завершена!")
    print(f" Загружен период: {start_date} → {end_date}")
    print(f" Всего дней: {total_days}")

if __name__ == "__main__":
    # Загружаем весь 2023 год + 2024-2026 до вчерашнего дня
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    fetch_range(
        start_date="2023-01-01",
        end_date=yesterday.strftime("%Y-%m-%d"),
        delay_sec=0.5  # Полсекунды между запросами
    )