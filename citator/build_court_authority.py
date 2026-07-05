#!/home/sage/.venvs/lawdata/bin/python
"""build_court_authority.py — the MECHANICAL, index-only court reference table.

Every U.S. court in the CourtListener `courts` dump, tagged with:
  level   : SCOTUS | FED_APPEALS | FED_DISTRICT | FED_BANKRUPTCY | STATE_SUPREME
            | STATE_APPEALS | STATE_TRIAL | STATE_OTHER | OTHER
  circuit : 1..11 | 'DC' | 'FED' | None      (the geographic federal circuit)
  state   : full state/territory name | None

This is the map the authority tier needs. The CL dump does NOT encode which circuit
a district sits in (every district's parent_court_id is the generic `usdistct` node),
so we derive it: each district's short_name carries its state, and — by 28 U.S.C. § 41 —
no state spans two circuits, so STATE -> CIRCUIT fully determines DISTRICT -> CIRCUIT.

No AI, no network, no cost. Pure lookup. Output: data/court_authority.parquet.
"""
import duckdb, os, sys

COURTS_CSV = "/mnt/d/backups/ai-law-research/data/courtlistener/courts-2025-12-02.csv"
OUT = os.path.join(os.path.dirname(__file__), "data", "court_authority.parquet")

# 28 U.S.C. § 41 — the geographic circuits. Territories included (PR=1, VI=3, Guam/NMI=9).
# Federal Circuit (subject-matter) and D.C. Circuit are handled by court_id directly.
STATE_CIRCUIT = {
    "Maine": 1, "Massachusetts": 1, "New Hampshire": 1, "Rhode Island": 1, "Puerto Rico": 1,
    "Connecticut": 2, "New York": 2, "Vermont": 2,
    "Delaware": 3, "New Jersey": 3, "Pennsylvania": 3, "Virgin Islands": 3,
    "Maryland": 4, "North Carolina": 4, "South Carolina": 4, "Virginia": 4, "West Virginia": 4,
    "Louisiana": 5, "Mississippi": 5, "Texas": 5,
    "Kentucky": 6, "Michigan": 6, "Ohio": 6, "Tennessee": 6,
    "Illinois": 7, "Indiana": 7, "Wisconsin": 7,
    "Arkansas": 8, "Iowa": 8, "Minnesota": 8, "Missouri": 8,
    "Nebraska": 8, "North Dakota": 8, "South Dakota": 8,
    "Alaska": 9, "Arizona": 9, "California": 9, "Hawaii": 9, "Idaho": 9, "Montana": 9,
    "Nevada": 9, "Oregon": 9, "Washington": 9, "Guam": 9, "Northern Mariana Islands": 9,
    "Colorado": 10, "Kansas": 10, "New Mexico": 10, "Oklahoma": 10, "Utah": 10, "Wyoming": 10,
    "Alabama": 11, "Florida": 11, "Georgia": 11,
    "District of Columbia": "DC",
}
# match longest names first so "West Virginia" wins over "Virginia", "North Dakota" over "Dakota"
_STATES_BY_LEN = sorted(STATE_CIRCUIT, key=len, reverse=True)

# The 13 modern federal appellate courts by court_id.
APPEALS_CIRCUIT = {f"ca{n}": n for n in range(1, 12)}
APPEALS_CIRCUIT.update({"cadc": "DC", "cafc": "FED"})

# Districts whose short_name names no state — hand-assigned. The Canal Zone district sat
# in the Fifth Circuit (old 28 U.S.C. § 41; court abolished 1982). `orld` (District of
# Orleans, 1804-1812) predates the circuit system — appeals went straight to SCOTUS — and
# `usdistct` is CL's generic parent node, not a court; both correctly stay circuit-less.
DISTRICT_OVERRIDE = {"canalzoned": (5, "Canal Zone")}


def state_of(short_name: str):
    """Find the state/territory named in a court's short_name (longest match wins)."""
    if not short_name:
        return None
    for st in _STATES_BY_LEN:
        if st in short_name:
            return st
    return None


def classify(court_id, jurisdiction, short_name):
    """Return (level, circuit, state) for one court."""
    j = (jurisdiction or "").strip()
    if court_id == "scotus":
        return "SCOTUS", None, None
    if court_id in APPEALS_CIRCUIT:
        return "FED_APPEALS", APPEALS_CIRCUIT[court_id], None
    if j == "F":  # historical U.S. Circuit Courts (uscirct, circt*) and stragglers
        return "OTHER", None, None
    if j in ("FD", "FB", "FS"):
        level = {"FD": "FED_DISTRICT", "FB": "FED_BANKRUPTCY", "FS": "OTHER"}[j]
        if court_id in DISTRICT_OVERRIDE:
            circ, st = DISTRICT_OVERRIDE[court_id]
            return level, circ, st
        st = state_of(short_name)
        return level, (STATE_CIRCUIT.get(st) if st else None), st
    if j in ("S", "SS"):
        return "STATE_SUPREME", None, state_of(short_name)
    if j in ("SA", "SAG"):
        return "STATE_APPEALS", None, state_of(short_name)
    if j in ("ST",):
        return "STATE_TRIAL", None, state_of(short_name)
    if j.startswith("S"):
        return "STATE_OTHER", None, state_of(short_name)
    return "OTHER", None, None


def main():
    con = duckdb.connect()
    con.execute("SET enable_progress_bar=false")
    rows = con.execute(
        f"select id, jurisdiction, short_name, citation_string, full_name "
        f"from read_csv('{COURTS_CSV}', header=true)"
    ).fetchall()

    out = []
    for court_id, jur, short_name, cite_str, full_name in rows:
        level, circuit, state = classify(court_id, jur, short_name)
        out.append((court_id, level, str(circuit) if circuit is not None else None,
                    state, jur, cite_str, short_name or full_name))

    con.execute("""create table ca(
        court_id varchar, level varchar, circuit varchar,
        state varchar, jurisdiction varchar, citation_string varchar, court_name varchar)""")
    con.executemany("insert into ca values (?,?,?,?,?,?,?)", out)
    con.execute(f"copy ca to '{OUT}' (format parquet)")

    # ---- report ----
    print(f"wrote {len(out)} courts -> {OUT}\n")
    print("level distribution:")
    for lvl, n in con.execute("select level,count(*) from ca group by 1 order by 2 desc").fetchall():
        print(f"  {lvl:16} {n}")
    # sanity: every FED_DISTRICT should have a circuit; list any that don't (historical/territorial)
    orphans = con.execute(
        "select court_id,court_name from ca where level='FED_DISTRICT' and circuit is null order by 1").fetchall()
    print(f"\nFED_DISTRICT with NO circuit resolved ({len(orphans)}) — expect only historical/oddities:")
    for cid, nm in orphans:
        print(f"  {cid:14} {nm}")
    # spot-check the 1st Circuit (Trenkler's line)
    print("\n1st Circuit members (appeals + districts):")
    for cid, lvl, nm in con.execute(
            "select court_id,level,court_name from ca where circuit='1' order by level,court_id").fetchall():
        print(f"  {cid:8} {lvl:14} {nm}")


if __name__ == "__main__":
    main()
