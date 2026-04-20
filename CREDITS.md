# Credits and Third-Party Notices

This file lists the sources, authors, and licenses of every third-party component used by — or intended to be integrated into — this fork of FreeCAD-PCB. Every contributor named here is acknowledged as a copyright holder of the portions they authored.

## Project Context

This workbench is developed as part of the **[Philippine OpenEngineering Pipeline](https://sites.comfac.net/freecad.html)** — a national engineering capacity initiative led by **Comfac Technology Group** and **Cornersteel Systems Corp**.

**Funding:** Comfac Global Group (CGG) commits a minimum of ₱1M annually to Project FreeCAD, covering technical leadership, AI tooling, OJT interns, infrastructure, evangelization, and school outreach.

**Partnership model:** Philippine engineering schools and technical institutions partner with CGG to co-develop open-source engineering tools. Students earn global open-source credentials; schools save millions in software licensing; every module becomes a public good under AGPLv3.

**This PCB module** is the electronics design track, developed in collaboration with ECE/EE school partners for DRC rules, Philippine EMC standards, and local fabrication workflow integration.

---

## 1. This Repository

### 1.1 Upstream author

**FreeCAD-PCB** workbench — Copyright © 2013–2019 **marmni** (`<marmni@onet.eu>`).
Upstream: <https://github.com/marmni/FreeCAD-PCB>.
License: **GNU Affero General Public License v3.0** (see `LICENSE`, matching the declaration in `package.xml`). The README's historical "LGPL" note conflicted with `package.xml`; this fork resolves the ambiguity in favour of `package.xml` and has written to upstream to confirm. Until upstream confirms otherwise, all inherited code in this fork is treated as AGPLv3.

### 1.2 This fork

Procedural / generative additions — Copyright © 2026 **Comfac-Global-Group (CGG R&D)**.
All new code contributed to this repository is released under **AGPLv3** (inherited) unless explicitly marked otherwise. See §3 for the dual-licensing plan for the procedural core.

### 1.3 Contributors via pull requests

Each merged pull request remains under its author's copyright; by contributing, authors license their work to this project under AGPLv3 (DCO-style). Full commit attribution is in the git history; see `AUTHORS.md` if added.

---

## 2. Third-Party Components

### 2.1 SKiDL — reference library for procedural circuit design

**Repository:** <https://github.com/devbisme/skidl>
**Fork analysed here:** <https://github.com/Comfac-Global-Group/skidl>
**Author:** Dave Vandenbout (<http://xess.com>)
**Copyright:** © 2016–2021 Dave Vandenbout.
**License:** MIT.

The `proceedural-pcb.md` design doc in this repository extracts rules and structure from SKiDL. Any code ported from SKiDL into this workbench retains Dave Vandenbout's copyright notice at the top of the relevant file. Ported modules are redistributed here under AGPLv3 per MIT's "any derivative license" permission, but the MIT header is preserved.

### 2.2 SQLAlchemy — object-relational mapper

**Repository:** <https://github.com/sqlalchemy/sqlalchemy>
**Copyright:** © 2005–present Michael Bayer and contributors.
**License:** MIT.

Currently vendored in `sqlalchemy/` (inherited from upstream). Planned action: un-vendor and declare as a pip dependency (see `qa.md` KI-01). MIT notice preserved.

### 2.3 FreeCAD — the host application

**Repository:** <https://github.com/FreeCAD/FreeCAD>
**License:** LGPL-2.1+ (with some GPL-licensed components).

This workbench consumes FreeCAD's Python API. Per LGPL-2.1 §5, this does not subject this workbench to LGPL, but AGPLv3 is already the applicable license here. LGPL is compatible with AGPLv3 combined-work distribution.

### 2.4 PySide6 / Qt for Python

**License:** LGPL-3.0 (PySide6); Qt itself is LGPL-3.0 / commercial dual.

Used dynamically via FreeCAD's Qt binding. No static linking.

### 2.5 Python standard library

CPython / PSF License. Permissive; no action required.

### 2.6 Hershey fonts (`hershey.txt`)

**Origin:** U.S. National Bureau of Standards (NBS, now NIST), Dr. Allen V. Hershey, 1967.
**License:** Public domain (U.S. federal work).

---

## 3. External Data & Assets

### 3.1 3D component STEP models (`parts/`)

Downloaded from <https://github.com/marmni/FreeCAD-PCB-library> (per `parts/README.txt`). **Licensing varies by model** — some are vendor-supplied under their own terms. Each model's provenance is not yet individually audited in this fork. Planned action:

- Audit `parts/` contents and record each model's origin + license in a `parts/MANIFEST.csv`.
- Do not redistribute models whose licence forbids redistribution; require users to fetch them via `command/PCBDownload.py` at runtime instead.
- Models without clear licence are flagged for removal.

### 3.2 KiCad symbol libraries (`.kicad_sym`)

**Upstream:** <https://gitlab.com/kicad/libraries/kicad-symbols>
**License:** **CC-BY-SA 4.0** with an explicit exemption for symbols instantiated into designs. See <https://www.kicad.org/libraries/license/>.

This workbench **loads** KiCad libraries at runtime from the user's own KiCad installation. **It does not bundle** or redistribute KiCad library files. Users of this workbench who distribute boards designed with it do not need to share their board files under CC-BY-SA — KiCad's library license explicitly carves out instantiated symbols.

### 3.3 KiCad footprint libraries (`.kicad_mod`)

**Upstream:** <https://gitlab.com/kicad/libraries/kicad-footprints>
**License:** Same as §3.2 (CC-BY-SA 4.0 with instantiation exemption).
Same treatment: load from user install, never bundle.

### 3.4 KiCad 3D model libraries

**Upstream:** <https://gitlab.com/kicad/libraries/kicad-packages3D>
**License:** CC-BY-SA 4.0, same exemption.
Loaded at runtime, never bundled.

### 3.5 Example boards (`examples/`)

These `.brd` / `.emn` files were inherited from upstream's test set. Provenance and licence for each file are not individually documented in the upstream repo. Planned action: audit and either confirm permissive re-use or remove.

### 3.6 Eagle `.brd` format

Eagle's file format is Autodesk-proprietary but the format spec is publicly documented. Reading Eagle files does not require a licence; redistributing Autodesk's own format documentation would. This repo does neither — it implements a format reader from public information only.

---

## 4. Runtime Dependencies Referenced by Design Docs

### 4.1 kinet2pcb (for `gen_pcb`)

**License:** MIT.
Depends on KiCad's `pcbnew` Python module (GPL-3.0). Calling `pcbnew` as a separate process does not contaminate this workbench. Linking `pcbnew` at build time would make the combined work GPL-3.0; this workbench plans to call it via subprocess or via the `.kicad_pcb` round-trip exporter (§4.2 below) instead.

### 4.2 KiCad pcbnew file format

Reading and writing `.kicad_pcb` files is unencumbered — the format is documented by the KiCad project for interoperability. This workbench's planned `.kicad_pcb` writer (FR-O-02) reads and writes the format without linking KiCad code.

---

## 5. Licence Compatibility Matrix

| Source | Licence | Combines into AGPLv3 work? |
|---|---|---|
| This workbench | AGPLv3 | — |
| SKiDL code port | MIT | Yes, inherits AGPL |
| SQLAlchemy | MIT | Yes |
| FreeCAD | LGPL-2.1+ | Yes (dynamic link only) |
| PySide6 | LGPL-3.0 | Yes (dynamic link only) |
| Hershey fonts | Public domain | Yes |
| KiCad libraries (runtime load only) | CC-BY-SA 4.0 | Not bundled; no combined-work implication |
| Vendor STEP models | Mixed / per-model | Audit required; some may be non-redistributable |

---

## 6. Licensing — AGPLv3 Throughout

Per the decision recorded in `qa.md` QD-13 (2026-04-20), the entire project — including the procedural core (Part / Pin / Net / ERC / DRC / placer / router logic) and the FreeCAD workbench wrapper — is released under **AGPLv3**. There is no separate MIT-licensed package; all code in this repository carries `# SPDX-License-Identifier: AGPL-3.0-or-later`.

Code ported from SKiDL (MIT) is redistributed here under AGPLv3, retaining the original MIT header and Dave Vandenbout's copyright notice per MIT's terms.

---

## 7. Action Items (tracked)

- [ ] **Contact @marmni** to confirm `package.xml`'s AGPLv3 declaration and formally close the README/xml ambiguity upstream.
- [ ] **Audit `parts/`** — document each STEP model's origin + licence, remove any non-redistributable entries, migrate the rest to on-demand download.
- [ ] **Audit `examples/`** — document provenance of each `.brd` / `.emn`, remove any without clear re-use permission.
- [ ] **Un-vendor SQLAlchemy** — add as pip dep; remove `sqlalchemy/` from the tree.
- [x] **License decision made (2026-04-20):** AGPLv3 for everything; no dual-licensing. All new source files carry `# SPDX-License-Identifier: AGPL-3.0-or-later`.
- [ ] **Add AUTHORS.md** once contributors beyond the original author begin making substantial commits.

---

*Last updated: 2026-04-20.*
