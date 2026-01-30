#!/bin/bash
python scripts/analyze_ng.py \
  --ticker ${NG_TICKER:-NG1!} \
  --data-path ${DATA_PATH:-data/ng_history.csv} \
  --strategy-style ${STRATEGY_STYLE:-breakout_aggressive} \
  --max-risk ${MAX_RISK:-2.0} \
  --output-format ${OUTPUT_FORMAT:-json+telegram}
