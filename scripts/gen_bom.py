#!/usr/bin/env python3
"""
Generate levvdeck-BOM.csv from the shared design data block (gen_netlist.py).
Groups identical (value, footprint) parts and lists their references.

Usage: python3 scripts/gen_bom.py [-o levvdeck-BOM.csv]
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gen_netlist import build_design  # noqa: E402


def _refkey(ref):
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def build_bom():
    components, _ = build_design()
    groups = OrderedDict()
    for c in components:
        key = (c["value"], c["footprint"], c["desc"])
        groups.setdefault(key, []).append(c["ref"])
    rows = []
    for (value, footprint, desc), refs in groups.items():
        refs_sorted = sorted(refs, key=_refkey)
        rows.append({
            "References": " ".join(refs_sorted),
            "Qty": len(refs_sorted),
            "Value": value,
            "Footprint": footprint,
            "Description": desc,
        })
    rows.sort(key=lambda r: _refkey(r["References"].split()[0]))
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate LevvDeck BOM CSV")
    p.add_argument("-o", "--output", default="levvdeck-BOM.csv")
    args = p.parse_args(argv)

    rows = build_bom()
    fields = ["References", "Qty", "Value", "Footprint", "Description"]
    with open(args.output, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    total = sum(r["Qty"] for r in rows)
    print("Wrote %s  (%d line items, %d parts)" % (args.output, len(rows), total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
