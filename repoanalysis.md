# FreeCAD-PCB Repository Analysis

**Repo:** `Comfac-Global-Group/FreeCAD-PCB` (fork of `marmni/FreeCAD-PCB`)
**Workbench name:** PCB (`<classname>PCB</classname>` in `package.xml`)
**Version:** 6.2023.1
**Target FreeCAD:** ≥ 0.18 (package declares `freecadmin=0.18.0`)
**License:** LGPL/AGPLv3
**Size:** ~172,000 Python LOC across 100+ files
**Analysed:** 2026-04-20

**Purpose of this doc:** describe what this workbench actually *is* today, so we can measure it against the procedural-PCB design in `proceedural-pcb.md` and plan the gap (see `frd.md`).

---

## 1. What It Is (and Isn't)

FreeCAD-PCB is an **import, visualise, and lightly-edit** workbench. Its core loop:

1. **Read** a PCB file from an external EDA tool (Eagle, KiCad v3/v4, gEDA, LibrePCB, FreePCB, DipTrace, FidoCadJ, IDF v2/3/4, HyperLynx, Razen).
2. **Render** its geometry inside FreeCAD as `Part::Feature` objects — board outline, layers-as-Sketches, component proxies with linked STEP 3D models.
3. **Let the user tweak** part positions/rotations/sides, run 3D collision checks, render with Kerkythea/POV-Ray, and export back to the source format (or to BOM / drill report).

What it is **not:**

- Not a schematic editor.
- Not a router or autorouter (no trace creation at all).
- Not an autoplacer (manual drag-and-drop only).
- Not a design-rule checker (no trace-width or clearance rules).
- Not net-aware (imports discard the electrical netlist — only geometry is kept).
- Not procedural / code-first. There is no `Part()`, `Net()`, `Board()` Python API for building a PCB from scratch.
- Not parametric in any deep sense. Geometry is baked at import; moving a part translates its shape but never recomputes copper.

This workbench is, in practice, about **80% viewer / 20% geometry-placement tool**.

---

## 2. Repo Layout

```
FreeCAD-PCB/
├── InitGui.py, Init.py, __init__.py       # entry + command registration
├── PCBboard.py, PCBbrd.py                 # board object + import dispatcher
├── PCBobjects.py              (1693 LOC)  # custom Part::FeaturePython classes
├── PCBpartManaging.py         (1208 LOC)  # STEP model loader, part placement helpers
├── PCBtoolBar.py              (1060 LOC)  # toolbar + menu wiring
├── PCBcommands.py, PCBcategories.py       # command dispatch
├── PCBconf.py                              # 17 standard layer types, per-format mapping
├── PCBdataBase.py                          # SQLAlchemy ORM (parts library)
├── PCBfunctions.py, PCBcheckFreeCADVersion.py
├── PCBrc.py                                # resource loader
│
├── command/                                # 30+ user-facing commands
│   ├── PCBcreateBoard.py, PCBexport.py
│   ├── PCBcollision.py                    # 3D bbox collision (NOT electrical DRC)
│   ├── PCBexportBOM.py, PCBexportHoles.py
│   ├── PCBexportKerkythea.py, PCBexportPovRay.py
│   ├── PCBexportDrillingMap.py
│   ├── PCBDownload.py                     # fetch 3D models online
│   └── ...
│
├── formats/                                # per-EDA-tool import adapters
│   ├── baseModel.py                        # shared helpers (filterHoles, ...)
│   ├── kicad_v3.py   (~61k LOC)
│   ├── eagle.py      (~52k LOC)
│   ├── fidocadj.py   (~52k LOC)
│   ├── librepcb.py   (~38k LOC)
│   ├── razen.py      (~38k LOC)
│   ├── geda.py       (~31k LOC)
│   ├── freepcb.py    (~30k LOC)
│   ├── kicad_v4.py   (~20k LOC — inherits from v3)
│   ├── idf_v2/v3/v4.py  hyp.py  diptrace.py
│   └── dialogMAIN_FORM.py, PCBmainForms.py
│
├── parts/                                  # bundled STEP/col component models
├── sqlalchemy/                             # vendored ORM
├── save/                                   # user-saved settings/state
├── generateModels/                         # 3D model generation helpers
├── script/, icons/, data/                  # assets
├── examples/                               # 18 .brd/.emn test boards
├── instructions/                           # PDF manual
└── proceedural-pcb.md                      # target spec for procedural redesign
```

Adapter files dominate the byte count: the `formats/` directory is ~350k of repetitive per-EDA-tool parsing code.

---

## 3. Document-Object Model

The workbench registers several custom FreeCAD scripted objects (all inherit `Part::FeaturePython`).

### 3.1 `PCBboardObject` — the board substrate (`PCBboard.py:~104`)

```python
obj.addProperty("App::PropertyFloatConstraint", "Thickness", "PCB", "Thickness")   # 0.2-10mm
obj.addProperty("App::PropertyLink",            "Border",    "PCB", ...)            # outline Sketch
obj.addProperty("App::PropertyLink",            "Holes",     "Holes", ...)          # holes Sketch
obj.addProperty("App::PropertyBool",            "Display",   "Holes", ...)
obj.addProperty("App::PropertyBool",            "AutoUpdate", "Base", ...)
obj.addProperty("App::PropertyLinkList",        "Group",     "Base", "Group")       # children
```

- Board outline = a user or imported Sketch, extruded by Thickness.
- Holes = a single Sketch with circles; all treated as through-holes.
- **No stackup object.** Thickness is a scalar. No dielectric layers, no per-layer copper weight, no Dk.

### 3.2 `partObject` / `partObject_E` — component instances (`PCBobjects.py:60-230`)

```python
obj.addProperty("App::PropertyString",      "Package")       # footprint name (string)
obj.addProperty("App::PropertyEnumeration", "Side")          # TOP / BOTTOM
obj.addProperty("App::PropertyDistance",    "X")
obj.addProperty("App::PropertyDistance",    "Y")
obj.addProperty("App::PropertyDistance",    "Socket")        # Z height above board
obj.addProperty("App::PropertyAngle",       "Rot")           # 0-360°
obj.addProperty("App::PropertyBool",        "KeepPosition")  # lock
obj.addProperty("App::PropertyLink",        "PartName")      # ref des
obj.addProperty("App::PropertyLink",        "PartValue")     # value
```

**What's missing from this schema** (relative to the procedural spec):
- No `pins[]` — the part has no pin list at the FreeCAD object level
- No `nets[]` / net bindings
- No pin-type information (input/output/power/passive…)
- No footprint geometry as a first-class object (it's a *string* that points to something in the linked STEP model)
- No netclass / design-rule link

### 3.3 `layerSilkObject` (`PCBobjects.py:~673`) and `constraintAreaObject` (`:~1518`)

Layer geometry and keepout zones. Each is a Sketcher-backed shape. No z-ordering metadata, no coupling to a copper-layer model (there isn't one).

### 3.4 `DocumentObserver` (`PCBobjects.py:1679`)

Watches the whole FreeCAD document for thickness / Socket changes and nudges parts' Z heights to stay on top of the board.

### 3.5 Parametric behaviour — limited

`partObject.onChanged()` reacts to X/Y/Rot/Socket/Side by updating `Placement` and propagating the delta to child pads/holes. But there is **no `execute()`** that rebuilds geometry — the stub at line 131 is `pass`. Change the stackup, swap a footprint, or alter a trace width after import, and the geometry does not regenerate. Everything that matters is baked the moment the file is imported.

---

## 4. Import Pipeline

All imports dispatch through `PCBbrd.open()`, which sniffs the file and routes to a `formats/<tool>.py` adapter. The shared base (`formats/baseModel.py`) provides helpers for:

- `filterHoles(r, Hmin, Hmax)` — ignore holes outside a size range
- `detectIntersectingHoles(...)` — merge near-overlapping holes
- `addHoleToObject(...)` — push a hole into the holes Sketch
- `filterTentedVias(...)` — skip vias whose drill is covered by mask
- `setProjectFile(...)` — tokenise input into `[start]...[stop]` blocks

Each adapter then walks its file and, for each element, creates or appends to a Sketch or a `partObject`. Traces and pads become circles/polygons in Sketcher; components become `partObject` instances with their `Package` string filled in.

**Critical observation:** the import path constructs **geometry only**. The netlist in the source file (every KiCad `.kicad_pcb` has one, as does an Eagle `.brd`) is *parsed but discarded*. No `Net` object is created. There is no intermediate representation — each adapter speaks directly to FreeCAD's object tree. This means:

- Two different imports of the same board will produce structurally different FreeCAD trees.
- No round-trip fidelity: export is format-specific per adapter, not a common serialiser.
- Nothing downstream can ask "which component is on this net?" — because *there are no nets*.

---

## 5. Parts Library (SQLAlchemy-backed)

`PCBdataBase.py` defines a real SQLite-backed parts library:

```
Models      (id, name, description, category_id, datasheet, path3DModels, ...)
Packages    (id, model_id, name, software, x, y, z, rx, ry, rz)
modelsParam (id, model_id, name, color, align, active, display, x, y, z, rz, size, spin)
Categories  (id, name, parent_id, description)     # nested tree
Paths       (id, model_id, path, attribute)         # STEP/STL file paths
Settings    (id, name, value)                        # key-value config
```

`PCBpartManaging.py` wraps this for:
- `getPartShape(filePath, step_model, colorizeElements)` — load STEP or cached `.col` BREP
- `adjustRotation()`, `loadPackagesData()` — apply per-package offset
- On-demand STEP download via `command/PCBDownload.py`

A genuinely useful piece of the workbench. Categorised, queryable, supports per-variant 3D-model offsets. **Reusable** as the parts library for a procedural redesign.

Missing on top of it: no pin-count, no pin-to-pad map, no electrical metadata (power/ground pin marking, max voltage, etc.), no footprint geometry as native FreeCAD (the footprint is *only* a 3D model and a name).

---

## 6. Layer Model

17 named layer *types* in `PCBconf.py` — but they are tags, not stack members:

```
pathT   pathB          # copper traces, top and bottom
padT    padB           # pads
silkT   silkB          # silkscreen
glueT   glueB          # glue dots
placeT  placeB         # placement drawings
anno                   # annotations
measure                # measurement layer
... 4 more ...
```

Each layer is a Sketcher object in the FreeCAD document. `softLayers["eagle"]` etc. map EDA-tool layer numbers to these names. There is:

- No layer *stack* (ordered list of copper + dielectric).
- No dielectric thickness / Dk / loss-tangent metadata.
- No inner copper layer support beyond top/bottom — a 4-layer import collapses inner layers onto top/bottom or drops them.
- No per-layer impedance awareness.

---

## 7. Command Surface

From `InitGui.py` + `PCBcommands.py` + `PCBtoolBar.py`, the user-facing commands are:

**Create / edit**
- Create new PCB (outline sketch + holes sketch + thickness)
- Add / edit constraint area (keepout)
- Add annotation / section / bounding-box / glue
- Create drill centre
- Part: assign / update / move / find-online 3D model

**Display**
- Shaded / Flat lines / Wireframe / Internal view
- Toggle layer visibility
- Cut to board outline / Show signals / Cut holes through all layers

**Analysis**
- Detect collisions (all-to-all)
- Detect collisions with PCB
- Bounding box calc

**Render**
- Export to Kerkythea
- Export to POV-Ray

**Export**
- Back to source format (per-adapter)
- BOM (CSV)
- Holes coordinates / drill report
- Drilling map symbols

**No commands for:** creating a trace, creating a via, creating a net, placing parts automatically, routing, running DRC, running ERC, verifying impedance, length-matching.

---

## 8. What's Parametric vs Baked

| Thing | Parametric? | Behaviour |
|---|---|---|
| Board thickness | Yes (reactive) | Parts' Z heights follow via `DocumentObserver` |
| Part position (X, Y, Rot, Socket) | Yes | `onChanged()` syncs `Placement` and child pads |
| Part side (TOP/BOTTOM) | Yes | Mirrors the shape via 180° rotation |
| Board outline (sketch edit) | **No geometry regen** | Sketch edits don't recompute copper / pads |
| Copper traces | **Baked** | Static Sketcher shapes from import |
| Pads / footprints | **Baked** | Can move a part; can't re-render its footprint |
| Layer stack | N/A | No stack exists |
| DRC rules | N/A | No rules exist |

---

## 9. Capability Matrix (against `proceedural-pcb.md`)

| Capability from the procedural spec | Present today | Notes |
|---|---|---|
| `Part` / `Pin` / `Net` / `Bus` / `Circuit` primitives (§1-3) | ❌ | None — parts are geometry proxies only |
| Connection operators (`+=`, `&`, `|`) | ❌ | No electrical graph to connect |
| 14 pin types + drive model (§3) | ❌ | No pin concept |
| ERC with conflict matrix (§4) | ❌ | No ERC at all |
| Hierarchy / subcircuits (§5) | ❌ | No hierarchy concept |
| Force-directed placer (§6) | ❌ | Manual drag only |
| Layer-aware router (§7) | ❌ | No router |
| Board outline primitive (§9) | ✅ | `PCBboardObject` — outline + thickness + holes |
| Hole / cutout primitive | ✅ | Via `Holes` sketch on the board |
| Keepout zone | ✅ | `constraintAreaObject` (visual only, not DRC-aware) |
| Layer stack (§10) | ❌ | Flat layers; no dielectric/Dk |
| Real footprints (§11) | Partial | Loads STEP models; no pin-to-pad map; no footprint geometry as FreeCAD native |
| DRC / netclass rules (§12) | ❌ | Collision only, not DRC |
| Vias / planes / pours (§13) | ❌ | None |
| Side assignment (§14) | ✅ | `Side` property on `partObject` |
| 3D collision (§15) | ✅ | `PCBcollision.py` bbox check |
| Length matching / impedance (§16) | ❌ | None |
| Thermal / mech constraints (§17) | ❌ | None |
| Export: BOM / Gerbers / STEP / KiCad PCB | Partial | BOM ✅, STEP ✅, Gerbers ❌, KiCad round-trip ❌ |

See `frd.md` for the gap-closure plan derived from this matrix.

---

## 10. Code Quality Signals

- **Python 2/3 straddle.** `try: import builtins except: import __builtin__` patterns still present (`PCBdataBase.py:31`). Py2 no longer a concern; these can be cleaned up.
- **PySide (Qt4-era).** Imports `from PySide import QtCore, QtGui` — not PySide6 / Qt6. Modern FreeCAD builds ship Qt6; this will need porting.
- **Monolithic files.** `PCBobjects.py` (1693), `PCBpartManaging.py` (1208), `PCBtoolBar.py` (1060). Splitting these is day-one refactor work.
- **Version guard disabled.** `PCBcheckFreeCADVersion.checkCompatibility()` is commented out at `InitGui.py:122` — the workbench silently accepts any FreeCAD.
- **No tests.** No `tests/` dir, no pytest, no CI config in the repo. Every format adapter is hand-verified.
- **SQLAlchemy vendored in-tree.** `sqlalchemy/` directory rather than a pip dependency — stale copy, may lag security fixes.
- **No type hints.** Pure `.py` with no annotations; refactoring tools and IDE support are limited.

---

## 11. What's Reusable vs What Has to Be Rewritten

### Reusable (keep and extend)

1. **3D visualisation pipeline.** `Part::FeaturePython` + Sketcher gives clean 3D rendering for free. Keep.
2. **Parts library (SQLAlchemy schema + STEP loader).** Solid. Extend with pin/pad/net metadata.
3. **Import adapters for *geometry*.** `formats/*.py` can be repurposed as importers — but the output must feed the new electrical model, not skip straight to FreeCAD geometry.
4. **Board + holes + keepout objects.** `PCBboardObject`, `constraintAreaObject` are reasonable foundations. Wrap them in a parametric stackup.
5. **Collision detection.** `PCBcollision.py` bbox logic is fine; extend to 3D cuboid with height.
6. **Kerkythea / POV-Ray / STEP export.** Rendering infrastructure is mature; keep.

### Rewrite (no equivalent exists)

1. **Electrical object model** (Part, Pin, Net, Bus, Circuit). Port from SKiDL verbatim where possible.
2. **ERC engine.** Port SKiDL's 14×14 matrix.
3. **DRC engine.** New — trace/pad/via clearance, annular ring, silk-over-mask, netclass-driven.
4. **Stackup model.** New — ordered list of (copper, dielectric, silk, mask, paste, fab) with thickness / Dk / loss-tangent per layer.
5. **Autoplacer.** New (or port SKiDL's force-directed placer, extended to 3D).
6. **Router.** New — layer-aware A* with via cost. SKiDL's switchbox router is not applicable to PCB.
7. **Trace / via / pour primitives.** New FreeCAD document objects.
8. **Parametric `execute()`.** Every FreeCAD object must regenerate geometry on upstream change. Currently none do.
9. **KiCad `.kicad_pcb` round-trip.** Important for practical use; the current export paths are per-adapter and lossy.

---

## 12. Notable Risks

- **Qt4 → Qt6 port.** PySide imports will break on modern FreeCAD. Estimate: 2-3 weeks of tedium across ~30 UI files.
- **Vendored SQLAlchemy.** Upgrading Python / FreeCAD may surface compat issues. Consider unvendoring.
- **No tests anywhere.** Any refactor has no safety net. First task in any serious effort: write golden-file tests against `examples/*.brd`.
- **Monolithic `PCBobjects.py`.** Touching one object type risks breaking others. Split per-class first.

---

## 13. One-Line Summary

> FreeCAD-PCB is a competent **3D PCB viewer with a parts library** bolted onto FreeCAD. To make it procedural / code-first as `proceedural-pcb.md` proposes, we keep the 3D rendering, the parts library, and the import geometry; we build the entire electrical model (nets, pins, ERC, DRC, router, autoplacer, stackup) from scratch, likely porting SKiDL's core for the electrical side.

---

*See also: `proceedural-pcb.md` (target spec), `frd.md` (functional requirements & gap-closure plan), `qa.md` (open questions & verification plan).*
