#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

SAW_BIN="$ROOT/instruments/bin/saw"
ABC_BIN="$ROOT/instruments/bin/abc"
AIGTOAIG_BIN="$(which aigtoaig)"

WRAPPER="$ROOT/LIMITEDCNF/reverse_round/simon32_64_reverse_wrappers.cry"

for R in 10 11 12 13 14; do
  for B in 1 2 4 8; do
    echo "=== Building reverse shared: R=$R B=$B ==="

    SHARED="$ROOT/LIMITEDCNF/reverse_round/${R}roundsCNF/shared"

    mkdir -p "$SHARED/saw_files" "$SHARED/aigs" "$SHARED/aags" "$SHARED/cnfs" "$SHARED/maps"

    SAW_FILE="$SHARED/saw_files/simon32_64_r${R}_b${B}_reverse.saw"
    AIG="$SHARED/aigs/simon32_64_r${R}_b${B}_reverse_rk.aig"
    OPT_AIG="$SHARED/aigs/simon32_64_r${R}_b${B}_reverse_rk_opt.aig"
    AAG="$SHARED/aags/simon32_64_r${R}_b${B}_reverse_rk_opt.aag"
    CNF="$SHARED/cnfs/simon32_64_r${R}_b${B}_reverse_rk_opt_mapped.cnf"
    MAP="$SHARED/maps/simon32_64_r${R}_b${B}_reverse_rk_combined_map.txt"

    cat > "$SAW_FILE" << EOF
m <- cryptol_load "$WRAPPER";

enc <- cryptol_extract m "enc${R}_reverse_rk_${B}blocks";

write_aig "aigs/simon32_64_r${R}_b${B}_reverse_rk.aig" enc;
EOF

    (
      cd "$SHARED"
      "$SAW_BIN" -B "saw_files/simon32_64_r${R}_b${B}_reverse.saw"

      "$ABC_BIN" -c "read_aiger aigs/simon32_64_r${R}_b${B}_reverse_rk.aig; fraig; write_aiger -s aigs/simon32_64_r${R}_b${B}_reverse_rk_opt.aig"

      "$AIGTOAIG_BIN" \
        "aigs/simon32_64_r${R}_b${B}_reverse_rk_opt.aig" \
        "aags/simon32_64_r${R}_b${B}_reverse_rk_opt.aag"
    )

    python3 "$ROOT/instruments/base/aig_to_cnf_with_map.py" \
      --aag "$AAG" \
      --cnf "$CNF" \
      --map "$MAP"

    echo
  done
done
