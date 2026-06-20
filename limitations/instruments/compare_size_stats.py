#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path("/home/balerso/Simon/Simon-Limitations/limitations")

BASE_STATS = ROOT / "instruments" / "base" / "base_size_stats.csv"
RK_STATS = ROOT / "instruments" / "rk_schedule" / "rk_schedule_size_stats.csv"
REV_STATS = ROOT / "instruments" / "reverse_round" / "reverse_round_size_stats.csv"

OUT = ROOT / "instruments" / "comparison_size_stats.csv"


def load_base_like_stats(path):
    """
    For files with columns:
    rounds,key,blocks,vars,clauses,literals,path
    """
    data = {}

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            key = (
                int(row["rounds"]),
                int(row["key"]),
                int(row["blocks"]),
            )

            data[key] = {
                "vars": int(row["vars"]),
                "clauses": int(row["clauses"]),
                "literals": int(row["literals"]),
            }

    return data


def load_rk_stats(path):
    """
    For rk_schedule_size_stats.csv with columns:
    rounds,key,blocks,base_vars,base_clauses,base_literals,
    rk_vars,rk_clauses,rk_literals,delta_vars,delta_clauses,delta_literals
    """
    data = {}

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            key = (
                int(row["rounds"]),
                int(row["key"]),
                int(row["blocks"]),
            )

            data[key] = {
                "vars": int(row["rk_vars"]),
                "clauses": int(row["rk_clauses"]),
                "literals": int(row["rk_literals"]),
                "delta_vars": int(row["delta_vars"]),
                "delta_clauses": int(row["delta_clauses"]),
                "delta_literals": int(row["delta_literals"]),
            }

    return data


def main():
    base = load_base_like_stats(BASE_STATS)
    rk = load_rk_stats(RK_STATS)
    rev = load_base_like_stats(REV_STATS)

    keys = sorted(base.keys())

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow([
            "rounds", "key", "blocks",

            "base_vars", "base_clauses", "base_literals",

            "rk_vars", "rk_clauses", "rk_literals",
            "rk_delta_vars", "rk_delta_clauses", "rk_delta_literals",

            "reverse_vars", "reverse_clauses", "reverse_literals",
            "reverse_delta_vars", "reverse_delta_clauses", "reverse_delta_literals",
        ])

        for item in keys:
            if item not in rk:
                raise KeyError(f"Missing RK stats for {item}")
            if item not in rev:
                raise KeyError(f"Missing reverse stats for {item}")

            b0 = base[item]
            rks = rk[item]
            revs = rev[item]

            w.writerow([
                item[0], item[1], item[2],

                b0["vars"], b0["clauses"], b0["literals"],

                rks["vars"], rks["clauses"], rks["literals"],
                rks["delta_vars"], rks["delta_clauses"], rks["delta_literals"],

                revs["vars"], revs["clauses"], revs["literals"],
                revs["vars"] - b0["vars"],
                revs["clauses"] - b0["clauses"],
                revs["literals"] - b0["literals"],
            ])

    print(f"written {OUT}")
    print(f"rows: {len(keys)}")


if __name__ == "__main__":
    main()
