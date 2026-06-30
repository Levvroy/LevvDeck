#!/usr/bin/env bash
# Auto-route levvdeck.kicad_pcb with freerouting (headless).
#   levvdeck.kicad_pcb -> levvdeck.dsn -> [freerouting] -> levvdeck.ses -> board
#
# Requires: KiCad pcbnew python (for DSN export / SES import) and Java.
# freerouting jar is downloaded once (pin via FREEROUTING_VERSION / FREEROUTING_JAR).
#
# Trace widths / clearances come from the board's net classes (set min 0.15 mm
# by the pipeline; power nets are widened in KiCad's net-class editor — see
# BUILD.md). freerouting honors the DSN rules exported from the board.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

PY="${KICAD_PYTHON:-python3}"
FREEROUTING_VERSION="${FREEROUTING_VERSION:-1.9.0}"
JAR="${FREEROUTING_JAR:-freerouting-${FREEROUTING_VERSION}.jar}"
PASSES="${FREEROUTING_PASSES:-100}"

[ -f levvdeck.kicad_pcb ] || { echo "No levvdeck.kicad_pcb (run place.py first)"; exit 1; }

echo "== 1/4 export Specctra DSN =="
"$PY" scripts/_export_dsn.py levvdeck.kicad_pcb levvdeck.dsn

echo "== 2/4 ensure freerouting jar ($JAR) =="
if [ ! -f "$JAR" ]; then
  URL="https://github.com/freerouting/freerouting/releases/download/v${FREEROUTING_VERSION}/freerouting-${FREEROUTING_VERSION}.jar"
  echo "downloading $URL"
  curl -fSL "$URL" -o "$JAR"
fi

echo "== 3/4 run freerouting ($PASSES passes) =="
# freerouting uses Swing even in batch; wrap in xvfb-run when there is no display.
FR_CMD=(java -jar "$JAR" -de levvdeck.dsn -do levvdeck.ses -mp "$PASSES")
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
  echo "(no DISPLAY -> using xvfb-run)"
  xvfb-run -a "${FR_CMD[@]}"
else
  "${FR_CMD[@]}"
fi

[ -f levvdeck.ses ] || { echo "freerouting produced no .ses — check log above"; exit 1; }

echo "== 4/4 import session back into board =="
"$PY" scripts/_import_ses.py levvdeck.kicad_pcb levvdeck.ses

echo "Routing imported. Run 'make drc' next and review unrouted nets in KiCad."
