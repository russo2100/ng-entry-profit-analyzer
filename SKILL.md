## 📄 1. `SKILL.md` (ПОЛНАЯ ВЕРСИЯ с Пунктами 1 и 2)

<details>
<summary><b>⬇️ Нажми, чтобы развернуть SKILL.md (большой файл ~600 строк)</b></summary>

```markdown
---
name: ng-entry-profit-analyzer
description: >
  Identifies optimal entry points, profit targets (TP1/TP2/TP3), and stop-loss levels for Natural Gas futures (NG) 
  using 12+ months historical data, seasonal patterns, breakout strategy, and EIA reports. 
  Outputs structured JSON with confidence scores and risk levels for automated trading bots. 
  Optimized for Russian market (RUB, Moscow timezone).
license: MIT
metadata:
  author: YourName / YourOrg
  version: 0.9-staging
  created: 2026-01-30
  updated: 2026-01-30
  runtime: Python 3.10+, FastAPI, LangGraph
  dependencies: yahoo_fin, pandas, numpy, requests, pyyaml, jsonschema, matplotlib
  tags: [trading, natural-gas, breakout-strategy, seasonal-analysis, risk-management, eia-integration, figi-resolution]
---

# NG Entry & Profit Analyzer

## When to Use This Skill

Use this skill when you need to:

1. **Identify optimal entry zones** for Natural Gas futures (NG) on 1H/15m timeframes during Moscow trading hours (09:00-23:50 MSK, Mon-Sat).
2. **Calculate profit targets** (TP1/TP2/TP3) and stop-loss levels based on historical volatility and seasonal patterns (12+ months).
3. **React to EIA Storage Reports** (Thursdays 18:30 MSK) — analyze impact on current price action and adjust entry zones.
4. **Execute Breakout Trading Strategy** adapted for Russian market (RUB-based risk, Moscow timezone, investing.com data source).
5. **Sync analysis with trading bot** — generates JSON output every 30 minutes for automated parsing and decision-making.

**Do NOT use** for stocks, cryptocurrencies, or other commodities (skill calibrated specifically for NG seasonal behavior).

---

## Inputs

### Required

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| **ticker** | string | Natural Gas contract symbol | `"NG1!"`, `"NGH26"` |
| **historical_data** | CSV/JSON/config | OHLCV data (12+ months). See formats below. | `{"source": "yahoo_fin", "period": "18mo"}` |
| **current_analysis_period** | integer | Lookback window (days). Default: `60` | `30`, `60`, `90` |

#### ticker Format & FIGI Resolution

**Supported formats:**
- **Continuous contract**: `NG1!` (always refers to front month)
- **Specific month contract**: `NGH26` (March 2026), `NGM26` (June 2026), etc.

**FIGI mapping:**
If your trading bot requires FIGI identifiers (e.g., for Tinkoff Invest, Interactive Brokers APIs), the skill will resolve ticker → FIGI using:

**File**: `src/contracts.yaml`

**Example structure:**
```yaml
natural_gas:
  NG1!:
    type: continuous
    description: "Front month continuous contract"
  NGH26:
    figi: "BBG000N4R6V1"
    exchange: "NYMEX"
    expiry: "2026-03-27"
    description: "Natural Gas March 2026"
  NGJ26:
    figi: "BBG000N4R7W2"
    exchange: "NYMEX"
    expiry: "2026-04-28"
    description: "Natural Gas April 2026"
  # ... остальные месяцы ...
```

**How it works:**
1. User passes `ticker: "NGH26"` to skill
2. Skill loads `src/contracts.yaml`
3. Resolves `NGH26` → `figi: "BBG000N4R6V1"`
4. Includes FIGI in JSON output for bot to use:
   ```json
   {
     "ticker": "NGH26",
     "figi": "BBG000N4R6V1",
     "exchange": "NYMEX",
     "expiry": "2026-03-27",
     ...
   }
   ```

**Fallback:** If ticker not found in `contracts.yaml`, skill proceeds with symbol-based analysis but logs warning:
```
⚠️ FIGI not found for NGH26 in contracts.yaml. Analysis will continue but bot may need manual FIGI mapping.
```

**Maintenance:**
- Update `src/contracts.yaml` monthly when new contracts are listed (typically 2-3 months before expiry)
- Script `scripts/update_contracts.py` can auto-fetch latest FIGIs from broker API (optional, for Production)

---

#### historical_data Formats

**Option A**: CSV/JSON file
- Format: `date, open, high, low, close, volume`
- Example: `data/ng_history.csv`

**Option B**: API data source config
```json
{
  "source": "yahoo_fin",
  "symbol": "NG=F",
  "period": "18mo"
}
```

**Option C**: Investing.com scraper config
```json
{
  "source": "investing_com",
  "url": "https://ru.investing.com/commodities/natural-gas",
  "scrape_days": 400
}
```

---

### Optional

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| **strategy_style** | string | `"breakout_aggressive"` | `"breakout_aggressive"` or `"breakout_conservative"` |
| **max_risk_percent** | float | `2.0` | Max portfolio risk per trade (range: 0.5-3.0%) |
| **eia_data** | object | `null` | EIA Storage Report (recommended Thursdays). Format: `{"report_date": "2026-01-23", "net_change_bcf": -150, "total_storage_bcf": 2400}` |
| **figi** | string | `null` | Optional: FIGI identifier. If not provided, resolved from contracts.yaml |
| **contracts_yaml_path** | string | `"src/contracts.yaml"` | Path to contracts mapping file |
| **timezone** | string | `"Europe/Moscow"` | IANA timezone identifier |
| **output_format** | string | `"json"` | `"json"` or `"json+telegram"` |

---

### Input Validation

Inputs are validated against JSON Schema: `assets/input_schema.json`.

**Key validation rules:**
- `ticker`: Must match regex `^[A-Z]{2}[0-9]?!?$` or `^[A-Z]{3}[0-9]{2}$` (e.g., `NG1!`, `NGH26`)
- `historical_data`: If CSV file, must contain at least 252 trading days (≈12 months)
- `current_analysis_period`: Min 14 days, max 180 days
- `max_risk_percent`: Min 0.5%, max 5.0% (values >3% trigger warning)
- `eia_data.report_date`: Must be within last 30 days (older data flagged as stale)
- `figi`: Must match pattern `^BBG[A-Z0-9]{9}$` (if provided)

See [assets/input_schema.json](assets/input_schema.json) for full specification.

---

## Outputs

### Primary Output: JSON File

**File**: `ng_analysis_YYYYMMDD_HHMM.json`

```json
{
  "timestamp": "2026-01-30T15:30:00+03:00",
  "ticker": "NG1!",
  "figi": "BBG000N4R6V1",
  "exchange": "NYMEX",
  "expiry": "2026-03-27",
  "current_price": 3.25,
  "direction": "long",
  "confidence": 78,
  "risk_level": "medium",
  "entry_zones": [
    {
      "priority": 1,
      "range": [3.18, 3.22],
      "trigger": "breakout_pullback_to_support",
      "reasoning": "Historical seasonal low for Jan-Feb, 68% retest success rate (2015-2025 data)"
    },
    {
      "priority": 2,
      "range": [3.10, 3.14],
      "trigger": "deeper_retracement",
      "reasoning": "61.8% Fib from Dec rally, aligns with Nov 2025 accumulation zone"
    }
  ],
  "stop_loss": {
    "level": 3.05,
    "distance_points": 17,
    "distance_rub": 850,
    "reasoning": "Below weekly low + 2 ATR buffer (14-day ATR = 0.12)"
  },
  "take_profit": [
    {
      "target": "TP1",
      "level": 3.40,
      "rrr": 2.1,
      "probability": 65,
      "reasoning": "Typical Jan-Feb rally target, resistance from 2024/2025"
    },
    {
      "target": "TP2",
      "level": 3.55,
      "rrr": 3.5,
      "probability": 45,
      "reasoning": "Seasonal high for Q1 (2020-2025 avg), strong resistance"
    },
    {
      "target": "TP3",
      "level": 3.75,
      "rrr": 5.2,
      "probability": 25,
      "reasoning": "Extended breakout scenario (cold snap catalyst), 75th percentile move"
    }
  ],
  "market_context": {
    "trend": "uptrend_early_stage",
    "volatility_regime": "elevated",
    "seasonal_phase": "winter_peak_demand",
    "eia_impact": "neutral",
    "fib_levels": [3.10, 3.22, 3.40, 3.55]
  },
  "warnings": [
    "EIA report due Thu 18:30 MSK - expect 10-15% intraday volatility",
    "Contract NGH26 expires in 56 days - monitor rollover timing"
  ]
}
```

**Output schema validation**: See `assets/output_schema.json`

---

### Secondary Output: Telegram Message

**Format**: Plain text summary for human trader + bot parsing.

```
🔥 NG ENTRY SIGNAL | 2026-01-30 15:30 MSK

📊 Направление: LONG
💰 Текущая цена: $3.25
📋 Контракт: NGH26 (NYMEX, истекает 27.03.2026)
✅ Уверенность: 78% | Риск: MEDIUM

🎯 ВХОДЫ (по приоритету):
1️⃣ $3.18-$3.22 (пробой с откатом к поддержке)
2️⃣ $3.10-$3.14 (глубокая коррекция, 61.8% Fib)

🛑 STOP-LOSS: $3.05 (-850₽)

💎 ЦЕЛИ:
TP1: $3.40 (RRR 2.1) — вероятность 65%
TP2: $3.55 (RRR 3.5) — вероятность 45%
TP3: $3.75 (RRR 5.2) — вероятность 25%

📌 Обоснование: Сезонный минимум янв-фев, историческая поддержка (2015-2025), EIA в четверг — следи за волатильностью.

⚠️ Предупреждения:
- EIA отчёт четверг 18:30 МСК
- Контракт истекает через 56 дней

#NG #LongSetup #BreakoutStrategy
```

---

## Steps

### 1. Data Acquisition & Validation

**Actions**:
- Load historical data (12+ months OHLCV) from specified source (`yahoo_fin`, CSV, or `investing.com` scraper).
- Validate completeness: Check for gaps > 5 consecutive days. If gaps found, flag warning and interpolate (linear) or abort.
- Load `src/contracts.yaml` and resolve ticker → FIGI/exchange/expiry.
- Check contract expiry: If < 7 days, add warning to output.
- Download latest EIA report (if Thursday or recent data available) via EIA API.
- Fetch current price (real-time or latest close).

**Validation**:
- ✅ Data spans >= 12 months.
- ✅ Current price within 20% of last close (sanity check).
- ✅ Timezone conversion to MSK completed.
- ✅ FIGI resolved (or fallback logged).

---

### 2. Seasonal & Historical Context Analysis

**Actions**:
- **Seasonal patterns**:
  - Calculate avg monthly returns (Jan-Dec) over 10-year period.
  - Identify current month's typical behavior (e.g., Jan = winter demand spike).
  - Extract seasonal high/low ranges for current month (from historical data).

- **Volatility regime**:
  - Compute 14-day ATR (Average True Range).
  - Compare current ATR to 12-month rolling avg ATR.
  - Classify: `low` (<80% avg), `normal` (80-120%), `elevated` (>120%).

- **Trend detection** (on `current_analysis_period`):
  - Apply 50-day and 200-day moving averages.
  - Classify: `uptrend` (price > MA50 > MA200), `downtrend`, `sideways`.

**Output**: `market_context` object (trend, volatility_regime, seasonal_phase).

---

### 3. Breakout Strategy Application

**Logic** (adapted for Russian market):

- **Breakout Entry**:
  - Identify recent swing high/low (last 20-30 bars on 1H chart).
  - If price breaks above swing high + 0.5 ATR → `long` candidate.
  - If breaks below swing low - 0.5 ATR → `short` candidate.
  - **Pullback zones**: After breakout, mark 38.2%, 50%, 61.8% Fibonacci retracement levels as secondary entry zones.

- **Confirmation filters**:
  - Volume spike (>150% of 20-bar avg) on breakout bar.
  - No adverse EIA report in last 24h (if available).
  - Seasonal alignment (e.g., don't short in Jan if historically bullish).

- **Russian market adjustments**:
  - Convert all price levels to RUB for risk calculations (use current USD/RUB rate from `.env` or auto-fetch).
  - Trading hours: 09:00-23:50 MSK (Mon-Sat) — mark entries only within active hours.

**Output**: `direction` (long/short/wait), `entry_zones` (1-3 prioritized zones).

---

### 4. Risk Management & Stop-Loss Calculation

**Actions**:
- **Stop-loss placement**:
  - For long: `SL = entry - (2 × ATR)` or below recent swing low, whichever is tighter.
  - For short: `SL = entry + (2 × ATR)` or above recent swing high.
  - Ensure SL respects `max_risk_percent`: Calculate position size to limit loss to X% of account.

- **Position sizing** (for reference, not executed by skill):
  - `position_size_rub = (account_balance × max_risk_percent) / (entry - stop_loss in RUB)`.
  - Output in JSON for bot to consume.

**Output**: `stop_loss` object (level, distance_points, distance_rub, reasoning).

---

### 5. Profit Targets & RRR Calculation

**Actions**:
- **TP1** (conservative): 1st resistance level or 1.5-2× risk distance.
  - Use historical resistance zones (last 3-6 months) or Fibonacci extensions (127.2%).
- **TP2** (moderate): Seasonal high for current month or 2.5-3.5× risk.
- **TP3** (aggressive): Extended move (75th percentile of historical monthly range) or 4-6× risk.

- **Probability estimates**:
  - Backtest: How often did NG reach TP1/TP2/TP3 after similar breakout setups (last 3 years)?
  - Assign probabilities (e.g., TP1: 60-70%, TP2: 40-50%, TP3: 20-30%).

- **RRR calculation**: `RRR = (TP - entry) / (entry - SL)`.

**Output**: `take_profit` array (TP1/TP2/TP3 with levels, RRR, probability, reasoning).

---

### 6. Confidence Score & Risk Level

**Confidence score** (0-100%):
- Base: 50%.
- +10% if seasonal alignment (e.g., long in winter demand period).
- +10% if volume confirms breakout.
- +10% if EIA data supportive (e.g., drawdown > forecast for long).
- +10% if trend aligned (e.g., long in uptrend).
- -15% if high volatility regime (unpredictable).
- -10% if counter-seasonal (e.g., long in summer low-demand).

**Risk level**: `low` (confidence >75%, tight SL), `medium` (60-75%), `high` (<60% or wide SL).

**Output**: `confidence` (integer), `risk_level` (string).

---

### 7. Output Generation & Logging

**Actions**:
- Validate output against `assets/output_schema.json` using `jsonschema` library.
- Write JSON file to `outputs/ng_analysis_YYYYMMDD_HHMM.json`.
- If `output_format` includes `telegram`, send formatted message via Telegram Bot API (with fallback if fails).
- Log decision to `logs/ng_analyzer.log`:
  ```json
  {
    "timestamp": "2026-01-30T15:30:12+03:00",
    "level": "INFO",
    "event": "analysis_completed",
    "ticker": "NG1!",
    "figi": "BBG000N4R6V1",
    "direction": "long",
    "confidence": 78,
    "entry_zones_count": 2
  }
  ```

**Validation**:
- ✅ JSON schema valid (bot can parse).
- ✅ Telegram message sent or fallback saved (if enabled).
- ✅ Structured log entry written.

---

## Examples

### Example 1: Bullish Breakout After EIA Drawdown (Winter)

**Input**:
```json
{
  "ticker": "NG1!",
  "historical_data": {"source": "yahoo_fin", "symbol": "NG=F", "period": "18mo"},
  "current_analysis_period": 60,
  "strategy_style": "breakout_aggressive",
  "max_risk_percent": 2.0,
  "eia_data": {"report_date": "2026-01-23", "net_change_bcf": -180, "total_storage_bcf": 2350},
  "output_format": "json+telegram"
}
```

**Output** (abbreviated):
```json
{
  "ticker": "NG1!",
  "figi": "BBG000N4R6V1",
  "direction": "long",
  "confidence": 82,
  "entry_zones": [{"priority": 1, "range": [3.30, 3.34], "trigger": "breakout_retest"}],
  "stop_loss": {"level": 3.18, "distance_rub": 960},
  "take_profit": [
    {"target": "TP1", "level": 3.55, "rrr": 2.5, "probability": 70},
    {"target": "TP2", "level": 3.75, "rrr": 4.1, "probability": 50}
  ],
  "market_context": {"seasonal_phase": "winter_peak_demand", "eia_impact": "bullish_surprise"}
}
```

**Reasoning**: Large EIA drawdown (-180 bcf vs -140 expected) + winter demand + breakout above $3.30 resistance. High confidence.

---

### Example 2: Bearish Breakdown (Summer Low Demand)

**Input**:
```json
{
  "ticker": "NG1!",
  "historical_data": {"source": "csv", "file_path": "data/ng_18months.csv"},
  "current_analysis_period": 45,
  "strategy_style": "breakout_conservative",
  "max_risk_percent": 1.5,
  "eia_data": {"report_date": "2025-07-17", "net_change_bcf": +85, "total_storage_bcf": 3200}
}
```

**Output**:
```json
{
  "direction": "short",
  "confidence": 71,
  "entry_zones": [{"priority": 1, "range": [2.45, 2.50], "trigger": "breakdown_retest"}],
  "stop_loss": {"level": 2.62, "distance_rub": 720},
  "take_profit": [
    {"target": "TP1", "level": 2.25, "rrr": 2.0, "probability": 65},
    {"target": "TP2", "level": 2.10, "rrr": 3.2, "probability": 40}
  ],
  "market_context": {"seasonal_phase": "summer_injection_season", "eia_impact": "bearish_build"}
}
```

**Reasoning**: Seasonal weakness (July = injection season), bearish EIA (large build), breakdown below $2.50 support.

---

### Example 3: Sideways Market — Wait Signal

**Input**:
```json
{
  "ticker": "NG1!",
  "historical_data": {"source": "yahoo_fin", "symbol": "NG=F", "period": "15mo"},
  "current_analysis_period": 30,
  "strategy_style": "breakout_aggressive"
}
```

**Output**:
```json
{
  "direction": "wait",
  "confidence": 45,
  "entry_zones": [],
  "market_context": {"trend": "sideways", "volatility_regime": "low"},
  "warnings": ["No clear breakout pattern. Price consolidating in $2.80-$3.00 range for 3 weeks. Wait for volume spike or EIA catalyst."]
}
```

**Reasoning**: No breakout, low volatility, unclear direction. Skill outputs `wait` to avoid false signals.

---

### Example 4: Aggressive Entry After Failed Breakdown (Bear Trap)

**Input**:
```json
{
  "ticker": "NGH26",
  "historical_data": {"source": "investing_com", "url": "https://ru.investing.com/commodities/natural-gas", "scrape_days": 450},
  "strategy_style": "breakout_aggressive",
  "max_risk_percent": 2.5
}
```

**Output**:
```json
{
  "ticker": "NGH26",
  "figi": "BBG000N4R6V1",
  "direction": "long",
  "confidence": 75,
  "entry_zones": [{"priority": 1, "range": [3.05, 3.10], "trigger": "failed_breakdown_reversal"}],
  "stop_loss": {"level": 2.95},
  "take_profit": [{"target": "TP1", "level": 3.30, "rrr": 2.5}],
  "reasoning": "Price broke below $3.00 support but quickly reclaimed within 4 hours (bear trap). Historical data shows 72% reversal success rate in similar scenarios (2018-2025)."
}
```

---

### Example 5: EIA-Driven Volatility — Conservative Entry

**Input**:
```json
{
  "ticker": "NG1!",
  "eia_data": {"report_date": "2026-01-30", "net_change_bcf": -200, "total_storage_bcf": 2280},
  "strategy_style": "breakout_conservative",
  "max_risk_percent": 1.0
}
```

**Output**:
```json
{
  "direction": "long",
  "confidence": 68,
  "entry_zones": [{"priority": 1, "range": [3.40, 3.45], "trigger": "post_eia_stabilization"}],
  "warnings": ["EIA report just released. Wait 1-2 hours for initial volatility to settle before entering."],
  "market_context": {"eia_impact": "very_bullish", "volatility_regime": "elevated"}
}
```

**Reasoning**: Massive drawdown (-200 bcf) but conservative style → wait for post-EIA stabilization before entry.

---

## Limitations

1. **Not financial advice**: This skill provides analytical scenarios, not trading recommendations. User is solely responsible for trading decisions.

2. **Data dependency**: Requires high-quality 12+ months historical data. Gaps or errors in data will degrade accuracy.

3. **EIA API reliability**: EIA API may have downtime or delayed updates. Skill uses cached data as fallback but may miss real-time impact.

4. **Breakout false signals**: Breakout strategy has ~40-50% win rate in choppy markets. Skill attempts to filter but cannot eliminate false breakouts.

5. **Seasonal anomalies**: Extreme weather events (e.g., polar vortex, hurricane) can override seasonal patterns. Skill flags warnings but cannot predict black-swan events.

6. **Execution risk**: Skill does NOT place orders. Latency between signal generation and manual/bot execution can result in slippage.

7. **Russian market specifics**: RUB conversion rates fluctuate. Skill uses snapshot rate at analysis time; real execution may differ.

8. **Timeframe limitations**: Optimized for 1H/15m intraday trading. Not suitable for scalping (<5m) or long-term investing (weeks+).

9. **FIGI dependency**: If `contracts.yaml` is outdated, FIGI resolution may fail. Update file monthly or use `scripts/update_contracts.py`.

10. **Contract expiry**: Skill warns about upcoming expiry but does NOT auto-roll positions. User must manage rollover manually.

---

## What NOT to Do

❌ **Do NOT** use this skill for:
- Crypto, stocks, forex, or other commodities (calibrated only for Natural Gas).
- High-frequency trading (sub-5-minute timeframes).
- Backtesting (skill is for forward-looking analysis, not historical simulation).
- Live trading without human oversight (always validate signals before execution).

❌ **Do NOT** expect:
- 100% win rate (realistic expectation: 50-60% with good RRR).
- Instant execution (skill generates signals, bot must parse and act).
- Fundamental deep-dive (skill incorporates EIA basics but not full supply/demand modeling).

❌ **Do NOT** override:
- Stop-loss levels (skill calculations are risk-management critical).
- Data source without validation (incorrect data → incorrect signals).
- FIGI mapping without checking `contracts.yaml` (wrong contract → wrong execution).

---

## Metadata

- **Last Updated**: 2026-01-30
- **Version**: 0.9-staging
- **Test Coverage**: 20 scenarios (targeting 100+ for production)
- **Avg Execution Time**: 15-30 seconds (depends on data source latency)
- **Dependencies**: Python 3.10+, `yahoo_fin`, `pandas`, `numpy`, `requests`, `pyyaml`, `jsonschema`, `python-telegram-bot`
- **Integration**: FastAPI endpoint `/analyze-ng`, LangGraph node, standalone CLI script

---

## Support & Contribution

- **Issues**: Report bugs or request features via GitHub Issues.
- **Discussions**: Join Telegram group @ng_trading_strategy_ru for community support.
- **Contributions**: PRs welcome for: additional data sources, refined seasonal models, alternative breakout filters.

---

**Disclaimer**: Past performance is not indicative of future results. Use at your own risk. Always backtest and paper-trade before live deployment.
```

</details>

***

## 📄 2. `assets/output_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NG Entry & Profit Analyzer - Output Schema",
  "type": "object",
  "required": [
    "timestamp",
    "ticker",
    "current_price",
    "direction",
    "confidence",
    "risk_level",
    "entry_zones",
    "stop_loss",
    "take_profit",
    "market_context"
  ],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Analysis timestamp in ISO 8601 format"
    },
    "ticker": {
      "type": "string",
      "description": "Natural Gas contract symbol"
    },
    "figi": {
      "type": ["string", "null"],
      "pattern": "^BBG[A-Z0-9]{9}$",
      "description": "FIGI identifier (resolved from contracts.yaml or null if not found)"
    },
    "exchange": {
      "type": ["string", "null"],
      "description": "Exchange code (e.g., NYMEX)"
    },
    "expiry": {
      "type": ["string", "null"],
      "format": "date",
      "description": "Contract expiry date (YYYY-MM-DD)"
    },
    "current_price": {
      "type": "number",
      "minimum": 0,
      "description": "Current market price"
    },
    "direction": {
      "enum": ["long", "short", "wait"],
      "description": "Trading direction recommendation"
    },
    "confidence": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "Confidence score (0-100%)"
    },
    "risk_level": {
      "enum": ["low", "medium", "high"],
      "description": "Risk assessment"
    },
    "entry_zones": {
      "type": "array",
      "minItems": 0,
      "items": {
        "type": "object",
        "required": ["priority", "range", "trigger", "reasoning"],
        "properties": {
          "priority": {
            "type": "integer",
            "minimum": 1,
            "description": "Priority order (1 = highest)"
          },
          "range": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 2,
            "maxItems": 2,
            "description": "[lower_bound, upper_bound]"
          },
          "trigger": {
            "type": "string",
            "description": "Entry trigger pattern"
          },
          "reasoning": {
            "type": "string",
            "description": "Why this zone is significant"
          }
        }
      }
    },
    "stop_loss": {
      "type": "object",
      "required": ["level", "distance_points", "distance_rub", "reasoning"],
      "properties": {
        "level": {"type": "number", "description": "Stop-loss price level"},
        "distance_points": {"type": "number", "description": "Distance in points"},
        "distance_rub": {"type": "number", "description": "Distance in RUB"},
        "reasoning": {"type": "string"}
      }
    },
    "take_profit": {
      "type": "array",
      "minItems": 1,
      "maxItems": 3,
      "items": {
        "type": "object",
        "required": ["target", "level", "rrr", "probability", "reasoning"],
        "properties": {
          "target": {"enum": ["TP1", "TP2", "TP3"]},
          "level": {"type": "number", "minimum": 0},
          "rrr": {"type": "number", "minimum": 0, "description": "Risk/Reward Ratio"},
          "probability": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Success probability (%)"},
          "reasoning": {"type": "string"}
        }
      }
    },
    "market_context": {
      "type": "object",
      "required": ["trend", "volatility_regime", "seasonal_phase"],
      "properties": {
        "trend": {"enum": ["uptrend", "downtrend", "sideways", "uptrend_early_stage", "downtrend_early_stage"]},
        "volatility_regime": {"enum": ["low", "normal", "elevated", "extreme"]},
        "seasonal_phase": {"type": "string", "description": "Current seasonal phase (e.g., winter_peak_demand)"},
        "eia_impact": {"enum": ["bullish", "bearish", "neutral", "bullish_surprise", "bearish_surprise", "very_bullish", "very_bearish"], "description": "EIA report impact"},
        "fib_levels": {
          "type": "array",
          "items": {"type": "number"},
          "description": "Key Fibonacci levels"
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Risk warnings and alerts"
    }
  }
}