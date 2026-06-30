# LevvDeck

Streaming deck for OBS — an ESP32 macropad with a 3×3 Cherry MX matrix, two
EC11 rotary encoders, a 0.96" SSD1306 OLED, and 2× WS2812B LEDs.

This repo contains the **board design as code**: the netlist, firmware, custom
ESP32-DevKitC socket footprint, and a reproducible KiCad pipeline that places,
routes, DRC-checks, and exports JLCPCB-ready Gerbers.

- **Build it:** see [BUILD.md](BUILD.md) (needs KiCad 8/9 on your machine).
- **Design source of truth:** [`gen_netlist.py`](gen_netlist.py) — the locked
  pinout / matrix / footprints. `firmware.ino` mirrors the same pins.
- **Connections reference:** [`levvdeck-connections.md`](levvdeck-connections.md).

```sh
make SPACING=22.86 footprint   # your measured DevKit pin-row spacing
make netlist board place       # build + place
make route drc gerbers bom     # route, check, export
```

The 3×3 matrix uses COL2ROW with a 1N4148 per key. The ESP32 DevKitC is
socketed on the **bottom** of the board with its USB at a board edge (cutout).
See BUILD.md for the 🛑 HUMAN CHECK gates (DevKit row spacing, placement review,
diode/OLED/EC11 polarity) you must approve before fabrication.
