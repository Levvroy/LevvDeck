#!/usr/bin/env python3
"""
Build levvdeck.kicad_pcb from the design data block, with all footprints
loaded and every net assigned.

Two paths:
  1. (default) Native pcbnew builder using gen_netlist.build_design(). Robust,
     handles the custom LevvDeck:U1 lib and multi-pad GND. Needs KiCad's
     `pcbnew` Python module (ships with KiCad 8/9).
  2. `--kinet2pcb` : delegate to the `kinet2pcb` CLI instead (pip install
     kinet2pcb). Uses the project fp-lib-table + your global KiCad libs.

Run from the repo root. Requires footprints/LevvDeck.pretty to exist
(scripts/gen_u1_footprint.py) and levvdeck.net to exist (gen_netlist.py).

    python3 scripts/build_board.py [--kinet2pcb] [--kicad-fp-dir DIR]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from gen_netlist import build_design  # noqa: E402

NETLIST = os.path.join(REPO, "levvdeck.net")
BOARD = os.path.join(REPO, "levvdeck.kicad_pcb")
LOCAL_PRETTY = os.path.join(REPO, "footprints", "LevvDeck.pretty")

# Common locations of the standard KiCad footprint libraries.
STD_FP_CANDIDATES = [
    os.environ.get("KICAD9_FOOTPRINT_DIR"),
    os.environ.get("KICAD8_FOOTPRINT_DIR"),
    os.environ.get("KICAD7_FOOTPRINT_DIR"),
    "/usr/share/kicad/footprints",
    "/usr/local/share/kicad/footprints",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    "C:/Program Files/KiCad/9.0/share/kicad/footprints",
    "C:/Program Files/KiCad/8.0/share/kicad/footprints",
]


def find_std_fp_dir(override=None):
    for d in ([override] + STD_FP_CANDIDATES):
        if d and os.path.isdir(d):
            return d
    raise SystemExit(
        "Could not find KiCad's standard footprint dir. Pass --kicad-fp-dir "
        "or set KICAD9_FOOTPRINT_DIR.")


def lib_path_for(libnick, std_dir):
    if libnick == "LevvDeck":
        return LOCAL_PRETTY
    return os.path.join(std_dir, libnick + ".pretty")


def build_with_pcbnew(std_dir):
    import pcbnew

    components, nets = build_design()
    board = pcbnew.BOARD()

    # Lay refs out on a temporary grid; place.py does the real placement.
    spacing = pcbnew.FromMM(15.0)
    per_row = 6
    for idx, c in enumerate(components):
        libnick, fpname = c["footprint"].split(":", 1)
        pretty = lib_path_for(libnick, std_dir)
        fp = pcbnew.FootprintLoad(pretty, fpname)
        if fp is None:
            raise SystemExit("Footprint not found: %s (looked in %s)"
                             % (c["footprint"], pretty))
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"])
        x = (idx % per_row) * spacing
        y = (idx // per_row) * spacing
        fp.SetPosition(pcbnew.VECTOR2I(x, y))
        board.Add(fp)

    # Index footprints by reference for net assignment.
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    for netname, nodes in nets.items():
        netinfo = pcbnew.NETINFO_ITEM(board, netname)
        board.Add(netinfo)
        for ref, padname in nodes:
            fp = by_ref.get(ref)
            if fp is None:
                raise SystemExit("Missing footprint for ref %s" % ref)
            matched = [p for p in fp.Pads() if p.GetNumber() == str(padname)]
            if not matched:
                raise SystemExit("Pad %s.%s not found in footprint %s"
                                 % (ref, padname, fp.GetFPID().GetLibItemName()))
            for pad in matched:           # multiple pads (e.g. U1 GND) all set
                pad.SetNet(netinfo)

    board.Save(BOARD)
    print("Wrote %s  (%d footprints, %d nets) via pcbnew"
          % (BOARD, len(components), len(nets)))


def build_with_kinet2pcb():
    # kinet2pcb reads the project fp-lib-table + your global KiCad libs.
    cmd = ["kinet2pcb", "-i", NETLIST, "-o", BOARD, "-w"]
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=REPO, check=True)
    except FileNotFoundError:
        raise SystemExit("kinet2pcb not installed: pip install kinet2pcb")
    print("Wrote %s via kinet2pcb" % BOARD)


def main(argv=None):
    p = argparse.ArgumentParser(description="Build levvdeck.kicad_pcb")
    p.add_argument("--kinet2pcb", action="store_true",
                   help="use kinet2pcb CLI instead of the pcbnew builder")
    p.add_argument("--kicad-fp-dir", default=None,
                   help="path to KiCad standard footprints/ dir")
    args = p.parse_args(argv)

    if not os.path.isdir(LOCAL_PRETTY):
        raise SystemExit("Run scripts/gen_u1_footprint.py first (no %s)"
                         % LOCAL_PRETTY)
    if not os.path.isfile(NETLIST):
        raise SystemExit("Run gen_netlist.py first (no %s)" % NETLIST)

    if args.kinet2pcb:
        build_with_kinet2pcb()
    else:
        try:
            import pcbnew  # noqa: F401
        except ImportError:
            raise SystemExit(
                "pcbnew module not importable. Run with KiCad's python, or use "
                "--kinet2pcb. Typical: /usr/lib/kicad/bin/python or the KiCad "
                "Command Prompt on Windows.")
        std_dir = find_std_fp_dir(args.kicad_fp_dir)
        print("Standard footprints: %s" % std_dir)
        build_with_pcbnew(std_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
