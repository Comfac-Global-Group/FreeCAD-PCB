# FRD — Procedural PCB Workbench for FreeCAD

**Version:** 1.0 draft
**Status:** For review
**Date:** 2026-04-20
**Owner:** Justin / CGG R&D

**Project:** [Philippine OpenEngineering Pipeline](https://sites.comfac.net/freecad.html)  
**Sponsors:** Comfac Technology Group & Cornersteel Systems Corp  
**Mission:** Make the Philippines self-sufficient and innovative in engineering software — and give these tools freely to every Filipino engineer, student, and maker.

**Derived from:**
- `proceedural-pcb.md` — target design (extracted from SKiDL rules + PCB additions)
- `repoanalysis.md` — current state of the FreeCAD-PCB workbench
- `skidl/repoanalysis.md` — reference rules from SKiDL

This document is the **gap-closure plan**: what the FreeCAD-PCB workbench must become, and what has to be built, ported, or rewritten to get there. This module is the **electronics design track** of the broader Philippine OpenEngineering Pipeline, joining BIM/IFC, FEM, CFD, and procedural design modules.

---

## 1. Goal

Transform the FreeCAD-PCB workbench from an **import-viewer** into a **procedural and generative PCB maker** — one where the user supplies:

1. **Physical constraints** (board outline, thickness, stackup, mounting holes, keepouts)
2. **Electrical logic** (parts, pins, nets — the circuit graph)

…and the workbench then **procedurally draws the board** in two phases:

- **Phase A — Feasibility.** Route nets one at a time, in priority order, each obeying its hard rules (DRC clearance, layer assignment, via legality, pad connection) before the next begins. Either ends with a "correct but unoptimised" baseline, or fails fast with a location-specific diagnosis explaining which net couldn't find a legal path and why.
- **Phase B — Optimisation.** Only runs if Phase A succeeded. Takes the feasible baseline, perturbs it across many trials (reorder nets, swap layers, rip up and reroute, adjust vias, anneal), scores each trial, and keeps the best. The baseline acts as a cost floor — Phase B never makes the board worse.

The workbench is not just a Python front-end that emits geometry. It is a **generative layout engine**: it first asks "can this board be built at all?", and only then "what's the best way?". When the answer to the first question is "no", it says so with enough detail to fix the inputs.

### 1.1 User story

A user writes:

```python
from ppcb import *

# 1. Physical envelope
board = Board(
    outline=Sketch.rect(80, 60),
    thickness=1.6,
    stackup=Stackup.standard_2_layer(),
    mounting_holes=[(3,3), (77,3), (3,57), (77,57)],
)

# 2. Circuit logic
u1 = Part("MCU_Microchip", "ATmega328P-PU", footprint="Package_DIP:DIP-28_W7.62mm")
r1, r2 = 2 * Part("Device", "R", footprint="Resistor_SMD:R_0805_2012Metric")
vcc, gnd, rst = Net("VCC"), Net("GND"), Net("~RESET")
vcc += u1["VCC"], r1[1]
rst += u1["PC6"], r1[2]
gnd += u1["GND"], r2[2]

# 3. Electrical check
ERC()

# 4a. Phase A — Feasibility. Deterministic. Routes each net in priority order
#     under hard rules. Either succeeds with a baseline, or fails with a
#     location-specific diagnosis.
feasibility = board.feasibility()

if not feasibility.ok:
    print(feasibility.why_not())
    # e.g. "Net RST could not be routed. Blocked at (42.3, 31.0) on F.Cu by
    #       net VCC. Tried 2 layers, 147 grid cells exhausted.
    #       Suggested fixes:
    #         - Relax netclass SIGNAL clearance from 0.15 to 0.10 mm
    #         - Add inner layer (stackup=4)
    #         - Move part U1 up 3 mm to free the corridor at y=31"
    return

# 4b. Phase B — Optimisation. Starts from the feasible baseline; never worse.
result = board.optimize(
    feasibility.baseline,
    trials=100,
    budget="5min",
    cost=lambda t: t.vias + 0.01 * t.total_mm,
    on_trial=lambda t: print(f"[{t.i}] cost={t.cost:.2f} (best {t.best_cost:.2f})"),
)

# Convenience wrapper that runs both phases in one call:
#   result = board.generate(trials=100, budget="5min")

# 5. Export
board.export_step("board.step")
board.export_kicad_pcb("board.kicad_pcb")
board.export_gerbers("gerbers/")
```

`board.feasibility()` and `board.optimize()` are the primitives. `board.generate(...)` is a convenience wrapper that runs A, then B if A succeeded. Users who want to intervene between phases (inspect the baseline, pin parts, then optimise) use the primitives; users who just want a board use `generate`.

### 1.2 Non-goals

- Not a schematic editor replacement (the Python script *is* the schematic).
- Not an autorouter that beats commercial tools — "good enough to unstick first-pass layout" is sufficient for v1. The generative loop makes up for heuristic weakness with iteration.
- Not a high-speed/RF tuning tool in v1 (defer length-matching and impedance-control beyond Phase 6).
- Not a cloud-collaborative tool.
- Not a guarantee of routability. The trial-and-error engine will try, and if it fails, it will tell the user why — but it does not promise any given circuit can be laid out on any given board.

---

## 2. Scope

### 2.1 In scope (v1)

- Electrical model: Part, Pin, Net, Bus, Circuit, Hierarchy (port from SKiDL).
- Electrical Rules Check (port SKiDL 14×14 conflict matrix).
- Parametric board substrate: outline, holes, cutouts, keepouts, layer stackup (2- and 4-layer).
- Real footprints: load KiCad `.kicad_mod`, validate pin-to-pad mapping, render pads as FreeCAD geometry on the correct copper layers.
- Design Rules Check per netclass: trace width, clearance, via size, annular ring.
- Placer: force-directed, 3D-aware, respects keepouts and rooms.
- Router: layer-aware A\* with via cost and DRC checks.
- **Generative trial-and-error loop** (`board.generate(trials, budget, cost)`): iterate placement + routing variants, score, keep the best, diagnose failure when none succeed.
- **Parameter sweep** (`board.sweep(board_size=..., stackup=...)`): search across physical parameters to find the smallest / cheapest variant that routes.
- Copper pours: plane fills with thermal reliefs.
- Output: STEP (3D), KiCad `.kicad_pcb` (round-trip), Gerbers, BOM CSV, pick-and-place CSV.
- 3D collision check (reuse existing `PCBcollision.py`).

### 2.2 Deferred (v2+)

- Length-matching / serpentine insertion.
- Impedance-controlled widths.
- Differential pairs.
- Rip-up-and-retry routing.
- Push-and-shove interactive edit.
- Flex / rigid-flex boards.
- HDI / microvia stacks.

### 2.3 Explicitly dropped

- Python 2 support (the current codebase straddles 2/3; v2 is Python 3.10+).
- Workbench-internal schematic drawing (users can still use SKiDL and render schematics separately).

---

## 3. Gap Analysis

The following table summarises the delta between today's FreeCAD-PCB (`repoanalysis.md §9`) and the target procedural design (`proceedural-pcb.md`).

| Area | FreeCAD-PCB today | Target (procedural-pcb) | Gap | Decision |
|---|---|---|---|---|
| **Part / Pin / Net primitives** | `partObject` geometry proxy only; no pins; no nets | Full electrical graph with connection operators | 100% | Port from SKiDL |
| **Pin types + drive** | Not present | 14 pin types, 8-level drive enum | 100% | Port from SKiDL verbatim |
| **ERC** | Not present | Full 14×14 matrix + drive check | 100% | Port from SKiDL |
| **Hierarchy (`@subcircuit`)** | Not present | Node-based hierarchy with HIER_SEP="." | 100% | Port from SKiDL |
| **Board outline + holes** | `PCBboardObject` — simple outline + holes + thickness | `Board(outline, thickness, stackup, ...)` primitive | Partial | Extend — add stackup slot |
| **Layer stack** | 17 flat layer types; no dielectric | Ordered stackup with Dk / thickness per layer | 90% | Build new `Stackup` object |
| **Footprint model** | String + linked STEP model; no pads as FreeCAD objects | Real pads on copper layers, pin-to-pad map | 70% | Add `Footprint` loader + pad objects |
| **DRC** | None | Per-netclass trace/clearance/via rules | 100% | Build new engine |
| **Placer** | Manual drag only | Force-directed with rooms and side assignment | 100% | Port SKiDL placer, extend to 3D |
| **Router** | None | Layer-aware A\* with via cost | 100% | Build new (SKiDL's is schematic-only) |
| **Generative loop (trial-and-error)** | None | Run N placement+routing trials, score, pick best, diagnose failure | 100% | Build new — orchestrates placer + router with seeds + budget |
| **Parameter sweep** | None | Search across board size / stackup / grid to find minimal working config | 100% | Build new on top of generative loop |
| **Vias / planes / pours** | None | First-class objects | 100% | Build new |
| **Side assignment** | `Side` property | Same | 0% | Reuse as-is |
| **Parts library (SQLAlchemy)** | Present and working | Needed | 0% | Reuse; extend schema with pin metadata |
| **3D collision check** | `PCBcollision.py` bbox | Same, extended with enclosure STEP | 20% | Extend |
| **Import adapters (Eagle, KiCad…)** | Present — writes geometry directly to FreeCAD | Need to feed procedural model, not geometry | 60% | Refactor each adapter to emit (Part, Net) graph instead of Sketch geometry |
| **Export: STEP** | Present | Present + component-level 3D models | 30% | Extend |
| **Export: KiCad .kicad_pcb** | Lossy per-adapter | Lossless round-trip | 80% | Build new writer |
| **Export: Gerbers** | None | Required | 100% | Build new |
| **Export: BOM** | CSV exporter works | Extend with netclass / footprint columns | 20% | Extend |
| **Parametric `execute()`** | Empty stub everywhere | Every object regenerates geometry on upstream change | 100% | Touch every FeaturePython class |
| **Qt bindings** | PySide (Qt4) | PySide6 (Qt6) | 100% | Port all UI |
| **Tests** | None | Golden-file regression suite | 100% | Build from `examples/*.brd` |

**Headline:** roughly 70% of the workbench is new code; 30% is keep-and-extend.

---

## 4. Architectural Principles

### 4.1 Procedural graph is the source of truth

The Python model (Part/Pin/Net/Circuit graph) is authoritative. FreeCAD document objects are a *view* over it, generated by `execute()` on recompute. Hand edits in the FreeCAD UI update the Python graph, not the other way round.

Rationale: avoids the "two sources of truth" pain that FreeCAD workbenches hit when users edit both the script and the generated geometry.

### 4.2 Everything is parametric

Every scripted object implements a real `execute()` that regenerates its geometry from its properties + the upstream graph. Changing board thickness re-renders; changing stackup re-renders; swapping a footprint re-renders. The current "baked-at-import" model is abandoned.

### 4.3 Reuse SKiDL's electrical semantics

The electrical rules (connection operators, ERC matrix, pin-type semantics, hierarchy model) are ported from SKiDL with minimal changes. The logic is well-tested and battle-hardened; re-deriving it would be a waste.

### 4.4 Replace, don't wrap, SKiDL's router

SKiDL's router targets schematic wires on a single layer, with no via, width, or clearance concept. It is the wrong starting point for a PCB router. We build a new layer-aware A\* router.

### 4.5 Import = geometry + netlist

Existing `formats/*.py` adapters must be refactored to emit a `(Circuit, Board)` pair — the netlist recovered from the file becomes a real `Circuit`, and the geometry becomes a `Board` with placed `Part`s. Today's adapters discard the netlist; v2 must preserve it.

### 4.6 Test with golden files

Every `examples/*.brd` becomes a regression fixture: imported → procedural graph → re-exported → byte-stable (or geometry-stable) across changes.

### 4.7 Feasibility first, optimisation second

Layout is two different problems stacked on top of each other, and the workbench keeps them separate.

- **Feasibility** is a **constraint-satisfaction problem.** Can every net be routed at all, under the hard rules? It has no RNG, no cost function, no perturbation — it's a deterministic per-net router that says "yes, here's a baseline" or "no, here's why not." When Phase A fails, trying 100 Phase B variations won't help; the inputs need to change.
- **Optimisation** is a **search problem.** Given a feasible baseline, what's the cheapest variant? It has RNG, cost, perturbation, parallelism — all the stochastic machinery.

Mixing them is expensive: a monolithic trial loop that restarts from scratch every iteration can spend its entire budget rediscovering that the board is infeasible. Separating them means Phase A fails fast with a useful diagnosis, and Phase B never wastes cycles on infeasible configurations.

A feasibility run is also a **correctness floor** for Phase B — the best-so-far cost starts at the baseline and monotonically improves.

### 4.8 Trial-and-error is a first-class feature, not a hidden implementation detail

Phase B iteration is **explicit and scriptable**:

- `board.optimize(baseline, trials=N, budget=T, cost=f)` is a public API, not an internal retry inside the router.
- Trials are **reproducible** — each carries a seed and full input fingerprint; re-running with the same seed produces the same output.
- Trials are **inspectable** — a failed or sub-optimal trial can be loaded back into FreeCAD for human diagnosis, not discarded.
- Trials are **parallelisable** — each is independent; the loop uses `multiprocessing`.
- Progress is **monotonic** — the feasible baseline is always the worst a Phase B run can end on.

This principle shapes every layer below: the placer must accept a seed; the router must be pausable/cancellable; the DRC must expose structured violation data; footprints must be swappable mid-run.

---

## 5. Functional Requirements

Numbered FR-XXX, grouped by module.

### 5.1 Electrical model (FR-E-xx)

- **FR-E-01** The workbench shall provide `Part`, `Pin`, `Net`, `Bus`, `Circuit` Python classes with the same public surface as SKiDL.
- **FR-E-02** `Part.__mul__` (`2 * Part(...)`) shall produce N independent instances from a template.
- **FR-E-03** Pin/net connection shall support `+=`, `&`, `|`, and `a & b & c` chaining.
- **FR-E-04** `pin += pin` shall route through a (possibly new) Net; direct pin-to-pin has no meaning.
- **FR-E-05** `net += net` shall merge nets (max drive, union netclasses), matching SKiDL's `Net.join()`.
- **FR-E-06** A `Circuit` shall own its Parts/Nets/Buses/NC-net and track the active hierarchy Node.
- **FR-E-07** `@subcircuit` decorator shall push/pop a hierarchy Node around a function body.
- **FR-E-08** Nets shall NOT be scoped to hierarchy (global at Circuit level), matching SKiDL.
- **FR-E-09** The 14 pin types (INPUT, OUTPUT, BIDIR, TRISTATE, PASSIVE, PWRIN, PWROUT, OPENCOLL, OPENEMIT, PULLUP, PULLDN, UNSPEC, NOCONNECT, FREE) shall be available with correct `drive`/`min_rcv`/`max_rcv`.
- **FR-E-10** The active circuit shall be a module-global singleton (`default_circuit`), replaceable per-script.

### 5.2 ERC (FR-R-xx for "rules")

- **FR-R-01** `ERC()` shall run part-level and net-level checks.
- **FR-R-02** Unconnected-pin warning: pin with no net and `func != NOCONNECT`.
- **FR-R-03** Wrongly-connected NOCONNECT: error if a NOCONNECT pin lands on a non-NC net.
- **FR-R-04** Zero-pin net and one-pin net shall be warnings.
- **FR-R-05** No-drivers and insufficient-drive shall be errors.
- **FR-R-06** The 14×14 pin-type conflict matrix from `proceedural-pcb.md §4.3` shall be enforced on every net.
- **FR-R-07** Users shall be able to register custom ERC rules via `circuit.add_erc_function(...)`.
- **FR-R-08** ERC results shall be structured (severity, message, part ref, net name, pin number) not free text.

### 5.3 Board substrate (FR-B-xx)

- **FR-B-01** `Board(outline, thickness, stackup, mounting_holes=None, corner_radius=None)` shall construct a FreeCAD Part::FeaturePython with a parametric 3D extrusion.
- **FR-B-02** `outline` shall accept any FreeCAD Sketch; `Sketch.rect(w, h, corner_radius)` provided as convenience.
- **FR-B-03** `Hole(position, drill, plating=PTH|NPTH)` shall be a first-class child of `Board`.
- **FR-B-04** `Cutout(sketch)` shall subtract from the board.
- **FR-B-05** `Keepout(sketch, layer, rule)` shall enforce its rule during placement and routing.
- **FR-B-06** Changing any `Board` property shall trigger a full recompute via `execute()`.

### 5.4 Stackup (FR-S-xx)

- **FR-S-01** `Stackup` shall be an ordered list of `CopperLayer` and `Dielectric` objects.
- **FR-S-02** `Stackup.standard_2_layer()` and `standard_4_layer()` convenience constructors shall be provided with sensible defaults.
- **FR-S-03** Copper layers shall have: `name`, `thickness`, `role` (signal/plane/mixed), `copper_weight`.
- **FR-S-04** Dielectrics shall have: `thickness`, `Dk`, `loss_tangent`.
- **FR-S-05** Non-copper layers (silk, mask, paste, fab) shall be attached to top and bottom sides regardless of copper count.
- **FR-S-06** Stackup edits shall re-render all pad/trace geometry at correct Z positions.

### 5.5 Footprints (FR-F-xx)

- **FR-F-01** `Footprint.load("Library:Name")` shall open a KiCad `.kicad_mod` file and return a parametric Footprint object.
- **FR-F-02** Footprint shall expose `pads[]` with position, shape, layers, drill (if TH).
- **FR-F-03** Footprint shall expose `courtyard` polygon and `height`.
- **FR-F-04** Footprint shall link to an optional 3D STEP model (reusing existing SQLAlchemy parts library).
- **FR-F-05** Binding a footprint to a Part shall validate that every symbol pin number has a matching pad number; missing maps raise at bind time.
- **FR-F-06** Pad geometry shall be rendered as real FreeCAD objects on the correct copper + silk + mask + paste layers.

### 5.6 DRC (FR-D-xx)

- **FR-D-01** `NetClass(name, trace_width, clearance, via, ...)` shall be assignable per-net.
- **FR-D-02** A default netclass shall apply to nets without an explicit assignment.
- **FR-D-03** `DRC()` shall check, per netclass:
  - (a) track-to-track clearance
  - (b) track-to-pad clearance
  - (c) pad-to-pad clearance
  - (d) hole-to-hole spacing
  - (e) annular ring (via / PTH)
  - (f) minimum drill / trace width
  - (g) silk-over-mask-opening
- **FR-D-04** DRC violations shall be structured: (severity, rule, location xy, layer, offending nets/parts).
- **FR-D-05** DRC shall run during `board.route()` (per-candidate-route check) and again as a final sweep.

### 5.7 Placer (FR-P-xx)

- **FR-P-01** `board.place()` shall position every Part with a footprint.
- **FR-P-02** Placement shall respect: board outline, mounting holes, keepouts, side constraints.
- **FR-P-03** Parts with `position_hint=(x,y)` shall be pulled toward that point as a soft constraint.
- **FR-P-04** Parts with `KeepPosition=True` (reusing the existing property) shall be locked.
- **FR-P-05** A `Room(name, board, x, y, w, h)` context manager shall scope parts to a region.
- **FR-P-06** Placement shall use a force-directed algorithm (attractive net forces + repulsive overlap forces + annealing), 3D-aware (side, height).
- **FR-P-07** Part orientation shall be searched across all 8 rotations/mirrors per side.
- **FR-P-08** A "net tension" cost function shall be exposed so users can plug in alternative placers.

### 5.8 Router (FR-U-xx for "route unit")

- **FR-U-01** `board.route()` shall route every net in the Circuit, respecting DRC.
- **FR-U-02** Routing shall be layer-aware (per the Stackup's copper layers).
- **FR-U-03** Layer transitions shall insert a Via with size/drill from the netclass.
- **FR-U-04** Routing shall be grid-based A\* (grid spacing from netclass).
- **FR-U-05** Nets shall be routed in priority order: power → differential/critical → bus → single-ended.
- **FR-U-06** Unroutable nets shall be reported, not silently skipped, and shall remain visible as rats-nest lines.
- **FR-U-07** The router shall emit real FreeCAD `Part::Feature` traces and vias, not raw Sketch lines.

### 5.9 Pours / planes (FR-C-xx for "copper")

- **FR-C-01** `board.plane(layer, net, split=None)` shall fill an inner copper layer with a net.
- **FR-C-02** Thermal reliefs shall auto-generate at pads on the plane net, with gap/width from the netclass.
- **FR-C-03** `Pour(net, layer, shape, clearance, thermal_relief)` shall cover an arbitrary region.
- **FR-C-04** DRC clearance shall void pour copper around other nets.

### 5.10 Generative layout — Two-Phase Loop (FR-TE-xx)

The headline user-facing feature. It wraps the placer (FR-P), router (FR-U), DRC (FR-D), and pour engine (FR-C) in a two-phase pipeline:

- **Phase A (FR-TE-A-xx)** — Constructive, deterministic, per-net feasibility pass.
- **Phase B (FR-TE-B-xx)** — Stochastic, parallel, iterative optimisation over the feasible baseline.
- **Orchestration (FR-TE-C-xx)** — `generate`, `sweep`, UI, progress reporting.

#### 5.10.A Phase A — Constructive feasibility pass

Phase A is a constraint-satisfaction pass. No RNG, no cost, no retries. It either produces a feasible baseline or fails with a structured diagnosis.

- **FR-TE-A-01** `board.feasibility()` shall run Phase A and return a `FeasibilityResult` with either a feasible `baseline` (a complete `Board` snapshot) or a `why_not()` diagnosis.
- **FR-TE-A-02** Nets shall be routed one at a time in a fixed priority order:
  1. Power rails (nets marked `POWER` class).
  2. Clock / high-speed (nets with `clock=True` or `high_speed=True`).
  3. Differential pairs.
  4. Buses (nets in a `Bus`).
  5. Remaining signal nets (shortest-first within this group as a tiebreaker).
- **FR-TE-A-03** Each net shall be routed under **hard rules only**: trace width from the netclass, min clearance from the netclass, layer legality, annular-ring rule, via rule, keepout respect. No optimisation objectives at this stage.
- **FR-TE-A-04** The per-net router shall be a layer-aware A\* (FR-U-04) with via cost set high enough that planar paths are preferred when available.
- **FR-TE-A-05** On the first net that cannot find any legal path, Phase A shall abort. It shall **not** fall back to "unroute everything and try a different order" — that's Phase B's job.
- **FR-TE-A-06** Phase A shall be **deterministic**: same inputs produce byte-identical output. Any RNG-dependent heuristic is forbidden in Phase A.
- **FR-TE-A-07** `FeasibilityResult.ok == False` shall yield a `why_not()` structure containing, per failed net:
  - The net's name and the pin it was attempting to reach.
  - The last grid cell visited before the search exhausted its frontier (coordinates + layer).
  - Which geometry blocked each attempted expansion (other nets' traces, pads, keepouts, board edge).
  - Which layers were tried and how many cells each exhausted.
  - A ranked list of **suggested fixes**, each with an estimated effect:
    - *"Relax netclass SIGNAL clearance from 0.15 to 0.10 mm"* — estimated from worst observed clearance deficit.
    - *"Add an inner layer (stackup=4)"* — estimated from layer-exhaustion count.
    - *"Move part U1 up 3 mm to free the corridor at y=31"* — estimated from congestion density around pinned geometry.
    - *"Enlarge board outline to 90×70 mm"* — smallest enlargement at which the exhausted frontier reached the destination.
    - *"Reroute net VCC manually first to free this corridor"* — based on blocking-net analysis.
- **FR-TE-A-08** The user shall be able to rerun Phase A with one or more nets **deprioritised or skipped** (`board.feasibility(skip=[net])`), to see if removing a specific net unblocks the rest. Skipped nets are reported as unrouted in the returned baseline but do not cause Phase A to fail.
- **FR-TE-A-09** Phase A output (the feasible baseline) shall be inspectable as a real FreeCAD geometry with all traces and vias rendered. Users can view, edit, or pin the baseline before running Phase B.
- **FR-TE-A-10** Phase A shall have a soft time budget (default 60 s per net, configurable). A net whose A\* exceeds its budget is treated as infeasible with the diagnosis "budget exceeded at corridor (x,y)"; the user can raise the budget and retry.
- **FR-TE-A-11** Phase A diagnostics shall be writable to a JSON report (`feasibility.write_report("why.json")`).

#### 5.10.B Phase B — Iterative optimisation

Phase B only runs if Phase A produced a feasible baseline. It perturbs, scores, keeps the best. Monotonic: the best-so-far never degrades below the baseline.

- **FR-TE-B-01** `board.optimize(baseline, trials, budget, cost, seed=None, on_trial=None, parallel=True)` shall run Phase B and return an `OptimizeResult`.
- **FR-TE-B-02** The feasible baseline is the **cost floor**. If no trial beats the baseline, the baseline is returned unchanged.
- **FR-TE-B-03** Each trial shall produce a `Trial` record: `seed`, elapsed wall-time, perturbation used, DRC errors, unrouted-nets count, via count, total trace length, cost, memory peak, and a `Board` snapshot.
- **FR-TE-B-04** Cost function shall be user-supplied; default: `100 * drc_errors + 50 * unrouted_nets + via_count + 0.01 * total_mm`.
- **FR-TE-B-05** A trial is **successful** iff `drc_errors == 0` and `unrouted_nets == 0`. Any trial that fails to retain feasibility shall be discarded without updating the best-so-far.
- **FR-TE-B-06** Perturbation strategies shall include, combinable per-trial:
  - Net re-ordering within priority classes.
  - Layer reassignment swaps (move a signal net between copper layers).
  - Rip-up-and-reroute of N lowest-cost net segments.
  - Via-position optimisation (slide vias to shorten the chord).
  - Simulated-annealing-style acceptance of worsening moves with decreasing probability.
  - Placer perturbation: nudge unpinned parts, then re-feasibility-route the affected nets (a mini Phase A restricted to a region).
- **FR-TE-B-07** Strategy selection: round-robin across the strategy list by default; user-overridable via `strategies=[...]`.
- **FR-TE-B-08** Seeded reproducibility: `optimize(..., seed=S)` + identical baseline + identical inputs → byte-identical output.
- **FR-TE-B-09** `budget` shall accept an integer (trial count) or duration string (`"5min"`, `"30s"`). Whichever limit is hit first stops the loop.
- **FR-TE-B-10** Cancellable mid-run (FreeCAD button or SIGINT headless); completed trials are preserved, and the best-so-far is the returned result.
- **FR-TE-B-11** Per-trial timeout derived from `budget / remaining_trials`; a pathological trial shall not starve the rest.
- **FR-TE-B-12** Parallelism: `parallel=True` (default) runs trials in independent worker processes via `multiprocessing`. Worker count defaults to `min(cpu_count(), trials)`.
- **FR-TE-B-13** Shared state across workers: read-only `Circuit` graph + `Board` substrate + feasibility baseline. Per-trial state (perturbation RNG, working geometry) lives in the worker.
- **FR-TE-B-14** Early stop: the user may pass `stop_when=lambda best: best.cost < 10` for cost-threshold termination.
- **FR-TE-B-15** `OptimizeResult.trials[]` shall retain all completed trials (cheap-serialised); the user can load any trial back into FreeCAD for human comparison against the best.

#### 5.10.C Orchestration, sweep, and progress UI

- **FR-TE-C-01** `board.generate(trials, budget, cost, seed=None)` shall be a convenience wrapper that calls `board.feasibility()`, then (on success) `board.optimize(...)`. Returns a `GenerateResult` union of both phases.
- **FR-TE-C-02** `GenerateResult.ok` is True iff Phase A succeeded **and** Phase B retained at least the baseline. `.why_not()` returns Phase A diagnostics when Phase A failed; otherwise returns the baseline's residual-cost breakdown.
- **FR-TE-C-03** `board.sweep(**ranges)` shall run `generate` across a Cartesian product of parameter ranges and return a ranked table of (config, feasible?, baseline cost, best cost, trials used). Example:
  ```python
  table = board.sweep(
      outline_size=[(80,60), (90,70), (100,80)],
      stackup=[Stackup.standard_2_layer(), Stackup.standard_4_layer()],
      trials_per_config=20,
      budget_per_config="2min",
  )
  ```
  The table shall identify the minimum-cost **feasible** configuration and, if none is feasible, summarise each configuration's Phase A failure reason.
- **FR-TE-C-04** Sweeps shall parallelise across configurations as well as within each configuration's trials.
- **FR-TE-C-05** Pinning / locked-trace hybrid:
  - Pinned parts (`part.KeepPosition = True`) and locked traces (`trace.locked = True`) are respected by both phases. Phase A routes around them; Phase B never perturbs them.
  - `part.position_hint = (x, y)` is a soft attractor honoured by the placer in both phases.
  - After `generate`, the user can pin parts they like and re-run — Phase A re-routes only the unpinned parts' nets; Phase B re-optimises only the free segments.
- **FR-TE-C-06** Progress callbacks: `on_trial(trial)` invoked after each Phase B trial; additionally `on_feasibility(result)` invoked when Phase A completes.
- **FR-TE-C-07** Dockable FreeCAD "Generate" panel shall show:
  - Phase A progress (per-net: routing / done / failed), with failure diagnosis expandable inline.
  - Phase B progress (trial number, best cost, cost history graph, elapsed vs budget, per-trial counters).
  - Clickable trial rows that load a trial's geometry into the 3D view without disturbing the current best.
- **FR-TE-C-08** Live-draw mode (`live=True`) renders each completed Phase B trial into the 3D view as it finishes. Disabled by default for batch runs; useful for demos and small trial counts.
- **FR-TE-C-09** Non-FreeCAD headless runs (CI, batch): the two-phase loop shall work without an open FreeCAD document; `GenerateResult` shall be fully serialisable to JSON + geometry blob.

### 5.11 Output (FR-O-xx)

- **FR-O-01** `board.export_step(path)` shall emit a 3D STEP of the board with populated components.
- **FR-O-02** `board.export_kicad_pcb(path)` shall emit a `.kicad_pcb` file openable in KiCad pcbnew without loss of nets, footprints, traces, vias, or pours.
- **FR-O-03** `board.export_gerbers(directory)` shall emit RS-274X Gerber files + drill files per industry convention.
- **FR-O-04** `board.export_bom(path)` shall emit CSV with: ref, value, footprint, quantity, net count.
- **FR-O-05** `board.export_cpl(path)` shall emit pick-and-place CSV with: ref, x, y, rotation, side.

### 5.12 Import (FR-I-xx)

- **FR-I-01** Each existing `formats/*.py` adapter shall be refactored to emit a `(Circuit, Board)` pair — not FreeCAD geometry directly.
- **FR-I-02** The KiCad v4/v5 import shall recover: netlist, footprints (as library refs), part positions, routed traces, vias, pours, board outline, stackup (if present).
- **FR-I-03** Importing shall be lossless for KiCad files produced by this workbench's exporter (round-trip fidelity).
- **FR-I-04** Other formats (Eagle, gEDA, etc.) may be lossy on advanced features but must preserve netlist + placement + outline at minimum.

### 5.13 Parametric recompute (FR-X-xx)

- **FR-X-01** Every custom scripted object (Board, Footprint, Trace, Via, Pour, Part, Pin) shall implement a real `execute()` that regenerates geometry.
- **FR-X-02** Recompute shall be topological: upstream changes cascade through dependents.
- **FR-X-03** Recompute shall be incremental where cheap (moving a part re-runs only its footprint extrusion + DRC on nearby routes), full where correctness requires (stackup change → full rebuild).

### 5.14 UI (FR-G-xx)

- **FR-G-01** The workbench shall port to PySide6 (Qt6) to work on current FreeCAD builds.
- **FR-G-02** Existing manual commands (place parts, edit board outline, toggle layers, 3D collision check) shall remain available.
- **FR-G-03** A new "Python Console" shall be prominently available for writing procedural scripts inline.
- **FR-G-04** ERC / DRC / placer / router progress shall be reported in a dockable panel with jump-to-offender links.

### 5.15 Tests (FR-T-xx)

- **FR-T-01** A pytest suite shall live in `tests/`.
- **FR-T-02** Every `examples/*.brd` / `.kicad_pcb` shall be imported and round-tripped; geometry diffs above a tolerance fail CI.
- **FR-T-03** ERC / DRC shall have per-rule unit tests driven by hand-written tiny circuits.
- **FR-T-04** Router shall have deterministic regression tests with fixed seeds.
- **FR-T-05** Golden-file baselines shall be regenerated explicitly, not silently, via a `--regenerate` flag.
- **FR-T-06** The generative loop shall have a deterministic regression test: fixed seed + fixed inputs → fixed best-trial cost. Drift triggers CI failure.
- **FR-T-07** A failure-diagnosis regression shall exist: a known-unroutable circuit (e.g., 20 crossing nets on a 1-layer postage-stamp board) shall produce a specific `why_not()` structure; changes to the diagnosis format fail CI.

### 5.16 Test Design & Validation System (FR-V-xx)

A dedicated testing architecture ensures the workbench produces electrically safe, manufacturable, and mechanically sound boards before any physical prototype is fabricated.

#### Principles

- **Determinism.** Every test with fixed inputs produces byte-identical output. No hidden state, no hardware dependencies, no network calls in the critical path.
- **Isolation.** Unit tests run without FreeCAD GUI head; integration tests may spawn FreeCAD in batch mode; system tests run end-to-end on reference boards.
- **Coverage hierarchy.**
  - *Unit* — individual rules (ERC matrix cells, DRC checks, operator semantics).
  - *Integration* — import → procedural graph → export round-trip.
  - *System* — full `board.generate()` pipeline on reference designs.
  - *Property-based* — random valid circuits must satisfy invariants (e.g., "no net has zero pins after ERC").
  - *Safety* — deliberately dangerous circuits must be caught before export.
- **Golden-file regression.** Every reference board has a known-good geometry fingerprint. Changes that alter the fingerprint fail CI unless `--regenerate` is passed.
- **Falsifiability.** Every test must be capable of failing. A test that cannot fail provides no information.

#### Key Focus Areas

| Focus | What is validated | Example failure mode |
|---|---|---|
| **Electrical safety** | Nets, pins, ERC, power sequencing | Short circuit between VCC and GND; unconnected reset pin |
| **Manufacturing correctness** | DRC, clearances, annular rings, drill hits | Trace narrower than netclass minimum; drill overlaps copper |
| **Thermal safety** | Current capacity per trace/via, copper area | 2A through a 0.1mm trace → fire risk |
| **Mechanical integrity** | 3D collision, enclosure fit, mounting holes | Connector body intersects enclosure wall |
| **Algorithmic correctness** | Router determinism, placer convergence, cost monotonicity | Phase B returns a higher-cost trial than baseline |

#### PCB Circumstance Test Matrix

The validation system shall include explicit test fixtures for the following real-world PCB failure modes:

**Conductive faults**
- **FR-V-01** *Net-to-net short* — two distinct nets merged by an overlapping trace or pad placement; DRC must flag with location and offending nets.
- **FR-V-02** *Power-rail short* — VCC and GND nets electrically connected; ERC must report pin-type conflict (PWRIN ↔ PWROUT at ERROR severity).
- **FR-V-03** *Pin-to-pin short* — adjacent pins on the same footprint bridged by solder or copper; DRC must check pad-to-pad clearance.
- **FR-V-04** *Via barrel short* — via drill too large, breaks isolation between layers; DRC annular-ring + minimum-via checks must catch.
- **FR-V-05** *Plane pour short* — copper pour flows into an unconnected pad because thermal relief is missing or clearance is violated.

**Open-circuit faults**
- **FR-V-06** *Broken trace* — trace segment removed or never generated; router must ensure every net is fully connected or explicitly reported as unrouted.
- **FR-V-07** *Missing via* — layer transition attempted but no via placed; DRC must detect discontinuous nets.
- **FR-V-08** *Unconnected pin* — pin left on NC net despite not being marked NOCONNECT; ERC must warn.

**Thermal & power faults**
- **FR-V-09** *Undersized trace for current* — net carrying >1A routed with 0.2mm trace on 1oz copper; thermal calculator must warn (v2 feature, v1 should document limitation).
- **FR-V-10** *Via current starvation* — single via carries high current; DRC should recommend via stitching (v2).
- **FR-V-11** *Ground loop / split plane* — ground plane interrupted by routing, creating return-path loops; DRC should warn on plane continuity (v2).

**Manufacturing & assembly faults**
- **FR-V-12** *Drill hits trace* — drill center too close to copper; DRC hole-to-copper clearance check.
- **FR-V-13** *Silk over exposed pad* — silkscreen polygon overlaps solder-mask opening; DRC silk-over-mask check.
- **FR-V-14** *Wrong footprint orientation* — polarized component (diode, electrolytic cap) placed backwards; ERC/DRC cannot catch this directly, but pick-and-place output must preserve orientation metadata for manual review.
- **FR-V-15** *Missing polarity mark* — silkscreen lacks polarity indicator on polarized footprint; footprint loader should warn if .kicad_mod is missing standard polarity graphics.

**Test Harness Architecture**

- **FR-V-16** `board.validate()` shall run ERC + DRC + 3D collision + circumstance checks in one call, returning a structured `ValidationReport`.
- **FR-V-17** `ValidationReport` shall contain: `{severity, category, rule_id, message, location_xy, layer, parts[], nets[], suggested_fix}`.
- **FR-V-18** The validation harness shall be scriptable without FreeCAD GUI (`--headless` mode).
- **FR-V-19** Every circumstance test (FR-V-01..15) shall have a hand-crafted fixture board that intentionally contains the fault, plus an identical "fixed" board that passes validation. CI diffs the two reports to ensure the fault is caught.

### 5.17 Bill of Materials & Procurement (FR-M-xx)

Beyond simple CSV export, the workbench shall manage parts data, source alternates, and generate quotations.

#### BOM Management

- **FR-M-01** `board.bom()` shall return a structured BOM object (not just a flat CSV).
- **FR-M-02** BOM entries shall contain: ref, value, footprint, manufacturer, MPN, quantity, side (TOP/BOTTOM), DNP flag, alternate parts list.
- **FR-M-03** Users shall be able to annotate parts with supplier metadata: `r1.mpn = "RC0603JR-0710KL"`, `r1.manufacturer = "Yageo"`, `r1.dnp = True`.
- **FR-M-04** The BOM shall group identical parts (same MPN or same value+footprint when MPN is absent) and report total quantity.
- **FR-M-05** The BOM shall respect DNP (do-not-populate) flags: DNP parts appear in the BOM but are excluded from pick-and-place and cost totals.

#### Price Lookup & Quotation

- **FR-M-06** `board.quote(sources=["digikey","mouser","lcsc"])` shall fetch live or cached pricing for each BOM line from configured distributors.
- **FR-M-07** Price lookup shall support API keys per distributor, stored in user config (never committed to repo).
- **FR-M-08** For each line, the quotation shall report: unit price at qty 1, unit price at BOM qty, unit price at 100/500/1000 qty breakpoints, stock status, MOQ, lead time.
- **FR-M-09** The quotation engine shall support alternate MPN fallback: if primary MPN is out of stock or exceeds budget, suggest the next alternate from the part's alternate list.
- **FR-M-10** `board.quote()` shall return a `Quotation` object with: per-line breakdown, total BOM cost at actual qty, total BOM cost at 100/500/1000 qty, cheapest source per line, and a "single-source" risk flag (when >50% of value comes from one distributor).

#### Export Formats

- **FR-M-11** `board.export_bom(path, format="csv")` — CSV with standard columns (ref, value, footprint, MPN, manufacturer, qty, side, DNP).
- **FR-M-12** `board.export_bom(path, format="json")` — Full structured BOM including alternates and supplier metadata.
- **FR-M-13** `board.export_bom(path, format="xlsx")` — Excel with separate sheets: BOM, Alternates, DNP list, Cost summary.
- **FR-M-14** `board.export_quote(path, format="pdf")` — Human-readable quotation PDF for purchasing.
- **FR-M-15** `board.export_quote(path, format="csv")` — Machine-readable quotation for ERP ingestion.

#### Offline / Cached Mode

- **FR-M-16** Price data shall be cacheable locally (`~/.cache/ppcb/prices.json`) so quotations can be regenerated without network access.
- **FR-M-17** Users shall be able to override prices manually: `r1.unit_price = 0.05` bypasses live lookup for that line.
- **FR-M-18** A "dry-run" mode shall generate a quotation using cached / manual prices only, without network calls.

---

## 6. Reuse Decisions

Per `repoanalysis.md §11`:

### 6.1 Keep and extend

- `PCBboardObject` — foundation for `Board`; extend with `Stackup` slot.
- Parts library (`PCBdataBase.py`, `PCBpartManaging.py`, SQLAlchemy schema) — extend schema with pin/pad metadata.
- `constraintAreaObject` — foundation for `Keepout`.
- `PCBcollision.py` — extend for 3D cuboid with height.
- Kerkythea / POV-Ray / STEP export — keep.
- Command-registration scaffolding (`InitGui.py`, `PCBcommands.py`, `PCBtoolBar.py`) — keep but migrate to PySide6.

### 6.2 Port from SKiDL

- Core object model (Part, Pin, Net, Bus, Circuit) — `src/skidl/{part,pin,net,bus,circuit}.py`.
- ERC engine — `src/skidl/erc.py` + pin conflict matrix in `src/skidl/pin.py`.
- Connection operators — already in the ported files above.
- Hierarchy — `src/skidl/node.py` + `@subcircuit` decorator in `circuit.py`.
- Force-directed placer (extend to 3D) — `src/skidl/schematics/place.py`.

### 6.2b Licence boundary (see `CREDITS.md` and `qa.md` QD-13)

- **Decision (2026-04-20):** The entire project is AGPLv3. There is no separate MIT-licensed procedural core.
- Code ported from SKiDL (MIT) is redistributed here under AGPLv3, retaining the original MIT header and Dave Vandenbout's copyright notice.
- KiCad symbol / footprint / 3D-model libraries (CC-BY-SA 4.0 with instantiation exemption) are **loaded from the user's install at runtime**, never bundled or redistributed.
- Every new source file created in this fork carries `# SPDX-License-Identifier: AGPL-3.0-or-later`.

### 6.3 Build new

- Stackup model.
- Footprint loader (KiCad `.kicad_mod`).
- DRC engine.
- Layer-aware A\* router.
- **Generative trial-and-error loop** (`board.generate`, `board.sweep`) — orchestrates placer + router + DRC + pour with seeds, budget, parallel workers, and structured failure diagnosis.
- **Failure-diagnosis engine** — turns raw DRC/unrouted-net data into ranked suggested fixes.
- Pour / thermal-relief engine.
- KiCad `.kicad_pcb` writer.
- Gerber writer.
- Parametric `execute()` implementations on every scripted object.

### 6.4 Drop

- Python 2 compatibility shims.
- `checkCompatibility` disabled guard — reinstate with real version check.
- Vendored SQLAlchemy (move to pip dependency).

---

## 7. Phased Delivery

Eight phases. Estimated in weeks by 1 engineer; half that with two.

| Phase | Scope | FRs in phase | Weeks |
|---|---|---|---|
| **P0 — Foundations** | Py3-only, PySide6 port, split monolithic files, pytest baseline, golden-file framework, drop Py2 shims | FR-G-01, FR-T-01, FR-T-02 | 3 |
| **P1 — Electrical core** | Port SKiDL core (Part/Pin/Net/Bus/Circuit/hierarchy) + ERC matrix | FR-E-*, FR-R-* | 3 |
| **P2 — Board + Stackup + Footprints** | `Board` with parametric `execute()`, `Stackup`, `Footprint.load()`, pad rendering, pin-to-pad validation | FR-B-*, FR-S-*, FR-F-*, FR-X-* | 4 |
| **P3 — Placer** | Force-directed 3D-aware placer with rooms, hints, side assignment | FR-P-* | 2 |
| **P4 — Router + DRC** | Layer-aware A\* router, netclass-driven DRC, via insertion | FR-U-*, FR-D-* | 4 |
| **P5a — Phase A (feasibility)** | Constructive per-net router, priority ordering, deterministic output, structured `why_not` with ranked suggested fixes, `board.feasibility()` API, skip-net diagnostic mode | FR-TE-A-* | 2 |
| **P5b — Phase B (optimisation)** | Perturbation strategies (reorder / layer-swap / rip-up / SA), cost-floor monotonicity, seeded reproducibility, parallel workers, per-trial timeout, `board.optimize()` API | FR-TE-B-* | 2 |
| **P5c — Orchestration + UI** | `board.generate` wrapper, `board.sweep` parameter sweep, dockable progress panel, live-draw mode, pinning + locked-trace hybrid, JSON report export | FR-TE-C-* | 2 |
| **P6 — Pours + planes** | Plane fills, thermal reliefs, pour around clearance | FR-C-* | 2 |
| **P7 — Import refactor** | Rewrite KiCad v4/v5 adapter to emit `(Circuit, Board)`; preserve netlist; Eagle/gEDA as time permits | FR-I-* | 3 |
| **P8 — Output** | STEP + KiCad round-trip + Gerbers + BOM + CPL | FR-O-* | 3 |
| **P9 — Polish** | Progress panels, jump-to-offender, docs, example boards in Python, release | FR-G-* | 2 |

**Total:** 31 engineer-weeks for one person; realistically 7-10 calendar months.

**Minimum viable demo:** P0 + P1 + P2 (10 weeks) — user can write a Python script that produces a 2-layer board with correct outline, stackup, footprints, and ERC. Routing is still manual / KiCad-side. That alone would be a useful tool.

**The "feasibility" demo:** P0 + P1 + P2 + P3 + P4 + P5a (18 weeks) — `board.feasibility()` returns a DRC-clean baseline for a simple circuit, or a structured diagnosis with ranked suggested fixes when it can't. At this point the workbench is already more useful than any interactive router because it tells the user *why* a board won't route.

**The "it's actually generative" demo:** add P5b + P5c (22 weeks total) — `board.generate(trials=100, budget="5min")` runs both phases and returns an optimised board. Parameter sweeps find the smallest board that works. This is the v1 headline and the point at which the workbench becomes meaningfully different from everything else in the FreeCAD ecosystem.

---

## 8. Acceptance Criteria (v1)

The workbench ships v1 when all of the following are true:

1. A user can write the "user story" script in §1.1, run it from FreeCAD's Python console, and see a correct 3D board.
2. `ERC()` on a hand-written wrong-connection test circuit produces the expected errors matching SKiDL's output exactly.
3. `DRC()` on a board with a known clearance violation reports the violation with correct coordinates.
4. `board.route()` (deterministic, single-shot) on a 20-net trivial board (e.g., a flasher LED circuit) produces a routable board with zero DRC errors.

   **Phase A — Feasibility**

5. **`board.feasibility()` on the 20-net flasher board returns a DRC-clean baseline in under 30 seconds of wall time.** The baseline is byte-identical across re-runs (deterministic).
6. **`board.feasibility()` on a deliberately-infeasible circuit (20 crossing nets on a 20 × 20 mm 1-layer postage stamp) returns `ok=False` with a `why_not()` that:** (a) names the specific net that failed, (b) gives the coordinate + layer where A\* exhausted its frontier, (c) names the blocking geometry (nets, pads, keepouts, board edge), (d) lists at least two ranked suggested fixes each with an estimated effect.
7. **`board.feasibility(skip=[one_net])` on the same infeasible circuit successfully routes the remainder and reports the skipped net cleanly.**

   **Phase B — Optimisation**

8. **`board.optimize(baseline, trials=100, budget="5min")` starting from the feasibility baseline produces a result whose cost is ≤ baseline cost** (monotonicity — Phase B never degrades the board).
9. **The same `board.optimize(...)` run on the 20-net flasher board converges to a best-trial cost within 15 % of a human-routed reference.**
10. **Phase B determinism:** `board.optimize(..., seed=42)` returns byte-identical geometry across re-runs with identical baseline and inputs.

    **Orchestration**

11. **`board.generate(trials=100, budget="5min")` on the 20-net board runs Phase A then Phase B and returns a DRC-clean result in under 5 minutes wall-time on a modern laptop.**
12. **`board.sweep(outline_size=[(80,60),(90,70),(100,80)], stackup=[2,4])` on a 40-net circuit returns a ranked table and correctly identifies the smallest board + thinnest stackup that is *feasible* (Phase A succeeds) and has the lowest Phase B cost.**
13. The FreeCAD dockable "Generate" panel shows live progress through both phases, lets the user cancel mid-run without losing completed trials, and lets them click any trial row to load its geometry into the 3D view.

    **Outputs and interoperability**

14. `board.export_kicad_pcb()` → open in KiCad pcbnew → KiCad's built-in DRC passes with zero errors.
15. `board.export_gerbers()` → load in a Gerber viewer → all layers align; drill holes match copper pads.
16. Importing `examples/test_simple.brd` produces an equivalent procedural Circuit whose re-export matches the original within geometry tolerance.
17. Unit-test suite passes in CI on Python 3.10 + FreeCAD ≥ 0.21 with PySide6.

---

## 9. Out-of-Scope (explicit)

- High-speed analysis (impedance, crosstalk, EM simulation).
- Panelisation.
- Assembly drawings / fabrication drawings.
- Schematic GUI editor.
- Cloud / multi-user collaboration.
- Spice co-simulation (though procedural model could feed SKiDL's `pyspice.py` in future).

---

## 10. Success Metrics

Once v1 ships, track:

- Time from empty Python script to Gerbers generated, for a 10-part board (target: ≤ 30 minutes for a first-time user).
- Percentage of `examples/*.brd` that import → Circuit → re-export cleanly (target ≥ 80% at v1.0, ≥ 95% at v1.5).
- KiCad round-trip fidelity: percentage of KiCad reference boards that survive import/export byte-stable (target ≥ 50% at v1.0).
- Router success rate on community-contributed test boards (target ≥ 80% of nets routed without manual intervention at v1.0).

---

## 11. Open Questions

Answered questions move here; unanswered ones live in `qa.md`.

See `qa.md` for the current list.

---

*End of FRD. Companion docs: `repoanalysis.md` (current state), `proceedural-pcb.md` (target rules), `qa.md` (open questions + QA plan).*
