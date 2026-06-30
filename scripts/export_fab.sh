#!/usr/bin/env bash
# Export JLCPCB-ready fabrication outputs from levvdeck.kicad_pcb:
#   - Gerbers (2-layer set) + Excellon drill (PTH/NPTH separate) in gerber/
#   - levvdeck-gerber.zip
#   - final top/bottom render PNGs
# Requires kicad-cli (KiCad 8/9).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

BOARD=levvdeck.kicad_pcb
OUT=gerber
[ -f "$BOARD" ] || { echo "No $BOARD"; exit 1; }
command -v kicad-cli >/dev/null || { echo "kicad-cli not found"; exit 1; }

rm -rf "$OUT"; mkdir -p "$OUT"

echo "== Gerbers =="
kicad-cli pcb export gerbers \
  --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,F.Paste,B.Paste,Edge.Cuts \
  --no-protel-ext \
  -o "$OUT/" "$BOARD"

echo "== Drill (Excellon, PTH/NPTH separate) =="
kicad-cli pcb export drill \
  --format excellon \
  --excellon-separate-th \
  --generate-map-file \
  --map-format gerberx2 \
  -o "$OUT/" "$BOARD"

echo "== Zip =="
rm -f levvdeck-gerber.zip
( cd "$OUT" && zip -r ../levvdeck-gerber.zip . >/dev/null )
echo "wrote levvdeck-gerber.zip"

echo "== Renders =="
if kicad-cli pcb render --help >/dev/null 2>&1; then
  kicad-cli pcb render --side top    -o render-top.png    "$BOARD" || true
  kicad-cli pcb render --side bottom -o render-bottom.png "$BOARD" || true
else
  echo "(kicad-cli pcb render unavailable; falling back to SVG plot)"
  kicad-cli pcb export svg --layers F.Cu,F.SilkS,Edge.Cuts -o render-top.svg "$BOARD" || true
fi

echo "Done. Verify gerber/ in a viewer before ordering. NEVER auto-order."
