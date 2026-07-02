#!/usr/bin/env python3
"""
Generate the custom U1 footprint: an ESP32-DevKitC-V4 (38-pin) socket made of
two 1x19 female headers. Pad names are the DevKitC silk labels (e.g. "IO21"),
which is exactly how gen_netlist.py references them, so net assignment Just
Works.

>>> 🛑 HUMAN CHECK — ROW SPACING <<<
The center-to-center distance between the two pin rows of YOUR DevKit varies by
board (commonly ~22.86 mm or ~25.40 mm). MEASURE IT WITH CALIPERS and pass it
in. Nothing about the board is final until this matches your physical board.

    python3 scripts/gen_u1_footprint.py --spacing 22.86

The footprint is authored on the front (F.Cu); place.py flips U1 to the BACK
(B.Cu) so the DevKit sits under the board with its USB port at the chosen edge.

Output: footprints/LevvDeck.pretty/ESP32_DevKitC_38P_Socket.kicad_mod
"""

from __future__ import annotations

import argparse
import os
import sys

# Make gen_netlist importable whether run from repo root or scripts/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Pinout and the canonical DevKitC pad layout live in gen_netlist (single
# source of truth). LEFT/RIGHT labels are re-exported here for gen_connections.
from gen_netlist import (  # noqa: E402
    PINOUT,
    U1_LEFT_LABELS as LEFT_LABELS,
    U1_RIGHT_LABELS as RIGHT_LABELS,
)

PITCH_MM = 2.54
DEFAULT_ROW_SPACING_MM = 22.86   # PLACEHOLDER — override with measured value
PADS_PER_ROW = 19


def label_to_net():
    """Map each footprint pad label to the net it carries (for the HUMAN CHECK
    mapping table). Unconnected DevKit pins map to None."""
    func_for_gpio = {gpio: func for func, gpio in PINOUT.items()}
    net_of = {}
    for lbl in set(LEFT_LABELS + RIGHT_LABELS):
        if lbl == "3V3":
            net_of[lbl] = "+3V3"
        elif lbl == "5V":
            net_of[lbl] = "+5V"
        elif lbl == "GND":
            net_of[lbl] = "GND"
        elif lbl in func_for_gpio:
            func = func_for_gpio[lbl]
            net_of[lbl] = "WS_DRIVE" if func == "WS2812" else func
        else:
            net_of[lbl] = None
    return net_of


def _pad(name, x, y, shape):
    return (
        '  (pad "%s" thru_hole %s\n'
        '    (at %.3f %.3f)\n'
        '    (size 1.800 1.800)\n'
        '    (drill 1.000)\n'
        '    (layers "*.Cu" "*.Mask")\n'
        '  )\n' % (name, shape, x, y)
    )


def render(spacing_mm: float) -> str:
    half = spacing_mm / 2.0
    height = (PADS_PER_ROW - 1) * PITCH_MM
    y0 = -height / 2.0

    s = []
    s.append('(footprint "ESP32_DevKitC_38P_Socket"')
    s.append('  (version 20240108)')
    s.append('  (generator "levvdeck_gen_u1_footprint")')
    s.append('  (layer "F.Cu")')
    s.append('  (descr "ESP32-DevKitC-V4 38-pin socket, 2x 1x19 female header, '
             'row spacing %.2f mm. Custom for LevvDeck. Flip to B.Cu when '
             'placing.")' % spacing_mm)
    s.append('  (tags "ESP32 DevKitC socket header")')
    s.append('  (attr through_hole)')
    s.append('  (property "Reference" "U1"')
    s.append('    (at 0 %.3f 0)' % (y0 - 2.0))
    s.append('    (layer "F.SilkS")')
    s.append('    (effects (font (size 1 1) (thickness 0.15))))')
    s.append('  (property "Value" "ESP32-DevKitC"')
    s.append('    (at 0 %.3f 0)' % (-y0 + 2.0))
    s.append('    (layer "F.Fab")')
    s.append('    (effects (font (size 1 1) (thickness 0.15))))')

    # Pads
    for i, lbl in enumerate(LEFT_LABELS):
        shape = "rect" if i == 0 else "oval"     # pin 1 square
        s.append(_pad(lbl, -half, y0 + i * PITCH_MM, shape).rstrip("\n"))
    for i, lbl in enumerate(RIGHT_LABELS):
        s.append(_pad(lbl, +half, y0 + i * PITCH_MM, "oval").rstrip("\n"))

    # Silk outline + pin-1 marker + USB direction hint (USB at bottom edge).
    ox = half + 2.0
    oy = -y0 + 1.5
    s.append('  (fp_line (start %.3f %.3f) (end %.3f %.3f) '
             '(stroke (width 0.15) (type solid)) (layer "F.SilkS"))'
             % (-ox, -oy, ox, -oy))
    s.append('  (fp_line (start %.3f %.3f) (end %.3f %.3f) '
             '(stroke (width 0.15) (type solid)) (layer "F.SilkS"))'
             % (-ox, oy, ox, oy))
    s.append('  (fp_text user "USB v"')
    s.append('    (at 0 %.3f 0)' % (oy + 1.2))
    s.append('    (layer "F.SilkS")')
    s.append('    (effects (font (size 1 1) (thickness 0.15))))')
    # Pin-1 triangle marker near 3V3.
    s.append('  (fp_text user "1"')
    s.append('    (at %.3f %.3f 0)' % (-half - 1.6, y0))
    s.append('    (layer "F.SilkS")')
    s.append('    (effects (font (size 0.8 0.8) (thickness 0.15))))')

    # Courtyard
    cx = half + 2.5
    cy = -y0 + 2.5
    s.append('  (fp_poly (pts (xy %.3f %.3f) (xy %.3f %.3f) (xy %.3f %.3f) '
             '(xy %.3f %.3f)) (stroke (width 0.05) (type solid)) (fill none) '
             '(layer "F.CrtYd"))'
             % (-cx, -cy, cx, -cy, cx, cy, -cx, cy))

    s.append(')')
    return "\n".join(s) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate U1 ESP32 socket footprint")
    p.add_argument("--spacing", type=float, default=DEFAULT_ROW_SPACING_MM,
                   help="row-to-row spacing in mm (MEASURE with calipers)")
    p.add_argument("--map", action="store_true",
                   help="print pad-label -> net mapping table and exit")
    args = p.parse_args(argv)

    if args.map:
        net_of = label_to_net()
        print("DevKitC pad -> net mapping (verify against your board):\n")
        print("  %-3s %-6s %-10s   %-3s %-6s %-10s" %
              ("pin", "left", "net", "pin", "right", "net"))
        for i in range(PADS_PER_ROW):
            ll = LEFT_LABELS[i]
            rl = RIGHT_LABELS[i]
            print("  %-3d %-6s %-10s   %-3d %-6s %-10s" %
                  (i + 1, ll, net_of[ll] or "-",
                   i + 20, rl, net_of[rl] or "-"))
        return 0

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo, "footprints", "LevvDeck.pretty")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ESP32_DevKitC_38P_Socket.kicad_mod")
    with open(out_path, "w") as fh:
        fh.write(render(args.spacing))
    print("Wrote %s (row spacing %.2f mm)" % (out_path, args.spacing))
    if abs(args.spacing - DEFAULT_ROW_SPACING_MM) < 1e-9:
        print("WARNING: using PLACEHOLDER spacing %.2f mm — measure your "
              "DevKit and re-run with --spacing." % DEFAULT_ROW_SPACING_MM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
