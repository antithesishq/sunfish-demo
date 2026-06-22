---
sut_path: /home/avpai/src/sunfish-demo
commit: d41cc1a39324b1789f49c0cd3daa0c47e887afb0
updated: 2026-06-22
external_references:
  - path: http://wbec-ridderkerk.nl/html/UCIProtocol.html
    why: UCI protocol spec — consulted during scoping; not relevant to the assertion scan itself.
---

# Existing Antithesis Assertions

## Result: none found

A scan of the codebase found **no Antithesis SDK usage** and **no Antithesis SDK
assertions** of any kind. The codebase has not been instrumented for Antithesis.

### How the scan was performed

From the repo root:

```
grep -rniE "antithesis|assert_always|assert_sometimes|assert_reachable|assert_unreachable|sometimes|always_or" --include="*.py" .
  -> NONE FOUND

grep -rnE "^\s*assert " --include="*.py" .
  -> tools/uci.py:210:    assert args[8] == "moves"
```

### Findings

- **No `import antithesis` / `from antithesis` anywhere.** The Antithesis Python
  SDK is not a dependency (`requirements.txt` lists only `chess==1.9.4` and
  `tqdm==4.57.0`).
- **No SDK assertion calls** (`assert_always`, `assert_sometimes`,
  `assert_reachable`, `assert_unreachable`, `always_or_unreachable`, or their
  lifecycle/`Sometimes` equivalents).
- **One plain Python `assert`** at `tools/uci.py:210`
  (`assert args[8] == "moves"` in the `position fen ... moves ...` branch). This
  is a stdlib `assert`, not an Antithesis assertion. It validates UCI input shape
  and would raise `AssertionError` on malformed `position fen` input — i.e. it is
  a potential crash site, not instrumentation. It does not report to Antithesis.

### Implication for setup and workload

All Antithesis instrumentation is **greenfield**. The `antithesis-setup` skill
must install the Antithesis Python SDK into the SUT dependency graph and add the
bootstrap property. The `antithesis-workload` skill will add the
property-catalog assertions from scratch. No existing assertions need to be
preserved, reconciled, or de-duplicated against — every property in the catalog
is "missing" (not "already present" or "partial").
