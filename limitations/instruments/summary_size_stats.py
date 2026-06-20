#!/usr/bin/env python3
from pathlib import Path
import csv
from statistics import mean

ROOT = Path("/home/balerso/Simon/Simon-Limitations/limitations")
INP = ROOT / "instruments" / "comparison_size_stats.csv"
OUT = ROOT / "instruments" / "summary_size_stats.txt"


NUM_FIELDS = [
    "base_vars", "base_clauses", "base_literals",
    "rk_vars", "rk_clauses", "rk_literals",
    "rk_delta_vars", "rk_delta_clauses", "rk_delta_literals",
    "reverse_vars", "reverse_clauses", "reverse_literals",
    "reverse_delta_vars", "reverse_delta_clauses", "reverse_delta_literals",
]


def load_rows():
    rows = []
    with INP.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for name in ["rounds", "key", "blocks"] + NUM_FIELDS:
                row[name] = int(row[name])
            rows.append(row)
    return rows


def fmt_row(row):
    return f"r={row['rounds']} k={row['key']} b={row['blocks']}"


def main():
    rows = load_rows()

    lines = []
    lines.append(f"Total rows: {len(rows)}")
    lines.append("")

    for field in NUM_FIELDS:
        vals = [r[field] for r in rows]
        min_row = min(rows, key=lambda r: r[field])
        max_row = max(rows, key=lambda r: r[field])

        lines.append(f"{field}:")
        lines.append(f"  min = {min(vals)} at {fmt_row(min_row)}")
        lines.append(f"  max = {max(vals)} at {fmt_row(max_row)}")
        lines.append(f"  avg = {mean(vals):.2f}")
        lines.append("")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
