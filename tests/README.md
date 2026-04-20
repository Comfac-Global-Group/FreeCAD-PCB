# FreeCAD-PCB Test Suite

Part of the Philippine OpenEngineering Pipeline.

## Running tests

```bash
cd /path/to/FreeCAD-PCB
pytest tests/
```

## Test categories

| Directory | Purpose |
|---|---|
| `tests/` | pytest suite |
| `tests/fixtures/` | Hand-crafted test boards and circuits |
| `tests/golden/` | Known-good output fingerprints for regression |

## P0 — Foundations (current)

- `test_smoke.py` — import sanity, no Py2 shims, license present

## P1+ — To be implemented per phase

- `test_erc_matrix.py` — P1
- `test_drc_rules.py` — P4
- `test_router_regression.py` — P4
