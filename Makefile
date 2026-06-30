# LevvDeck PCB build pipeline.
# Run on a machine with KiCad 8/9 (kicad-cli + pcbnew python), Java, and
# `pip install kinet2pcb` (optional). See BUILD.md for the full walkthrough
# and the 🛑 HUMAN CHECK gates.
#
# Quick start:
#   make deps
#   make SPACING=22.86 footprint   # <-- your measured DevKit row spacing
#   make board place               # then review the placement render (HUMAN CHECK)
#   make route drc                 # then review DRC + the 3 pre-fab HUMAN CHECKs
#   make gerbers bom               # fab outputs

# KiCad's bundled python (has the pcbnew module). Override if needed, e.g.
#   make PY=/usr/lib/kicad/bin/python board
PY      ?= python3
SPACING ?= 22.86          # ESP32 DevKit pin-row spacing in mm (MEASURE IT)

BOARD   = levvdeck.kicad_pcb
NETLIST = levvdeck.net
FP      = footprints/LevvDeck.pretty/ESP32_DevKitC_38P_Socket.kicad_mod

.PHONY: all deps verify netlist connections bom footprint board place \
        route drc render gerbers clean

all: footprint netlist board place route drc gerbers bom
	@echo "== pipeline complete — review DRC report and renders =="

deps:
	pip install kinet2pcb || echo "(kinet2pcb optional; pcbnew builder is the default)"
	@echo "freerouting jar auto-downloads on 'make route'."

# ---- source generation (no KiCad needed) --------------------------------
verify:
	$(PY) gen_netlist.py --check
	$(PY) -m py_compile gen_netlist.py gen_connections.py \
	    scripts/gen_u1_footprint.py scripts/gen_bom.py scripts/build_board.py \
	    scripts/place.py scripts/_export_dsn.py scripts/_import_ses.py
	@echo "verify OK"

netlist:
	$(PY) gen_netlist.py

connections:
	$(PY) gen_connections.py

bom:
	$(PY) scripts/gen_bom.py

footprint:
	$(PY) scripts/gen_u1_footprint.py --spacing $(SPACING)

# ---- board pipeline (needs KiCad pcbnew / kicad-cli) --------------------
board: $(NETLIST) $(FP)
	$(PY) scripts/build_board.py

place: $(BOARD)
	$(PY) scripts/place.py

route: $(BOARD)
	bash scripts/route.sh

drc: $(BOARD)
	cp -f rules/jlcpcb.kicad_dru levvdeck.kicad_dru
	kicad-cli pcb drc \
	    --severity-error --exit-code-violations \
	    -o drc.rpt $(BOARD); \
	  st=$$?; echo "DRC report -> drc.rpt"; \
	  if [ $$st -ne 0 ]; then echo "DRC VIOLATIONS present (exit $$st)"; fi; \
	  exit $$st

render: $(BOARD)
	kicad-cli pcb render --side top    -o render-top.png    $(BOARD)
	kicad-cli pcb render --side bottom -o render-bottom.png $(BOARD)

gerbers: $(BOARD)
	bash scripts/export_fab.sh

clean:
	rm -f $(BOARD) $(BOARD)-bak levvdeck.dsn levvdeck.ses levvdeck.kicad_dru \
	      drc.rpt render-*.png render-*.svg levvdeck-gerber.zip
	rm -rf gerber
	@echo "cleaned generated build artifacts (kept source + levvdeck.net)"
