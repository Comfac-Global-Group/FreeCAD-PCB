<img align="left" width="80" height="80" src="data/FreeCAD-PCB_workbench_icon.svg">

# FreeCAD-PCB

<br>
Procedural and generative PCB workbench for FreeCAD.<br>
Original work Copyright (c) 2013-2019 [@marmni](https://github.com/marmni) <marmni@onet.eu><br>
Procedural / generative fork maintained by Comfac-Global-Group (CGG R&D).
<br><br>

<kbd>![screenshot](https://a.fsdn.com/con/app/proj/eaglepcb2freecad/screenshots/Tube_amplifier_FreeCAD-PCB.png/max/max/1)</kbd>

---

## What this fork aims to become

The upstream workbench imports and views PCB files produced by other EDA tools (Eagle, KiCad, gEDA, LibrePCB, IDF, etc.). This fork turns that into a **procedural and generative** PCB maker inside FreeCAD:

- **Procedural.** You describe the circuit in Python — parts, pins, nets — and the workbench draws the board. No schematic editor required; the code *is* the design.
- **Generative / trial-and-error.** Given the board dimensions and the circuit logic, the workbench **attempts** placements and routing over and over until it finds a layout that satisfies the design rules — or tells you clearly what makes your board impossible to route with the current parameters.
- **3D-native.** The output is a real FreeCAD parametric model. Change the board thickness, swap a footprint, change the stackup — the geometry regenerates.

## Philippine OpenEngineering Pipeline

This workbench is a module of the **[Philippine OpenEngineering Pipeline](https://sites.comfac.net/freecad.html)** — a national engineering capacity initiative led by **Comfac Technology Group** and **Cornersteel Systems Corp**.

> **Mission:** Make the Philippines not just self-sufficient in engineering software, but innovative — and give these tools freely to every Filipino engineer, student, and maker.

**How it works:**
- **Comfac (CGG)** funds the development, provides real engineering problems as the test bench, and anchors the investment.
- **Partner schools** supply OJT students and thesis researchers who work on real CGG problems, building global open-source credentials while saving their institutions millions in software costs.
- **Everything built becomes a public good.** Every module, symbol library, and procedural tool is open-sourced under AGPLv3 — reducing information asymmetry and making engineering more affordable for all Filipinos.

**Funding:** CGG has committed a minimum of **₱1M annually** to Project FreeCAD, covering technical leadership, AI tooling, OJT interns, infrastructure, and school outreach.

**School partners:** Engineering colleges and technical institutions co-develop modules, publish add-ons, and earn permanent global attribution on upstream FreeCAD contributions. No cost to join — real student credentials, real institutional savings.

**This PCB module** is the electronics design track of the pipeline. It joins the broader ecosystem: BIM/IFC, FEM, CFD, ducting/piping procedural design, and the AI labeling flywheel that converts decades of Philippine engineering drawings into editable, intelligent FreeCAD geometry.

### The difference from "import and view"

| Today (upstream) | With this fork |
|---|---|
| Open an existing `.brd` / `.kicad_pcb` | Write a Python script (or load one) that describes the circuit |
| Workbench renders what the file says | Workbench *figures out* where parts go and how traces run |
| Manual placement only; no routing | Trial-and-error placement + routing; reports best result or why none worked |
| No electrical model | Full Part / Pin / Net / Circuit graph with ERC |
| No design rules | Per-netclass DRC (trace width, clearance, annular ring, via size) |
| Geometry baked at import | Fully parametric — change a property, geometry regenerates |

---

## The design docs in this repo

Before implementation starts, the design is captured in four docs. Read them in this order:

1. **[`proceedural-pcb.md`](proceedural-pcb.md)** — the rules the workbench should follow. Extracted from the SKiDL library (a Python DSL for circuits) and extended with everything a 3D PCB needs: board outline, layer stack, footprints, DRC, vias, pours, 3D collision.
2. **[`repoanalysis.md`](repoanalysis.md)** — what the upstream workbench actually does today, at the code level. Capability matrix showing what exists vs what needs to be built.
3. **[`frd.md`](frd.md)** — the Functional Requirements Document. Gap-closure plan, phased delivery, numbered FR-XX requirements, acceptance criteria. This is the build plan.
4. **[`qa.md`](qa.md)** — open design questions with recommended answers, the verification plan (unit tests, regression suite, manual QA checklist), and the known-issue carry-forward list.

---

## Usage sketch (future API — not yet implemented)

```python
from ppcb import *

# 1. Declare the board's physical constraints
board = Board(
    outline=Sketch.rect(80, 60),
    thickness=1.6,
    stackup=Stackup.standard_2_layer(),
    mounting_holes=[(3,3), (77,3), (3,57), (77,57)],
)

# 2. Declare the circuit (SKiDL-style)
u1 = Part("MCU_Microchip", "ATmega328P-PU", footprint="Package_DIP:DIP-28_W7.62mm")
r1, r2 = 2 * Part("Device", "R", footprint="Resistor_SMD:R_0805_2012Metric")
vcc, gnd, rst = Net("VCC"), Net("GND"), Net("~RESET")
vcc += u1["VCC"], r1[1]
rst += u1["PC6"], r1[2]
gnd += u1["GND"], r2[2]

# 3. Check the electrical graph
ERC()

# 4. Generative layout: try 100 placement+routing combinations, keep the best
result = board.generate(
    trials=100,
    budget="5min",
    cost=lambda t: 100*t.drc_errors + 50*t.unrouted_nets + t.vias + 0.01*t.total_mm,
)

if result.ok:
    board.export_step("board.step")
    board.export_kicad_pcb("board.kicad_pcb")
    board.export_gerbers("gerbers/")
else:
    print(result.why_not())
    # e.g. "7 nets could not be routed on 2 layers — try stackup=4 or board.outline=rect(90,70)"
```

---

## Prerequisites

- FreeCAD ≥ 0.21 (Qt 6 / PySide6)
- Python ≥ 3.10

Upstream still advertises FreeCAD ≥ 0.18 and Python ≥ 2.7, but the procedural/generative redesign drops both. See `frd.md` §9 for the version bump rationale.

## Installation

Until the procedural/generative features land, installation is via the [FreeCAD Addon Manager](https://github.com/FreeCAD/FreeCAD-addons#1-builtin-addon-manager) as with any FreeCAD workbench. Procedural features ship per phase — see `frd.md` §7.

## Status

Design-phase. No procedural/generative code shipped yet; current behaviour matches upstream FreeCAD-PCB (import + view).

## Feedback

Issues and design discussion: file against this fork's repository. Upstream: https://github.com/marmni/FreeCAD-PCB

## Licence

This workbench is distributed under the **GNU Affero General Public License v3.0** (AGPLv3), matching the declaration in `package.xml`. The full licence text is in `LICENSE`; a plain-English summary of obligations and the full third-party attribution list are in `CREDITS.md`.

Upstream's README historically mentioned "LGPL" while `package.xml` declared AGPLv3; this fork resolves the ambiguity in favour of AGPLv3 and has reached out to upstream to confirm. See `CREDITS.md` §1.1.

**Key consequence of AGPLv3:** if you modify this workbench and provide it as a network service, you must offer the modified source to that service's users. Running it locally inside your own copy of FreeCAD does not trigger this clause.

**Planned dual-licensing of the procedural core:** the long-term plan is to release the platform-agnostic procedural logic (`ppcb-core`) under the MIT licence in a separate repository, so the same engine can power other tools. The FreeCAD-specific wrapper stays AGPLv3. See `CREDITS.md` §6 and `qa.md` QD-13.

See `CREDITS.md` for every third-party source and its licence (SKiDL MIT, SQLAlchemy MIT, KiCad libraries CC-BY-SA with instantiation exemption, Hershey fonts public domain, etc.).
