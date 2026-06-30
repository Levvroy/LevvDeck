#!/usr/bin/env python3
"""Import a freerouting .ses session back into the board using pcbnew.
Usage: python3 scripts/_import_ses.py [board.kicad_pcb] [in.ses]"""
import os
import sys
import pcbnew

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
board_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "levvdeck.kicad_pcb")
ses_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "levvdeck.ses")

if not os.path.isfile(ses_path):
    sys.exit("No session file: %s (did freerouting run?)" % ses_path)

board = pcbnew.LoadBoard(board_path)
ok = pcbnew.ImportSpecctraSES(board, ses_path)
if ok is False:
    sys.exit("ImportSpecctraSES reported failure")
board.Save(board_path)
print("Imported %s into %s" % (ses_path, board_path))
