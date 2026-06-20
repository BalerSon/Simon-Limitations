#!/usr/bin/env bash
set -euo pipefail

for R in 10 11 12 13 14; do
  for B in 1 2 4 8; do
    MAP="BASECNF/with_rk/${R}roundsCNF/shared/maps/simon32_64_r${R}_b${B}_with_rk_combined_map.txt"
    OUT="BASECNF/with_rk/${R}roundsCNF/shared/maps/simon32_64_r${R}_b${B}_rk_vars.json"

    echo "Extracting rk vars: R=${R}, B=${B}"

    python3 instruments/rk_schedule/extract_rk_vars.py \
      --map "$MAP" \
      --rounds "$R" \
      --out "$OUT"
  done
done
