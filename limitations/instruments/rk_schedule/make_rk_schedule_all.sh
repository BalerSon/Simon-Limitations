#!/usr/bin/env bash
set -euo pipefail

for R in 10 11 12 13 14; do
  for K in 1 2 3 4 5; do
    for B in 1 2 4 8; do
      IN="BASECNF/with_rk/${R}roundsCNF/K${K}/instances/simon32_64_r${R}_key${K}_b${B}_base.cnf"
      RKMAP="BASECNF/with_rk/${R}roundsCNF/shared/maps/simon32_64_r${R}_b${B}_rk_vars.json"
      OUT="LIMITEDCNF/rk_schedule/${R}roundsCNF/K${K}/instances/simon32_64_r${R}_key${K}_b${B}_rk_schedule.cnf"

      echo "Building RK_SCHEDULE: R=${R}, K=${K}, B=${B}"

      python3 instruments/rk_schedule/add_rk_schedule_constraints.py \
        --cnf "$IN" \
        --rk-map "$RKMAP" \
        --rounds "$R" \
        --out "$OUT"
    done
  done
done
