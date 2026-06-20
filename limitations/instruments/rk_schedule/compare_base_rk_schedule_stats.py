#!/usr/bin/env python3
from pathlib import Path


def cnf_stats(path: Path):
    vars_count = None
    clauses_header = None
    real_clauses = 0
    literals = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("c"):
                continue

            if line.startswith("p cnf"):
                parts = line.split()
                vars_count = int(parts[2])
                clauses_header = int(parts[3])
                continue

            nums = [int(x) for x in line.split() if x != "0"]
            if nums:
                real_clauses += 1
                literals += len(nums)

    return vars_count, clauses_header, real_clauses, literals


def main():
    out = Path("instruments/rk_schedule/rk_schedule_size_stats.csv")

    rows = []
    rows.append(
        "rounds,key,blocks,"
        "base_vars,base_clauses,base_literals,"
        "rk_vars,rk_clauses,rk_literals,"
        "delta_vars,delta_clauses,delta_literals"
    )

    for r in [10, 11, 12, 13, 14]:
        for k in [1, 2, 3, 4, 5]:
            for b in [1, 2, 4, 8]:
                base = Path(
                    f"BASECNF/with_rk/{r}roundsCNF/K{k}/instances/"
                    f"simon32_64_r{r}_key{k}_b{b}_base.cnf"
                )

                limited = Path(
                    f"LIMITEDCNF/rk_schedule/{r}roundsCNF/K{k}/instances/"
                    f"simon32_64_r{r}_key{k}_b{b}_rk_schedule.cnf"
                )

                if not base.exists():
                    raise FileNotFoundError(base)

                if not limited.exists():
                    raise FileNotFoundError(limited)

                bv, bc, brc, bl = cnf_stats(base)
                rv, rc, rrc, rl = cnf_stats(limited)

                rows.append(
                    f"{r},{k},{b},"
                    f"{bv},{bc},{bl},"
                    f"{rv},{rc},{rl},"
                    f"{rv-bv},{rc-bc},{rl-bl}"
                )

    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"written {out}")


if __name__ == "__main__":
    main()
