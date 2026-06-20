#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


RK_RE = re.compile(
    r"rk\[(\d+)\]\[(\d+)\]\s+output\s+\d+\s+aig_lit\s+-?\d+\s+dimacs_lit\s+(-?\d+)"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True, help="combined map file")
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--out", required=True, help="output json")
    args = ap.parse_args()

    map_path = Path(args.map)
    out_path = Path(args.out)

    rk = [[None for _ in range(16)] for _ in range(args.rounds)]

    with map_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = RK_RE.search(line)
            if not m:
                continue

            r = int(m.group(1))
            b = int(m.group(2))
            lit = int(m.group(3))

            if 0 <= r < args.rounds and 0 <= b < 16:
                rk[r][b] = lit

    missing = []
    for r in range(args.rounds):
        for b in range(16):
            if rk[r][b] is None:
                missing.append((r, b))

    if missing:
        raise ValueError(f"Missing rk variables: {missing[:20]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "rounds": args.rounds,
        "source_map": str(map_path),
        "rk": rk,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("OK")
    print(f"map:    {map_path}")
    print(f"out:    {out_path}")
    print(f"rounds: {args.rounds}")
    print(f"rk[0]:  {rk[0]}")
    print(f"rk[-1]: {rk[-1]}")


if __name__ == "__main__":
    main()