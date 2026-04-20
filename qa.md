# QA — Open Questions and Verification Plan

**Version:** 1.0 draft
**Date:** 2026-04-20
**Companion docs:** `proceedural-pcb.md` (target rules), `repoanalysis.md` (current state), `frd.md` (functional requirements).

This doc has two purposes:

1. **Design questions** that must be settled before (or during) implementation — each with options, trade-offs, and a recommendation where one exists.
2. **Verification plan** — the concrete test strategy to prove the workbench behaves correctly at each phase of `frd.md §7`.

---

## Part 1 — Open Design Questions

Numbered QD-XX (question, design). Each has a proposed answer; revisit before the phase that needs it.

---

### QD-01 — Source of truth: Python graph or FreeCAD document?

**Question:** When a user hand-edits a part position in the FreeCAD 3D view, does the Python circuit graph update, or is the hand-edit a local override?

**Options:**

- **(A) Python graph is authoritative.** Hand edits write back into the graph (stored as a JSON blob in the FCStd file, re-run on open).
- **(B) FreeCAD document is authoritative.** The Python graph only exists during script execution; afterwards, the document is canonical.
- **(C) Hybrid.** Graph is authoritative for topology (nets, parts, pins). FreeCAD document owns placements as "overrides" layered on top.

**Recommendation:** **(C).** Matches user expectation — re-running the script shouldn't destroy their hand-placed parts, but adding a new `Part()` to the script should appear on the board.

**Implementation sketch:** store the procedural source (JSON of Part/Net structure) on the Board object; store placement overrides per Part; on re-run, merge overrides back in, warn if a Part the override referenced no longer exists.

---

### QD-02 — Netlist-first or geometry-first?

**Question:** Does the user describe the circuit (nets, parts) and let the workbench generate geometry, or does the user draw geometry (pads, traces) and let the workbench infer netlists?

**Recommendation:** **Netlist-first** for v1. It matches SKiDL, matches the procedural-pcb design, and matches how every serious PCB tool works. Geometry-first is a v2+ "reverse-engineer a board from Gerbers" feature.

---

### QD-03 — Routing strategy

**Question:** Which routing algorithm?

**Options:**

- **(A) Grid-based A\*** per layer with via cost. Simple, deterministic, slow on large boards.
- **(B) Topological (line-expansion / shapely).** Faster, handles arbitrary shapes, more complex to write.
- **(C) Rip-up-and-retry.** Routes in priority order; if a net is blocked, rip up lower-priority nets and try again. Needed for dense boards.
- **(D) Hybrid global + detail.** Global router finds layer assignments and rough paths (fast); detail router places tracks.

**Recommendation:** Start with **(A) grid A\* with simple rip-up** at v1. Plan **(D)** for v2 when dense boards arrive.

---

### QD-04 — Grid resolution

**Question:** What grid for the router to use? Finer = better routing, slower.

**Options:** 0.1 mm (industry common), 0.127 mm (5 mil — imperial heritage), 0.05 mm (fine-pitch), per-netclass (mixed).

**Recommendation:** **0.1 mm default**, user-overridable per-board and per-netclass. Imperial 5-mil (0.127 mm) offered as preset.

---

### QD-05 — Copper pour algorithm

**Question:** How to generate copper pours with clearance and thermal reliefs?

**Options:**

- **(A) Polygon offset (shapely `buffer`).** Start with the pour region, subtract clearance around every other-net object, add thermal reliefs around same-net pads.
- **(B) Distance-field raster.** Render everything to a pixel grid at pour resolution, flood-fill, re-polygonise.
- **(C) Use KiCad's pour engine via pcbnew Python.** Delegate.

**Recommendation:** **(A).** Shapely is well-tested, Python-native, produces clean polygons. KiCad delegation (C) is tempting but couples us to pcbnew runtime.

---

### QD-06 — Footprint provenance

**Question:** Where do footprints come from at v1?

**Options:**

- **(A) KiCad footprint libraries (.kicad_mod).** User points workbench at their KiCad library paths; we load on demand.
- **(B) Bundle our own.** Ship a curated subset.
- **(C) Build a registry service.** Fetch over the network.

**Recommendation:** **(A).** Every target user has KiCad installed. Bundling is redundant; a registry service is a product in itself.

---

### QD-07 — 3D component models

**Question:** How to populate the board with 3D STEP models of components?

**Options:**

- **(A) Reuse `PCBpartManaging.py` + SQLAlchemy DB.** Keep today's infrastructure.
- **(B) Use KiCad's `ki_3dmodel` references.** Each footprint declares its 3D model path; we resolve it.
- **(C) Both.** Prefer (B); fall back to (A) for custom parts not in KiCad libraries.

**Recommendation:** **(C).**

---

### QD-08 — Stackup defaults

**Question:** What stackup does `Board()` get if the user doesn't specify one?

**Recommendation:** 2-layer, 1.6 mm FR4, 35 µm (1 oz) copper. Matches industry default for hobby/prototyping. `Stackup.standard_4_layer()` available as a one-liner upgrade.

---

### QD-09 — Reference designator auto-assignment

**Question:** When the user creates `r1 = Part("R")` without setting `.ref`, what's R1?

**Options:**

- **(A) Creation order.** R1 = first R created, R2 = second.
- **(B) Placement order.** Assign after placement, top-left to bottom-right.
- **(C) User choice.** Flag on Circuit.

**Recommendation:** **(A) at creation, (B) at post-placement renumber.** Users expect stable refs during development; final board uses positional numbering. Provide `circuit.renumber_by_position()`.

---

### QD-10 — Error reporting shape

**Question:** How are ERC / DRC errors surfaced?

**Recommendation:** Structured list of `{severity, rule_id, message, location?, parts?, nets?}`. Dockable FreeCAD panel lists them; double-click jumps to the offender in the 3D view. JSON export for external consumption.

---

### QD-11 — PySide / Qt version

**Question:** Which Qt binding?

**Recommendation:** **PySide6 (Qt 6).** Current FreeCAD releases ship with Qt 6. Today's FreeCAD-PCB uses PySide (Qt 4) — broken on modern builds. No backward compatibility with Qt 4/5 in v1.

---

### QD-12 — Python version

**Recommendation:** **Python 3.10+** hard minimum. Drop all Py2/3 straddle code. FreeCAD ships 3.11 on current releases.

---

### QD-13 — Licensing

**Question:** Licence of the new code and the procedural core?

**Status of upstream (as of 2026-04-20):** `package.xml` declares **AGPLv3**, `README.md` historically said "LGPL", and no `LICENSE` file was committed. This fork resolved the ambiguity in favour of `package.xml` — AGPLv3 — and committed the canonical AGPL-3.0 text to `LICENSE`. A request to upstream `@marmni` for formal confirmation is outstanding (tracked in `CREDITS.md` §7).

**Options:**

- **(A) Keep AGPLv3 for everything.** Matches upstream package.xml. Strong copyleft; anyone offering the workbench as a network service must offer source.
- **(B) Relicense fork to LGPL-3.** Only legally possible with permission from every upstream copyright holder; impractical without contacting each contributor.
- **(C) Relicense fork to GPL-3.** Same legal obstacle as (B).
- **(D) Dual-licence: AGPL wrapper + MIT core.** This workbench stays AGPLv3 (inheriting upstream). The platform-agnostic procedural logic (Part/Pin/Net/ERC/DRC/placer/router with no FreeCAD dependency) is extracted into a **separate repo** `ppcb-core` under MIT. Other tools (Blender, KiCad plugins, web) can reuse the core without AGPL obligations.

**Decision (2026-04-20):** **(A) — Keep AGPLv3 for everything.** The project owner prefers AGPLv3 over dual-licensing. The procedural core will remain AGPLv3 and live in-tree; there is no separate MIT-licenced `ppcb-core` package. All code in this repository, including any procedural engine extracted later, is AGPLv3.

~~**Recommendation:** ~~(D)~~.~~ ~~This is the only option that is both (a) legally tractable without upstream relicensing cooperation and (b) gives the procedural engine the broadest reach.~~

~~**Implementation constraint:** `ppcb-core` must be a physically separate repository / pip package. No AGPL-licensed code (including *any* derivative of upstream FreeCAD-PCB code) may enter `ppcb-core`. Contributors to `ppcb-core` sign a simple DCO affirming MIT. Code shared between the two repos flows **one direction only**: MIT core → AGPL wrapper, never the reverse.~~

**Can AGPLv3 be downgraded to GPLv3 after-the-fact?** No — not unilaterally. AGPLv3 grants users a right (source availability on network use) that GPLv3 does not. Removing that right requires every copyright holder's consent. What **is** permitted without consent: combining AGPLv3 code with GPLv3 code in one project (per AGPLv3 §13); the combined work remains effectively AGPLv3.

---

### QD-14 — Dependency on pcbnew / KiCad Python

**Question:** Does the workbench require KiCad's Python module at runtime?

**Recommendation:** **No.** KiCad round-trip via our own `.kicad_pcb` parser/writer. Users should be able to run this workbench without KiCad installed. Optional integration (e.g., "open this board in KiCad") can delegate, but must not be a hard dependency.

---

### QD-15 — Interactive vs batch routing

**Question:** Can users route a single net interactively, or only via `board.route()` for all nets?

**Recommendation:** **Batch at v1, interactive at v2.** Interactive routing (push-and-shove) is a substantial project on its own.

---

### QD-16 — Handling of user hand-routed traces

**Question:** If a user hand-draws a trace in FreeCAD, what happens on next `board.route()`?

**Recommendation:** Hand-routed traces are **locked by default** (`locked=True` on the Trace object). Autoroute skips locked traces and routes around them. User can explicitly unlock for re-routing.

---

### QD-17 — Multi-board / panel support

**Question:** Support multiple boards in one FreeCAD document?

**Recommendation:** **v1: single board per document.** Panelisation is deferred.

---

### QD-18 — Units

**Question:** mm or mil internally?

**Recommendation:** **mm internally**, matching FreeCAD's default. User-facing inputs accept both. KiCad v5+ uses mm natively; KiCad v4 uses mil internally but we import and normalise.

---

### QD-19 — Performance target

**Question:** How big a board must the workbench handle at v1?

**Recommendation:** **≤ 500 nets, ≤ 1000 parts, 2-4 layer** boards must route in < 10 minutes on a modern laptop. Larger boards are v2 performance work.

---

### QD-20 — Incremental recompute

**Question:** On every property change, do we recompute the whole board?

**Recommendation:** **No.** Topological recompute via FreeCAD's dependency graph; only affected geometry is regenerated. Moving one part should re-render only its footprint + re-check nearby DRC, not re-route the board.

---

### QD-21 — Phase A diagnostic granularity

**Question:** How detailed must `feasibility.why_not()` be?

**Options:**

- **(A) Coarse.** "Net X failed to route."
- **(B) Medium.** "Net X failed at (42, 31), layer F.Cu. Blocked by nets [VCC, GND]."
- **(C) Fine.** As (B) plus: which layers were tried, how many A\* cells were exhausted each time, a ranked list of suggested fixes with estimated effects.
- **(D) Exhaustive.** As (C) plus: an image / 3D preview showing the congestion region; a replay of the last 50 A\* expansions before failure.

**Recommendation:** **(C) for v1, (D) as opt-in** via `why_not(verbose=True)`. (C) is what's captured in FR-TE-A-07; it's enough to act on without being expensive to generate. Exhaustive mode is a debugging aid, not a default.

**Why it matters:** a vague diagnosis is useless — the user goes back to guessing. An over-detailed diagnosis buries the actionable advice. "Here are the three things you could change, ranked" is the sweet spot.

---

### QD-22 — Phase A priority order: fixed or configurable?

**Question:** FR-TE-A-02 fixes the net priority order (power → clock → differential → bus → signal). Should the user be able to override it?

**Options:**

- **(A) Fixed.** Simplest; matches routing convention.
- **(B) Per-net priority field.** Users annotate `net.priority = 5`; the router sorts by it.
- **(C) Full pluggable ordering.** User supplies `priority_fn(net) -> float`.

**Recommendation:** **(B).** Per-net integer priority with sensible class defaults. Power nets default to priority 10, signal to priority 0; users can bump a critical signal to 8 without losing the default structure. (C) is over-engineered for v1.

---

### QD-23 — When Phase A fails, does Phase B still run?

**Question:** If the user calls `board.generate()` (the convenience wrapper) and Phase A fails, should Phase B run on the partial baseline (routed-so-far) to try to optimise what was achieved?

**Options:**

- **(A) Hard stop.** Phase A fails → return immediately with diagnosis. Phase B never runs.
- **(B) Best-effort Phase B.** Phase B runs on the partial baseline, may rearrange to help the failed net route.
- **(C) User choice.** `generate(..., on_feasibility_fail="stop" | "optimize")`.

**Recommendation:** **(A) as default, (C) for advanced users.** The whole point of the two-phase separation (principle §4.7) is that Phase B is not a fix for infeasibility. If the user genuinely wants Phase B to try anyway, let them say so explicitly — it's an escape hatch, not a default.

---

### QD-24 — Phase B perturbation budget per trial

**Question:** How aggressive should each Phase B trial be? Move one net, or rip up half the board?

**Recommendation:** **Start small, expand with iteration.** Trial 1-10: single-net perturbation. Trial 11-30: small cluster (5 nets). Trial 31+: region-level rip-up. This is standard simulated-annealing schedule behaviour — small moves explore near the baseline, larger moves escape local minima. Expose as a `schedule` parameter but ship a sensible default.

---

### QD-25 — Mini-Phase-A inside Phase B

**Question:** FR-TE-B-06 mentions "placer perturbation: nudge parts, then re-feasibility-route the affected nets." This is a mini Phase A restricted to a region. Should this be a full documented primitive?

**Options:**

- **(A) Internal only.** Implement it inside Phase B; not exposed.
- **(B) Public API.** `board.refeasibility(region=bbox, nets=[...])` as a primitive.

**Recommendation:** **(A) for v1.** It's useful internally but exposing it creates a lot of configuration surface. Revisit after v1 ships if users ask for it.

---

## Part 2 — Verification Plan

Structured QV-XX (question, verification).

### QV-01 — Golden-file regression suite

Every `examples/*.brd` and `examples/*.emn` is a regression fixture.

**Procedure:**

1. Import → procedural `(Circuit, Board)` graph.
2. Serialise to JSON fingerprint (topology: parts, nets, connections; geometry: bbox + hash of each copper layer).
3. Store fingerprint as `tests/golden/<example_name>.json`.
4. On every CI run, re-import and compare fingerprints.
5. Geometry tolerance: 0.001 mm for positions; exact for netlist.

Failing diffs should be human-readable — "Net 5 `VCC` has 12 pins, expected 11" / "Trace on layer F.Cu moved 0.003 mm" — not byte diffs of JSON.

### QV-02 — ERC unit tests

One test per rule in the ERC matrix. For each of the 14×14 pin-type pairs:

1. Build a two-part circuit with those pin types on a shared net.
2. Run `ERC()`.
3. Assert severity (OK / WARNING / ERROR) matches the matrix.

Plus one test each for:

- Unconnected-pin warning.
- NOCONNECT-wrongly-connected error.
- Zero-pin net warning.
- One-pin net warning.
- No-drivers error.
- Insufficient-drive error (pin.min_rcv > net.drive).

### QV-03 — DRC unit tests

One test per DRC rule (FR-D-03 a–g):

- Board with two traces exactly at min-clearance: pass.
- Two traces one micron closer than clearance: fail with correct coordinates.
- Via with annular ring just under rule: fail.
- Silk line crossing mask opening: fail.
- Drill under minimum: fail.

### QV-04 — Connection-operator semantics

One test per operator against SKiDL's expected behaviour:

- `pin += net` — pin on net, net's _pins list contains pin.
- `net += pin1, pin2` — both pins attached.
- `net1 += net2` — merged; drive = max(drives); netclasses unioned.
- `a & b & c` — chain connects a.out→b.in and b.out→c.in.
- `a | b` — shared in and out.
- `net += pin_from_other_circuit` — raises CircuitMismatch.
- `net += NC_net` — raises (cannot merge with NC).

### QV-05 — Hierarchy scoping

- `@subcircuit` function called twice produces two independent sub-nodes with distinct `hiername`s.
- Net created inside subcircuit is visible at Circuit level (nets are NOT scoped).
- Part created inside subcircuit has correct dot-path hiername.
- Nested `@subcircuit` produces `parent.child.leaf` hiername.

### QV-06 — Parametric recompute

- Create board; change `thickness`; assert every Part's Z position updates and the board mesh regenerates.
- Change stackup copper-layer thickness; assert pad geometry re-extrudes.
- Swap a footprint on a part; assert new pads appear, old removed.
- Add a new Net; assert it appears in exports without re-importing.
- Remove a Part; assert its footprint geometry + references from nets are cleanly removed.

### QV-07 — Router regression

Fixed-seed deterministic router tests:

- Trivial 2-part 1-net board: routes successfully, one trace.
- 555 timer circuit: routes successfully, DRC clean.
- 74LS00 quad-NAND: routes successfully.
- Impossible-route test: two nets requiring a crossing on a 1-layer board — router reports failure cleanly with location.
- Via-cost test: net that would need 3 vias on a noisy grid — router picks 0-via path when available.

Each test asserts: (a) all nets routed or clearly reported as unroutable, (b) zero DRC errors, (c) deterministic — re-run with same seed produces identical traces.

### QV-07a — Phase A feasibility regression

Per fixture, assert `board.feasibility()` behaves correctly:

- **Feasible fixture set.** The same boards from QV-07 that *should* route: Phase A returns `ok=True` with a baseline in bounded time (≤ 30 s for the flasher board). Baseline is byte-identical across re-runs.
- **Infeasible fixture: 1-layer crossing.** Two nets that *must* cross on a 1-layer board. Phase A returns `ok=False` with: specific failing net named, blocking net named, coordinate + layer reported, at least one suggested fix ("add layer" expected as top-ranked).
- **Infeasible fixture: board too small.** Same circuit on a 20 × 20 mm postage stamp. Phase A returns `ok=False` with "enlarge board" expected as top-ranked suggestion (based on frontier-exhaustion location near board edge).
- **Infeasible fixture: clearance too tight.** Parts close enough that netclass clearance makes a corridor impassable. Phase A returns `ok=False` with "relax clearance" expected as top-ranked.
- **Infeasible fixture: resolved by skip.** `board.feasibility(skip=[critical_net])` on the 1-layer-crossing fixture: Phase A succeeds with the remaining nets routed and `critical_net` correctly reported as skipped.
- **Determinism.** Same inputs → byte-identical baseline and byte-identical `why_not()` output, every time. No RNG in Phase A.

### QV-07b — Phase B optimisation regression

Starting from a canned feasibility baseline (saved as a fixture):

- **Monotonicity.** `board.optimize(baseline, trials=50, seed=42)` returns a result with `cost ≤ baseline.cost`. Never worse.
- **Improvement on a known-suboptimal baseline.** Starting from a deliberately-rough baseline (e.g., too-many-vias), Phase B reduces cost by ≥ 20 % within 50 trials.
- **Determinism.** Same baseline + seed → byte-identical best trial.
- **Parallelism equivalence.** Same baseline + seed + trial count → same best trial regardless of `parallel=True/False` and regardless of worker count. Variations allowed only in trial *ordering* in the trial history.
- **Cancellation safety.** Send SIGINT mid-run → returned result is the best-so-far; all completed trials are preserved; no corruption.
- **Cost floor preservation.** With a cost function that is adversarial (always returns 1e9), Phase B still returns the baseline unchanged (never replaces baseline with a trial that didn't beat it).

### QV-07c — Phase A → Phase B handoff

- **Generate wrapper.** `board.generate(trials=50)` on the flasher board equals `board.optimize(board.feasibility().baseline, trials=50)` to byte equality.
- **Feasibility-failed generate.** On an infeasible circuit, `board.generate(...)` returns immediately with `ok=False` and the same `why_not()` as `board.feasibility()`. Phase B is not invoked.
- **Opt-in Phase B on failure.** `board.generate(..., on_feasibility_fail="optimize")` does invoke Phase B on the partial baseline; result has `ok=False` but non-empty `trials[]`.

### QV-08 — Import round-trip

Per adapter, at least one fixture:

1. Import `foo.kicad_pcb`.
2. Export to `foo_roundtrip.kicad_pcb`.
3. Diff the two. Allowed drift: formatting, comment order, UUID regeneration. Disallowed drift: net topology, footprint assignments, trace endpoints, layer assignments.

KiCad is the priority (target: byte-stable round-trip). Eagle / gEDA / etc. are best-effort.

### QV-09 — End-to-end acceptance

The "happy path" script in `frd.md §1.1` runs start-to-finish, producing:

- A valid 3D STEP file that opens in FreeCAD and shows all components.
- A valid `.kicad_pcb` that opens in KiCad pcbnew; pcbnew's DRC passes zero errors.
- Valid Gerbers that open in a Gerber viewer with all layers aligned.
- A BOM and pick-and-place CSV that match the script's components.

This test gates v1 release.

### QV-10 — Manual QA checklist

Before every tagged release:

- [ ] Open FreeCAD, activate the workbench, create a new PCB from the UI — does it work?
- [ ] Import `examples/test_simple.brd` — does 3D view show the right thing?
- [ ] Run Python Console example script — does a board appear?
- [ ] ERC a circuit with a known error — does the dockable panel light up?
- [ ] DRC a board with a known violation — same.
- [ ] Drag a part in 3D view — does `board.route()` respect the new position?
- [ ] Export Gerbers — do all files appear in the output directory?
- [ ] Export KiCad .kicad_pcb — open in pcbnew — passes pcbnew's DRC?
- [ ] Collision test with a second FreeCAD body present — does it detect the intrusion?
- [ ] Run on Linux, macOS, Windows — does it start and render on all three?

---

## Part 3 — Regressions to Watch For

Listed as anti-patterns that have bitten similar projects; add to CI / manual tests.

- **R-01 — Recompute loops.** Parametric graph with circular dependencies triggers infinite recompute. Detect with FreeCAD recompute counter.
- **R-02 — Lost hand placements.** Re-running the script erases a user's manual moves. Covered by QD-01's hybrid model; test by script + drag + re-script.
- **R-03 — Stackup mismatch on round-trip.** Import a 4-layer board, export, re-import — did we preserve all layers? Covered by QV-08.
- **R-04 — Net-merge drive inflation.** `net1 += net2` should take max drive, not sum. Covered by QV-04.
- **R-05 — NOCONNECT accidentally on a real net.** Pin marked NC ends up connected because of sloppy op overloading. Covered by QV-02.
- **R-06 — Pour covers a drill.** Thermal relief missing, plating shorts to plane. Add to QV-07 as a DRC case.
- **R-07 — Silkscreen over an exposed pad.** Silk-over-mask-opening check must flag it. Covered by QV-03.
- **R-08 — Via-in-pad without fill.** On HDI boards, unfilled via-in-pad causes solder wicking. v1 should warn; v2 should fill.
- **R-09 — Layer flip on import.** An adapter mirrors bottom-side parts to the top. Manual QA per format.
- **R-10 — Unit confusion.** mil vs mm mix-up; KiCad v4 internal-mil vs v5 internal-mm. Enforce at the import-adapter boundary and test.
- **R-11 — Phase A wastes budget when infeasible.** A single bad net's A\* expands for minutes before giving up, starving the other nets. Enforce per-net time budget (FR-TE-A-10) and test with a deliberately-adversarial corridor.
- **R-12 — Phase A's "suggested fix" is wrong.** Diagnosis names "add layer" when the real problem is clearance, or vice versa. Covered by QV-07a — each infeasible fixture asserts the expected top-ranked suggestion.
- **R-13 — Phase B accepts a worsening trial.** Bug in cost comparison or RNG-based acceptance kicks in with a baseline cost floor bypassed. Covered by QV-07b's monotonicity and cost-floor-preservation tests.
- **R-14 — Phase A non-determinism sneaks in.** Someone adds a `random.shuffle()` or hash-seeded dict iteration inside the per-net router. Covered by QV-07a's byte-identical re-run assertion on every fixture.
- **R-15 — Phase B "improves" by violating feasibility.** A trial removes a via to shorten a trace but now DRC fails; the trial is accepted because cost appears lower. FR-TE-B-05 says such trials are discarded; test with a fixture where the only cost-reducing moves break DRC.
- **R-16 — `why_not` stale after input change.** User edits the circuit, reruns feasibility, but the displayed diagnosis is cached from the previous run. Invalidate diagnostics on any Circuit/Board property change.
- **R-17 — Infinite feasibility loop.** A circular dependency (e.g., net A requires net B to be routed first, B requires A) hangs Phase A. Detect cycles in the priority graph at phase start and fail explicitly with a clear message.

---

## Part 4 — Known Issues to Carry Forward

Things identified in `repoanalysis.md §10` that are inherited and should be tracked:

- **KI-01** Vendored SQLAlchemy is stale. Replace with pip dependency.
- **KI-02** `PCBcheckFreeCADVersion.checkCompatibility()` is commented out. Reinstate with real check.
- **KI-03** Monolithic files (`PCBobjects.py` 1693 LOC, etc.). Split per-class.
- **KI-04** Python 2/3 straddle code everywhere. Remove.
- **KI-05** No `tests/` directory. Added by P0.
- **KI-06** PySide (Qt4) imports. Migrate to PySide6.
- **KI-07** Import adapters hard-wire to FreeCAD objects. Refactor to emit `(Circuit, Board)`.

Each KI becomes a tracked issue in the repo's issue tracker before work begins.

---

## Part 5 — Decision Log

Track the outcome of each QD here as it's resolved. Empty until the user signs off.

| Date | QD | Decision | Reason |
|---|---|---|---|
| — | QD-01 | (pending) | — |
| — | QD-02 | (pending) | — |
| — | … | … | … |

---

*End of QA doc. Companion: `repoanalysis.md`, `frd.md`, `proceedural-pcb.md`.*
