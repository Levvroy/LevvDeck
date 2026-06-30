# LevvDeck — PCB Build Guide

This repo turns the LevvDeck design (ESP32 macropad: 3×3 Cherry MX matrix, 2×
EC11 encoders, SSD1306 OLED, 2× WS2812B) into fab-ready Gerbers. The design is
defined **once** in `gen_netlist.py`; everything else is generated from it.

> **This pipeline runs on YOUR machine with KiCad 8/9.** It was prepared in a
> container that has no KiCad and cannot take physical measurements, so the
> board is not finalized here — you drive the last steps and approve the three
> 🛑 HUMAN CHECK gates below.

## Prerequisites

- **KiCad 8 or 9** — provides `kicad-cli` and the `pcbnew` Python module.
  - The `pcbnew` module is KiCad's bundled python. If your system `python3`
    can't `import pcbnew`, use KiCad's python (e.g. `make PY=/usr/lib/kicad/bin/python …`
    on Linux, or run from the *KiCad Command Prompt* on Windows).
- **Java 17+** — for freerouting (auto-downloaded).
- **`pip install kinet2pcb`** — optional alternate board builder.
- Standard KiCad footprint libraries installed (default with KiCad).

## Source of truth & consistency

`gen_netlist.py` holds the locked pinout, the 3×3 matrix map, and the footprint
assignments. **`firmware.ino` mirrors the same GPIO numbers** — never change one
without the other. After any edit, regenerate:

```sh
make netlist connections bom
```

Net topology: **25 footprints, 29 nets**. (The brief estimated ~30; the
difference is the last WS2812's open `DOUT`, which is not a net.)

### Footprint note
The brief's `LED_WS2812B_PLCC4_5.0x5.0mm_P1.6mm` does not exist in the KiCad
library (that pitch is the 6-pin PLCC6 part). This design uses the correct 4-pin
WS2812B 5050 footprint **`LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm`**. All other
footprints are used exactly as named in the brief.

## Pipeline

```sh
make deps                       # kinet2pcb (optional) + freerouting note

# 🛑 HUMAN CHECK #1 — U1 row spacing. Measure your DevKit's pin-row spacing
#    (center-to-center) with calipers, then:
make SPACING=22.86 footprint    # e.g. 22.86 or 25.40 — use YOUR value
make netlist board              # netlist -> levvdeck.kicad_pcb (all nets assigned)
make place                      # auto-placement + Edge.Cuts + M3 holes
make render                     # writes render-top.png / render-bottom.png

# 🛑 HUMAN CHECK #2 — review placement render before routing. Tidy diode/switch
#    overlaps and confirm U1 USB faces the intended board edge (add the USB
#    cutout to Edge.Cuts in pcbnew).

make route                      # freerouting auto-route, imported back
make drc                        # JLCPCB ruleset -> drc.rpt (fails on violations)

# 🛑 HUMAN CHECK #3 — the three pre-fab checks (see below).

make gerbers bom                # levvdeck-gerber.zip + levvdeck-BOM.csv + renders
```

Or end-to-end once spacing is set: `make SPACING=<mm> all`.

## 🛑 HUMAN CHECK gates (do not skip)

1. **U1 DevKit row spacing.** The custom socket footprint is parameterized.
   Measure your board and pass `SPACING=<mm>`. Verify the pad→net mapping in
   `levvdeck-connections.md` (and `python3 scripts/gen_u1_footprint.py --map`)
   matches your DevKit's silk, and that **U1's USB end faces a board edge** with
   a cutout in `Edge.Cuts`. U1 is mounted on the **bottom (B.Cu)**.
2. **Placement review (before routing).** Open the render / board; confirm the
   3×3 grid pitch (19.05 mm), encoder/OLED positions, and that nothing
   important overlaps. The auto-placer leaves diodes close to switches — adjust
   by hand as needed.
3. **Pre-fabrication electrical checks.**
   - **Diode polarity:** `Dx.pad1` is the **cathode** and must face the ROW
     net. (Footprint `D_DO-35_SOD27_P7.62mm_Horizontal`, pad1 = K.)
   - **OLED header J1 order:** default is `GND / VCC / SCL / SDA` (pins 1–4).
     Confirm against your module's silk — VCC/GND or SCL/SDA order varies.
   - **EC11 pads:** `A`/`B` quadrature, `C` common→GND, `S1`/`S2` push switch.

## Net classes / trace widths

`make drc` copies `rules/jlcpcb.kicad_dru` → `levvdeck.kicad_dru` so KiCad applies
JLCPCB constraints (min track/space 0.15 mm, min drill 0.30 mm, min annular
0.13 mm). For hand soldering, widen power nets in pcbnew's **Net Class** editor:
`GND/+5V/+3V3` ≈ 0.5 mm, signals ≈ 0.3 mm, before `make route` (freerouting
honors these via the exported DSN).

## Outputs

| File | What |
|---|---|
| `levvdeck.net` | KiCad netlist (committed) |
| `levvdeck.kicad_pcb` | placed + routed board |
| `levvdeck-gerber.zip` | Gerbers + Excellon drill for JLCPCB |
| `levvdeck-BOM.csv` | bill of materials |
| `levvdeck-connections.md` | human-readable connections + U1 map |
| `render-top.png` / `render-bottom.png` | final renders |
| `drc.rpt` | DRC report |

## Pre-order checklist (JLCPCB, 2-layer)

- [ ] All three HUMAN CHECK gates approved.
- [ ] `drc.rpt` clean (no errors) against `rules/jlcpcb.kicad_dru`.
- [ ] No unrouted nets (freerouting log + pcbnew ratsnest empty).
- [ ] Board longest side ≤ keyboard length (target ~80×100 mm; `place.py` prints size).
- [ ] U1 USB cutout present on `Edge.Cuts`.
- [ ] Gerbers opened in a viewer and visually sane.
- [ ] **Never auto-order.** Upload `levvdeck-gerber.zip` manually.
