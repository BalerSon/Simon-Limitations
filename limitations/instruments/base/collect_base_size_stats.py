#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path("/home/balerso/Simon/Simon-Limitations/limitations")
BASE = ROOT / "BASECNF" / "with_rk"
OUT = ROOT / "instruments" / "base" / "base_size_stats.csv"

ROUNDS = [10, 11, 12, 13, 14]
KEYS = [1, 2, 3, 4, 5]
BLOCKS = [1, 2, 4, 8]


def cnf_stats(path: Path):
    vars_n = None
    clauses_n = None
    literals_n = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()

            if not s or s.startswith("c"):
                continue

            if s.startswith("p cnf"):
                parts = s.split()
                vars_n = int(parts[2])
                clauses_n = int(parts[3])
                continue

            lits = [x for x in s.split() if x != "0"]
            literals_n += len(lits)

    if vars_n is None or clauses_n is None:
        raise ValueError(f"No CNF header in {path}")

    return vars_n, clauses_n, literals_n


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rounds", "key", "blocks", "vars", "clauses", "literals", "path"])

        total = 0

        for r in ROUNDS:
            for k in KEYS:
                for b in BLOCKS:
                    cnf = (
                        BASE
                        / f"{r}roundsCNF"
                        / f"K{k}"
                        / "instances"
                        / f"simon32_64_r{r}_key{k}_b{b}_base.cnf"
                    )

                    if not cnf.exists():
                        raise FileNotFoundError(cnf)

                    vars_n, clauses_n, literals_n = cnf_stats(cnf)
                    w.writerow([r, k, b, vars_n, clauses_n, literals_n, cnf])
                    total += 1

    print(f"written {OUT}")
    print(f"rows: {total}")


if __name__ == "__main__":
    main()
