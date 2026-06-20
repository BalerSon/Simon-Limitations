#!/usr/bin/env bash
set -euo pipefail

RESULTS="instruments/rk_schedule/rk_schedule_fixedkey_check_results.txt"
: > "$RESULTS"

for R in 10 11 12 13 14; do
  for K in 1 2 3 4 5; do
    for B in 1 2 4 8; do
      CNF="LIMITEDCNF/rk_schedule/${R}roundsCNF/K${K}/instances/simon32_64_r${R}_key${K}_b${B}_rk_schedule.cnf"
      MAP="BASECNF/with_rk/${R}roundsCNF/shared/maps/simon32_64_r${R}_b${B}_with_rk_combined_map.txt"
      FIXED="LIMITEDCNF/rk_schedule/${R}roundsCNF/K${K}/instances/simon32_64_r${R}_key${K}_b${B}_rk_schedule_fixedkey.cnf"
      LOG="LIMITEDCNF/rk_schedule/${R}roundsCNF/K${K}/instances/simon32_64_r${R}_key${K}_b${B}_rk_schedule_fixedkey.log"

      echo "Checking fixed-key: R=${R}, K=${K}, B=${B}"

      python3 instruments/rk_schedule/make_fixedkey_for_cnf.py \
        --rounds "$R" \
        --key-id "$K" \
        --blocks "$B" \
        --cnf "$CNF" \
        --map "$MAP" \
        --out "$FIXED" > /dev/null

      timeout 60 ./instruments/bin/kissat "$FIXED" > "$LOG" || true

      if grep -q "s SATISFIABLE" "$LOG"; then
        echo "r=$R k=$K b=$B SAT" | tee -a "$RESULTS"
      elif grep -q "s UNSATISFIABLE" "$LOG"; then
        echo "r=$R k=$K b=$B UNSAT" | tee -a "$RESULTS"
      else
        echo "r=$R k=$K b=$B TIMEOUT" | tee -a "$RESULTS"
      fi
    done
  done
done
