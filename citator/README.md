# Citator — authority-tier pipeline (OpenCite, phase 1)

The **mechanical, index-only** layer of the OpenCite citator: given a case, trace who cites it
and rank each citer by **binding force relative to that case** — the thing neither KeyCite nor
Shepard's exposes, and the thing that explains why their document-level flags over-warn.

**No LLM, no per-run API cost beyond one cheap court lookup per citer.** The AI treatment layer
(FOLLOWED / DISTINGUISHED / MERELY-CITED / …) is a *later* phase and lives separately by design.

## The four tiers

| Tier | Meaning | Can it bind the target? |
|---|---|---|
| **BINDING-ON-TARGET** | SCOTUS, the issuing court later/en banc, or a higher court in the same line | yes — highest stakes |
| **SAME-LINE-LOWER** | a lower court bound by the target | shows how the rule is applied where it governs |
| **PERSUASIVE-SISTER** | other circuit / other state / coordinate court | no — spread & erosion only |
| **SAME-CASE-HISTORY** | the target's own later proceedings | procedural fate of *this* party (flagged for human read) |

The tier answers **"could this court bind the target?"** — purely structural, from court +
jurisdiction. Whether a citer actually *engages* the cited holding is the treatment layer's job.

## Files

- `build_court_authority.py` — one-time: every U.S. court → `level` + `circuit` + `state`.
  Derives district→circuit (absent from the CL dump) via state name + 28 U.S.C. § 41.
  Output: `data/court_authority.parquet` (3,355 courts).
- `citator_pipeline.py <cluster_id> [--name NAME]` — trace → resolve court (CL search API,
  cached in `data/cluster_meta.db`) → tier → `data/<slug>_authority.md`.

```bash
PY=/home/sage/.venvs/lawdata/bin/python
$PY build_court_authority.py                       # once
$PY citator_pipeline.py 196186                      # United States v. Trenkler
```

## Validation — United States v. Trenkler (cluster 196186, 1st Cir.)

Ran against the independent commercial ground truth in
`law-school/.../identity-vs-propensity/citator-comparison.md`. **64 distinct citing cases**
(75 raw clusters − CourtListener duplicate clusters), every citer tiered (0 UNKNOWN):

- BINDING-ON-TARGET 31 · SAME-LINE-LOWER 14 · PERSUASIVE-SISTER 13 · SAME-CASE-HISTORY 6
- **All six of Trenkler's substantive citers landed in the correct tier** (Shumway/Fortin/Zajac/
  Coe → PERSUASIVE-SISTER; Fanfan/Martinez-Mercado → BINDING line).
- **SAME-CASE-HISTORY caught all of Trenkler's own habeas/coram-nobis saga** — the litigation
  that drives KeyCite's yellow flag and Shepard's "Caution."
- **Headline result: zero of the negative treatment sits in the binding line.** The mis-scoped
  commercial flag is made legible by a computation that falls straight out of open data.

## Validation — People v. Zackowitz (cluster 3604518, N.Y. Court of Appeals)

Exercises the **state-supreme** branch. 133 distinct citing cases, every citer tiered (0 UNKNOWN):
BINDING-ON-TARGET 21 (later N.Y. Court of Appeals) · SAME-LINE-LOWER 54 (lower N.Y. courts) ·
PERSUASIVE-SISTER 58 (other states + federal).

- Caught a real doctrinal bug: *Shepard v. United States* (SCOTUS 1933) cites Zackowitz **as
  persuasive authority** and cannot overrule N.Y. common-law evidence — so SCOTUS is now tiered
  BINDING only for **federal** targets; over a state target it's PERSUASIVE-SISTER. Federal
  targets (Trenkler) are unaffected.

## Known limitations (v1)

- **State target deciding a *federal* question**: a SCOTUS (or federal) citer that actually binds
  on that federal point is still tiered PERSUASIVE-SISTER — the mechanical layer can't see subject
  matter; that's a treatment-layer call.
- **Panel vs en banc**: a later same-court panel is tiered BINDING-ON-TARGET though only en banc
  can overrule. The distinction is a treatment-layer nuance.
- Corpus frozen at 2025-12-02.
