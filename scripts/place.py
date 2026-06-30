#!/usr/bin/env python3
"""
Auto-place LevvDeck components on levvdeck.kicad_pcb per the target layout, draw
the Edge.Cuts outline + M3 mounting holes, flip U1 to the back, and save.

Layout (top view, F.Cu):
  - WS2812 LED1/LED2 + R1 along the very top edge.
  - OLED header J1 centered, flanked by encoders RV1 (left) / RV2 (right).
  - 3x3 Cherry MX grid at 19.05 mm pitch; each diode tucked above its switch
    (cathode/pad1 toward the ROW line).
  - U1 (ESP32 DevKitC socket) centered, FLIPPED TO B.Cu, USB toward bottom edge.
  - Rectangular Edge.Cuts ~5 mm beyond the component bbox; 4x M3 holes.

This is a *starting* placement. Diode/switch courtyards may overlap (the diode
sits low under the switch) — tidy by hand in the 🛑 placement HUMAN CHECK.

    python3 scripts/place.py [--kicad-fp-dir DIR]
Needs KiCad's pcbnew python (KiCad 8/9).
"""

from __future__ import annotations

import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from build_board import find_std_fp_dir  # noqa: E402
from gen_netlist import MATRIX            # noqa: E402

BOARD = os.path.join(REPO, "levvdeck.kicad_pcb")

PITCH = 19.05
BX, BY = 100.0, 90.0          # board-space center reference (mm)
MARGIN = 5.0                  # Edge.Cuts margin beyond component bbox
MOUNT_INSET = 5.0             # M3 hole inset from board edge

# Switch grid: column index 0/1/2 -> dx, row index 0/1/2 -> dy.
COL_DX = {0: -PITCH, 1: 0.0, 2: PITCH}
ROW_DY = {0: 0.0, 1: PITCH, 2: 2 * PITCH}
ROW_IDX = {"ROW0": 0, "ROW1": 1, "ROW2": 2}
COL_IDX = {"COL0": 0, "COL1": 1, "COL2": 2}


def mm(v):
    import pcbnew
    return pcbnew.FromMM(v)


def vec(x, y):
    import pcbnew
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def place(fp, x, y, rot=0.0):
    fp.SetPosition(vec(x, y))
    fp.SetOrientationDegrees(rot)


def main(argv=None):
    p = argparse.ArgumentParser(description="Auto-place LevvDeck board")
    p.add_argument("--kicad-fp-dir", default=None)
    args = p.parse_args(argv)

    import pcbnew
    if not os.path.isfile(BOARD):
        raise SystemExit("No %s — run scripts/build_board.py first" % BOARD)
    board = pcbnew.LoadBoard(BOARD)
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    def F(ref):
        fp = by_ref.get(ref)
        if fp is None:
            raise SystemExit("Footprint %s not on board" % ref)
        return fp

    # --- Switch matrix + diodes -------------------------------------------
    grid_top = BY - PITCH                 # y of ROW0
    for sw, d, row, col in MATRIX:
        x = BX + COL_DX[COL_IDX[col]]
        y = grid_top + ROW_DY[ROW_IDX[row]]
        place(F(sw), x, y, 0.0)
        # Diode above the switch, vertical, cathode (pad1) toward ROW line.
        place(F(d), x, y - 9.0, 90.0)

    # --- Top band: encoders, OLED, WS2812, R1 -----------------------------
    band_y = grid_top - 24.0
    place(F("RV1"), BX - 30.0, band_y, 0.0)
    place(F("RV2"), BX + 30.0, band_y, 0.0)
    place(F("J1"),  BX,        band_y - 2.0, 0.0)   # OLED header centered

    top_y = band_y - 16.0
    place(F("LED1"), BX - 15.0, top_y, 0.0)
    place(F("LED2"), BX + 15.0, top_y, 0.0)
    place(F("R1"),   BX,        top_y, 0.0)

    # --- U1 ESP32 socket: centered, flipped to back, USB toward bottom -----
    u1 = F("U1")
    place(u1, BX, BY + PITCH * 0.5, 0.0)
    u1.Flip(u1.GetPosition(), False)      # move to B.Cu (mirrored)

    # --- Edge.Cuts from union of footprint bounding boxes + margin ---------
    bbox = None
    for fp in board.GetFootprints():
        b = fp.GetBoundingBox()
        if bbox is None:
            bbox = b
        else:
            bbox.Merge(b)
    if bbox is None:
        raise SystemExit("No footprints to bound")
    x0 = pcbnew.ToMM(bbox.GetLeft()) - MARGIN
    y0 = pcbnew.ToMM(bbox.GetTop()) - MARGIN
    x1 = pcbnew.ToMM(bbox.GetRight()) + MARGIN
    y1 = pcbnew.ToMM(bbox.GetBottom()) + MARGIN

    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetStart(vec(x0, y0))
    rect.SetEnd(vec(x1, y1))
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(mm(0.1))
    board.Add(rect)

    # --- M3 mounting holes at the 4 corners -------------------------------
    std = find_std_fp_dir(args.kicad_fp_dir)
    mh_pretty = os.path.join(std, "MountingHole.pretty")
    corners = [
        (x0 + MOUNT_INSET, y0 + MOUNT_INSET),
        (x1 - MOUNT_INSET, y0 + MOUNT_INSET),
        (x0 + MOUNT_INSET, y1 - MOUNT_INSET),
        (x1 - MOUNT_INSET, y1 - MOUNT_INSET),
    ]
    for i, (mx, my) in enumerate(corners, 1):
        mh = pcbnew.FootprintLoad(mh_pretty, "MountingHole_3.2mm_M3")
        if mh is None:
            print("WARNING: MountingHole_3.2mm_M3 not found; skipping holes")
            break
        mh.SetReference("H%d" % i)
        mh.SetPosition(vec(mx, my))
        board.Add(mh)

    board.Save(BOARD)
    w = x1 - x0
    h = y1 - y0
    print("Placed and saved %s" % BOARD)
    print("Board outline: %.1f x %.1f mm  (target ~80 x 100)" % (w, h))
    if max(w, h) > 110:
        print("NOTE: longest side %.1f mm exceeds ~100 mm — review placement."
              % max(w, h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
