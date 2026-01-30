# Формулы и методология Breakout Strategy для NG

**Версия:** 1.0  
**Дата:** 2026-01-30  
**Таймфреймы:** 1H, 15m  
**Актив:** Natural Gas Futures (MOEX FORTS: NRG, NRH, NRJ контракты)

---

## Определение пробоя (Breakout)

### Критерии валидного пробоя:

1. **Ценовой пробой уровня:**
Long Breakout: Close > SwingHigh[-20:-5] + (0.5 × ATR)
Short Breakout: Close < SwingLow[-20:-5] - (0.5 × ATR)

text

Где:
- `SwingHigh[-20:-5]` = максимум за последние 20-5 баров (исключаем последние 5, чтобы избежать шума)
- `ATR[14]` = средний True Range за 14 периодов
- `Close[0]` = цена закрытия текущего бара

2. **Подтверждение объёмом:**
Volume > 1.5 × MA(Volume, 20)

text

Если объём не подтверждает → снижаем confidence на -15%

3. **Временной фильтр (для MOEX):**
Валидные часы пробоя: 10:00 - 22:00 МСК (пн-пт), 10:00 - 23:50 МСК (сб)

text

Пробои в ночную сессию (23:50-10:00) игнорируются (низкая ликвидность).

---

## Расчёт ATR (Average True Range)

```python
def calculate_atr(high, low, close, period=14):
 """
 high, low, close: pandas Series с историческими данными
 period: количество периодов для ATR (стандарт = 14)
 """
 tr1 = high - low  # Диапазон текущего бара
 tr2 = abs(high - close.shift(1))  # Разница макс и пред. закрытия
 tr3 = abs(low - close.shift(1))   # Разница мин и пред. закрытия
 
 true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
 atr = true_range.rolling(window=period).mean()
 
 return atr
Использование в skill:

Stop-loss: SL = Entry ± (2 × ATR)

Пробой: Требуется преодоление уровня + 0.5 × ATR (фильтр шума)

Волатильность режима: Сравнение текущего ATR с 60-дневным средним ATR

Fibonacci Retracement Levels (откаты после пробоя)
После валидного пробоя вверх/вниз цена часто откатывает к уровням Фибоначчи. Это вторичные зоны входа.

Формула расчёта:
Для Long Breakout (цена пробила вверх):

text
Swing Low  = Минимум перед пробоем (за последние 30-50 баров)
Swing High = Точка пробоя (макс бара пробоя)

Fib 38.2% = SwingHigh - 0.382 × (SwingHigh - SwingLow)
Fib 50.0% = SwingHigh - 0.500 × (SwingHigh - SwingLow)
Fib 61.8% = SwingHigh - 0.618 × (SwingHigh - SwingLow)
Для Short Breakout (цена пробила вниз):

text
Fib 38.2% = SwingLow + 0.382 × (SwingHigh - SwingLow)
Fib 50.0% = SwingLow + 0.500 × (SwingHigh - SwingLow)
Fib 61.8% = SwingLow + 0.618 × (SwingHigh - SwingLow)
Приоритет зон входа:
Приоритет	Уровень Фибоначчи	Вероятность отскока	Когда использовать
1	38.2%	55-65%	Агрессивный вход (breakout_aggressive)
2	50.0%	65-75%	Универсальный вход
3	61.8%	70-80%	Консервативный вход (breakout_conservative)
Правило: Если цена откатила глубже 78.6% → пробой считается неудачным, переходим в WAIT.

Stop-Loss Calculation
Формула для Long позиций:
python
def calculate_stop_loss_long(entry_price, atr, swing_low, style="aggressive"):
    """
    entry_price: цена входа
    atr: текущий ATR
    swing_low: ближайший swing low (минимум за последние 20-30 баров)
    style: "aggressive" или "conservative"
    """
    
    # Вариант 1: ATR-based stop
    sl_atr = entry_price - (2 * atr)
    
    # Вариант 2: Структурный stop (ниже swing low)
    sl_structure = swing_low - (0.5 * atr)  # Буфер 0.5 ATR под уровнем
    
    # Выбираем ближайший (более tight) для aggressive, дальний для conservative
    if style == "aggressive":
        stop_loss = max(sl_atr, sl_structure)  # Тот, что ближе к цене
    else:  # conservative
        stop_loss = min(sl_atr, sl_structure)  # Тот, что дальше (безопаснее)
    
    return stop_loss
Формула для Short позиций:
python
def calculate_stop_loss_short(entry_price, atr, swing_high, style="aggressive"):
    sl_atr = entry_price + (2 * atr)
    sl_structure = swing_high + (0.5 * atr)
    
    if style == "aggressive":
        stop_loss = min(sl_atr, sl_structure)
    else:
        stop_loss = max(sl_atr, sl_structure)
    
    return stop_loss
Конвертация в RUB:
python
def stop_loss_distance_rub(entry_price, stop_loss, usd_rub_rate, contract_multiplier=1000):
    """
    contract_multiplier: для NG на MOEX = 1000 (1 контракт = 1000 mmbtu)
    usd_rub_rate: курс USD/RUB (из .env или auto-fetch)
    """
    distance_points = abs(entry_price - stop_loss)
    distance_usd = distance_points * contract_multiplier
    distance_rub = distance_usd * usd_rub_rate
    
    return distance_rub
Take Profit Targets (TP1, TP2, TP3)
TP1 — Консервативная цель (RRR 1.5-2.5)
Метод 1: Ближайший уровень сопротивления/поддержки

python
def find_nearest_resistance(price_data, current_price, lookback=90):
    """
    Ищет ближайший уровень сопротивления за последние 90 дней
    """
    highs = price_data['high'].rolling(window=5).max()  # Локальные максимумы
    resistance_levels = highs[highs > current_price].unique()
    
    if len(resistance_levels) > 0:
        nearest_resistance = resistance_levels.min()
        return nearest_resistance
    else:
        return None  # Нет очевидного сопротивления → используем Fibonacci
Метод 2: Fibonacci Extension 127.2%

python
tp1 = entry_price + 1.272 × (swing_high - swing_low)
Выбор: Используем меньшее значение из двух методов (более консервативное).

TP2 — Умеренная цель (RRR 2.5-4.0)
Метод: Сезонный средний максимум текущего месяца

python
def get_seasonal_high(current_month, historical_data):
    """
    historical_data: DataFrame с колонками ['date', 'high', 'month']
    """
    month_data = historical_data[historical_data['month'] == current_month]
    seasonal_high = month_data['high'].quantile(0.75)  # 75-й процентиль
    
    return seasonal_high
Альтернатива: Fibonacci Extension 161.8%

python
tp2 = entry_price + 1.618 × (swing_high - swing_low)
TP3 — Агрессивная цель (RRR 4.0-6.0)
Метод: Экстремальное движение (90-й процентиль месячного диапазона)

python
tp3 = entry_price + 2.0 × (swing_high - swing_low)  # Удвоенный начальный импульс
Условие: TP3 используется только если:

Confidence >= 70%

Сезонность поддерживает (например, Long в январе-феврале)

EIA показывает бычий сюрприз (для Long) или медвежий (для Short)

Risk/Reward Ratio (RRR) Calculation
python
def calculate_rrr(entry, stop_loss, take_profit):
    """
    RRR = Потенциальная прибыль / Потенциальный убыток
    """
    profit = abs(take_profit - entry)
    risk = abs(entry - stop_loss)
    
    if risk == 0:
        return 0  # Защита от деления на ноль
    
    rrr = profit / risk
    return round(rrr, 2)
Минимальный приемлемый RRR: 1.5
Оптимальный RRR: 2.0 - 3.5
Агрессивный RRR: 4.0+

Если RRR < 1.5 → НЕ входим в сделку (плохой risk/reward).

Position Sizing (для справки бота)
Скилл НЕ выставляет ордера, но может рассчитать рекомендуемый размер позиции:

python
def calculate_position_size(account_balance_rub, max_risk_percent, entry_price, 
                           stop_loss, usd_rub_rate, contract_multiplier=1000):
    """
    Формула Келли (упрощённая версия)
    """
    # Максимальная сумма риска
    max_risk_rub = account_balance_rub * (max_risk_percent / 100)
    
    # Риск на 1 контракт
    distance_points = abs(entry_price - stop_loss)
    risk_per_contract_usd = distance_points * contract_multiplier
    risk_per_contract_rub = risk_per_contract_usd * usd_rub_rate
    
    # Количество контрактов
    if risk_per_contract_rub == 0:
        return 0
    
    position_size = max_risk_rub / risk_per_contract_rub
    position_size = max(1, int(position_size))  # Минимум 1 контракт
    
    return position_size
Пример:

Баланс: 500,000 RUB

Макс. риск: 2% = 10,000 RUB

Риск на контракт: 850 RUB (из stop-loss)

Размер позиции: 10,000 / 850 = 11 контрактов

Confidence Score Formula
python
def calculate_confidence_score(base_score, factors):
    """
    base_score: 50 (стартовая база)
    factors: dict с бонусами/штрафами
    """
    score = base_score
    
    # Бонусы
    if factors.get('seasonal_alignment'):
        score += 10  # Сезонность за нас (напр., Long в январе)
    if factors.get('volume_confirmation'):
        score += 10  # Объём подтвердил пробой
    if factors.get('eia_supportive'):
        score += 10  # EIA данные поддерживают направление
    if factors.get('trend_aligned'):
        score += 10  # Тренд совпадает с направлением (Long в uptrend)
    
    # Штрафы
    if factors.get('high_volatility'):
        score -= 15  # Повышенная волатильность (ATR > 120% среднего)
    if factors.get('counter_seasonal'):
        score -= 10  # Против сезонности (напр., Long в июне)
    if factors.get('weak_volume'):
        score -= 10  # Объём не подтвердил пробой
    if factors.get('near_expiry'):
        score -= 5   # Контракт истекает менее чем через 14 дней
    
    # Границы: 0-100
    score = max(0, min(100, score))
    
    return score
Примеры расчётов
Пример 1: Long Breakout (Aggressive)
Исходные данные:

Текущая цена: $3.45

SwingHigh (пробой): $3.40

SwingLow (база): $3.15

ATR: $0.12

Курс USD/RUB: 92.50

Расчёты:

Пробой подтверждён: $3.45 > $3.40 + (0.5 × $0.12) = $3.46 ❌
→ Ждём закрытия бара выше $3.46

Fibonacci levels (для вторичных входов):

Fib 38.2%: $3.40 - 0.382 × ($3.40 - $3.15) = $3.30

Fib 50.0%: $3.40 - 0.500 × ($3.40 - $3.15) = $3.28

Fib 61.8%: $3.40 - 0.618 × ($3.40 - $3.15) = $3.24

Stop-Loss:

SL (ATR): $3.45 - (2 × $0.12) = $3.21

SL (структурный): $3.15 - (0.5 × $0.12) = $3.09

Выбираем (aggressive): max($3.21, $3.09) = $3.21

Дистанция в RUB: ($3.45 - $3.21) × 1000 × 92.50 = 22,200 RUB

Take Profits:

TP1 (сопротивление $3.60 или Fib 127.2%): $3.60 (RRR = 2.1)

TP2 (сезонный макс фев): $3.80 (RRR = 3.9)

TP3 (экстремум): $3.95 (RRR = 5.6)

Confidence:

Base: 50

+10 (сезон зима)

+10 (объём подтверждён)

+10 (тренд uptrend)

= 80% (HIGH confidence)

Рекомендации по интеграции в код
Все формулы выше должны быть реализованы в scripts/calculate_zones.py

Используй pandas и numpy для векторизованных операций (быстрее циклов)

Кэшируй ATR и Fibonacci levels (не пересчитывай на каждом баре)

Логируй все промежуточные расчёты в logs/calculation_details.log (для отладки)

Валидируй выходные данные: если RRR < 1.5 → отменяй сигнал и выводи WAIT

Источники:

Technical Analysis of Financial Markets (John J. Murphy)

CME Group: Natural Gas Futures Contract Specs

Собственные бэктесты (2014-2025)