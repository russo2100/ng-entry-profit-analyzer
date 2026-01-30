"""
fetch_data.py - Загрузка исторических данных для Natural Gas

Поддерживаемые источники:
1. Yahoo Finance (yahoo_fin) — основной
2. Investing.com (scraping) — fallback
3. Локальный CSV файл

Автор: NG Entry & Profit Analyzer
Версия: 1.0
Дата: 2026-01-30
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, Optional, Union, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_data.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== YAHOO FINANCE ====================

def fetch_yahoo_fin(symbol: str = "NG=F", period: str = "18mo") -> Optional[pd.DataFrame]:
    """
    Загрузка данных с Yahoo Finance
    
    Args:
        symbol: Тикер символа (по умолчанию NG=F — непрерывный контракт)
        period: Период данных (18mo = 18 месяцев, 365d = 365 дней)
    
    Returns:
        OHLCV данные с колонками [date, open, high, low, close, volume] или None
    """
    try:
        # Динамический импорт (yahoo_fin может быть не установлен)
        try:
            from yahoo_fin import stock_info as si  # type: ignore
        except ImportError:
            logger.error("yahoo_fin не установлен! Установите: pip install yahoo_fin")
            return None
        
        logger.info(f"Загрузка данных Yahoo Finance: {symbol}, период {period}")
        
        # Загрузка данных
        df = si.get_data(symbol, interval="1d")
        
        # Фильтрация по периоду
        if period.endswith("mo"):
            months = int(period.replace("mo", ""))
            start_date = datetime.now() - timedelta(days=months*30)
        elif period.endswith("d"):
            days = int(period.replace("d", ""))
            start_date = datetime.now() - timedelta(days=days)
        else:
            raise ValueError(f"Неподдерживаемый формат периода: {period}")
        
        df = df[df.index >= start_date]
        
        # Переименование колонок и сброс индекса
        df = df.reset_index()
        df.rename(columns={
            'index': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }, inplace=True)
        
        # Оставляем только нужные колонки
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
        
        logger.info(f"Загружено {len(df)} строк данных из Yahoo Finance")
        return df
        
    except Exception as e:
        logger.error(f"Ошибка загрузки Yahoo Finance: {e}")
        return None


# ==================== INVESTING.COM SCRAPER ====================

def fetch_investing_com(url: str = "https://ru.investing.com/commodities/natural-gas", 
                       scrape_days: int = 400) -> Optional[pd.DataFrame]:
    """
    Скрапинг данных с Investing.com (FALLBACK, если Yahoo Finance недоступен)
    
    ВНИМАНИЕ: Требует установки beautifulsoup4, requests
    Может быть заблокировано сайтом (нужен User-Agent и rate limiting)
    
    Args:
        url: URL страницы Natural Gas на Investing.com
        scrape_days: Количество дней для загрузки (мин 252 = ~12 месяцев)
    
    Returns:
        OHLCV данные или None
    """
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
        
        logger.info(f"Попытка скрапинга Investing.com: {url}")
        logger.warning("ВНИМАНИЕ: Скрапинг может быть медленным или заблокирован сайтом")
        
        # TODO: Реализовать полноценный парсинг Investing.com
        # Сейчас возвращаем заглушку
        logger.error("Скрапинг Investing.com пока не реализован. Используйте Yahoo Finance или CSV.")
        return None
        
    except ImportError:
        logger.error("beautifulsoup4 или requests не установлены!")
        return None
    except Exception as e:
        logger.error(f"Ошибка скрапинга Investing.com: {e}")
        return None


# ==================== ЛОКАЛЬНЫЙ CSV ====================

def load_from_csv(file_path: str = "data/ng_history.csv") -> Optional[pd.DataFrame]:
    """
    Загрузка данных из локального CSV файла
    
    Формат CSV (с заголовками):
    date,open,high,low,close,volume
    2024-01-15,3.25,3.30,3.20,3.28,125000
    
    Args:
        file_path: Путь к CSV файлу
    
    Returns:
        OHLCV данные или None
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"CSV файл не найден: {file_path}")
            return None
        
        logger.info(f"Загрузка данных из CSV: {file_path}")
        df = pd.read_csv(file_path)
        
        # Проверка обязательных колонок
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"CSV файл должен содержать колонки: {required_cols}")
            return None
        
        # Преобразование даты
        df['date'] = pd.to_datetime(df['date'])
        
        # Сортировка по дате
        df = df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"Загружено {len(df)} строк из CSV")
        return df
        
    except Exception as e:
        logger.error(f"Ошибка загрузки CSV: {e}")
        return None


# ==================== ВАЛИДАЦИЯ ДАННЫХ ====================

def validate_data(df: Optional[pd.DataFrame], min_days: int = 252) -> Dict[str, Any]:
    """
    Проверка полноты и качества данных
    
    Проверки:
    1. Минимальное количество торговых дней (252 = ~12 месяцев)
    2. Отсутствие пропусков (gaps > 5 дней подряд)
    3. Отсутствие NaN значений
    4. Положительные цены (open, high, low, close > 0)
    
    Args:
        df: Данные OHLCV
        min_days: Минимальное кол-во торговых дней
    
    Returns:
        Результат валидации {'valid': bool, 'errors': list, 'warnings': list}
    """
    result: Dict[str, Any] = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    if df is None or df.empty:
        result['valid'] = False
        result['errors'].append("Данные пустые или None")
        return result
    
    # Проверка 1: Минимальное количество дней
    if len(df) < min_days:
        result['valid'] = False
        result['errors'].append(f"Недостаточно данных: {len(df)} дней (требуется >= {min_days})")
    
    # Проверка 2: NaN значения
    if df[['open', 'high', 'low', 'close']].isnull().any().any():
        result['valid'] = False
        result['errors'].append("Обнаружены NaN значения в ценах")
    
    # Проверка 3: Положительные цены
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        result['valid'] = False
        result['errors'].append("Обнаружены нулевые или отрицательные цены")
    
    # Проверка 4: Gaps (пропуски > 5 дней подряд)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    date_diffs = df['date'].diff().dt.days
    
    max_gap = date_diffs.max()
    if pd.notna(max_gap) and max_gap > 5:
        gap_count = (date_diffs > 5).sum()
        result['warnings'].append(f"Обнаружено {gap_count} пропусков > 5 дней (макс gap: {int(max_gap)} дней)")
    
    # Проверка 5: Логичность цен
    invalid_prices = (
        (df['high'] < df['low']) |
        (df['high'] < df['open']) |
        (df['high'] < df['close']) |
        (df['low'] > df['open']) |
        (df['low'] > df['close'])
    ).sum()
    
    if invalid_prices > 0:
        result['valid'] = False
        result['errors'].append(f"Обнаружено {invalid_prices} строк с нелогичными ценами")
    
    # Логирование результата
    if result['valid']:
        logger.info(f"✅ Валидация пройдена: {len(df)} дней данных")
    else:
        logger.error(f"❌ Валидация НЕ пройдена: {len(result['errors'])} ошибок")
        for error in result['errors']:
            logger.error(f"  - {error}")
    
    for warning in result['warnings']:
        logger.warning(f"  ⚠ {warning}")
    
    return result


# ==================== КЭШИРОВАНИЕ ====================

def cache_data(df: pd.DataFrame, cache_path: str = "data/ng_history_cache.csv", 
               ttl_hours: int = 24) -> bool:
    """
    Сохранение данных в локальный кэш
    
    Args:
        df: Данные OHLCV
        cache_path: Путь к файлу кэша
        ttl_hours: Time-to-live кэша (часы)
    
    Returns:
        True если сохранение успешно
    """
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        # Метаданные кэша
        metadata = {
            'cached_at': datetime.now().isoformat(),
            'rows': len(df),
            'date_range': f"{df['date'].min()} - {df['date'].max()}"
        }
        
        # Сохраняем данные
        df.to_csv(cache_path, index=False)
        
        # Сохраняем метаданные
        metadata_path = cache_path.replace('.csv', '_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Данные закэшированы: {cache_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка кэширования: {e}")
        return False


def load_from_cache(cache_path: str = "data/ng_history_cache.csv", 
                    ttl_hours: int = 24) -> Optional[pd.DataFrame]:
    """
    Загрузка данных из кэша (если не устарел)
    
    Args:
        cache_path: Путь к файлу кэша
        ttl_hours: Макс. возраст кэша (часы)
    
    Returns:
        Данные из кэша или None если устарел/отсутствует
    """
    try:
        if not os.path.exists(cache_path):
            return None
        
        metadata_path = cache_path.replace('.csv', '_metadata.json')
        if not os.path.exists(metadata_path):
            return None
        
        # Проверка возраста кэша
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        cached_at = datetime.fromisoformat(metadata['cached_at'])
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        
        if age_hours > ttl_hours:
            logger.info(f"Кэш устарел ({age_hours:.1f}ч > {ttl_hours}ч)")
            return None
        
        # Загружаем данные
        df = pd.read_csv(cache_path)
        df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"✅ Загружено из кэша: {len(df)} строк")
        return df
        
    except Exception as e:
        logger.error(f"Ошибка загрузки кэша: {e}")
        return None


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def fetch_historical_data(source_config: Dict[str, Any], 
                         use_cache: bool = True, 
                         cache_ttl_hours: int = 24) -> Dict[str, Any]:
    """
    Универсальная функция загрузки данных
    
    Args:
        source_config: Конфигурация источника
        use_cache: Использовать ли кэш
        cache_ttl_hours: Время жизни кэша
    
    Returns:
        {'data': DataFrame, 'validation': dict, 'source': str}
    """
    result: Dict[str, Any] = {
        'data': None,
        'validation': None,
        'source': None
    }
    
    # Попытка загрузки из кэша
    if use_cache:
        df = load_from_cache(ttl_hours=cache_ttl_hours)
        if df is not None:
            result['data'] = df
            result['source'] = 'cache'
            result['validation'] = validate_data(df)
            return result
    
    # Загрузка из источника
    source = source_config.get('source', 'yahoo_fin')
    df = None
    
    if source == 'yahoo_fin':
        symbol = source_config.get('symbol', 'NG=F')
        period = source_config.get('period', '18mo')
        df = fetch_yahoo_fin(symbol, period)
    
    elif source == 'csv':
        file_path = source_config.get('file_path', 'data/ng_history.csv')
        df = load_from_csv(file_path)
    
    elif source == 'investing_com':
        url = source_config.get('url', 'https://ru.investing.com/commodities/natural-gas')
        scrape_days = source_config.get('scrape_days', 400)
        df = fetch_investing_com(url, scrape_days)
    
    else:
        logger.error(f"Неизвестный источник данных: {source}")
        return result
    
    # Валидация
    if df is not None:
        validation = validate_data(df)
        result['data'] = df
        result['validation'] = validation
        result['source'] = source
        
        # Кэшируем, если валидация прошла
        if validation['valid']:
            cache_data(df, ttl_hours=cache_ttl_hours)
    
    return result


# ==================== ТЕСТИРОВАНИЕ ====================

if __name__ == "__main__":
    """Тестовый запуск"""
    logger.info("=== ТЕСТ fetch_data.py ===")
    
    config_yahoo = {
        "source": "yahoo_fin",
        "symbol": "NG=F",
        "period": "18mo"
    }
    result = fetch_historical_data(config_yahoo, use_cache=False)
    
    if result['data'] is not None:
        print(f"\n✅ Загружено {len(result['data'])} строк")
        print(f"Первые 5 строк:\n{result['data'].head()}")
    else:
        print("❌ Ошибка загрузки")
