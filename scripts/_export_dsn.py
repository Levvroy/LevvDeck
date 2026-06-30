#!/usr/bin/env python3
"""Export levvdeck.kicad_pcb -> levvdeck.dsn (Specctra) using pcbnew.
kicad-cli has no specctra export, so we use the pcbnew Python API.
Usage: python3 scripts/_export_dsn.py [board.kicad_pcb] [out.dsn]"""
import os
import sys
import pcbnew

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
board_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "levvdeck.kicad_pcb")
dsn_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "levvdeck.dsn")

board = pcbnew.LoadBoard(board_path)
ok = pcbnew.ExportSpecctraDSN(board, dsn_path)
if not ok and not os.path.isfile(dsn_path):
    sys.exit("ExportSpecctraDSN failed")
print("Wrote %s" % dsn_path)
