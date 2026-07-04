#!/home/sage/.venvs/lawdata/bin/python
"""citator_pipeline.py — authority-tier citator for one target case.

    python citator_pipeline.py <target_cluster_id> [--name "United States v. Trenkler"]

Pipeline (all mechanical — NO LLM, the treatment layer is a later stage):
  1. TRACE   target cluster -> citing cluster_ids   (local: citation-map + opinion_cluster.parquet)
  2. RESOLVE each cluster -> court_id/name/date/status (CourtListener search API, cached in sqlite)
  3. TIER    each citer relative to the target, using data/court_authority.parquet:
       BINDING-ON-TARGET  — can actually overrule/limit it (SCOTUS, same court later,
                            higher court in the same line)
       SAME-LINE-LOWER    — bound by the target; shows how the rule is applied where it governs
       PERSUASIVE-SISTER  — other jurisdiction; doctrinal spread/erosion, cannot bind
       SAME-CASE-HISTORY  — the target's own later proceedings (flagged for human read)
  4. REPORT  markdown table sorted by binding force -> data/<slug>_authority.md

The tier answers "COULD this court bind the target?" (structural). Whether a citer actually
engages the cited holding is the treatment layer's job — kept deliberately separate.
"""
import duckdb, sqlite3, sys, os, time, json, urllib.parse, urllib.request, re

HERE = os.path.dirname(__file__)
CMAP = "/mnt/d/backups/ai-law-research/data/courtlistener/citation-map-2025-12-02.csv"
LOOK = "/home/sage/lawdata/opinion_cluster.parquet"
COURT_AUTH = os.path.join(HERE, "data", "court_authority.parquet")
CACHE = os.path.join(HERE, "data", "cluster_meta.db")
KEY = None  # loaded from .env

TIER_ORDER = ["BINDING-ON-TARGET", "SAME-LINE-LOWER", "PERSUASIVE-SISTER",
              "SAME-CASE-HISTORY", "UNKNOWN"]
STATE_RANK = {"STATE_TRIAL": 0, "STATE_APPEALS": 1, "STATE_SUPREME": 2}
FED_LOWER = {"FED_APPEALS", "FED_DISTRICT", "FED_BANKRUPTCY"}
GENERIC_PARTY = {"united states", "united states of america", "u.s.", "us", "state", "people",
                 "commonwealth", "in re", "ex parte", "matter", "et al", "estate", "city", "county"}


def load_key():
    global KEY
    with open("/mnt/d/dev/ai-law-research/.env") as f:
        for line in f:
            if line.startswith("COURTLISTENER_API_KEY"):
                KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
    return KEY


# ---------- 1. TRACE ----------
def trace(target_cluster_id):
    con = duckdb.connect(); con.execute("SET threads=3"); con.execute("SET memory_limit='4GB'")
    con.execute("SET enable_progress_bar=false")
    ops = [r[0] for r in con.execute(
        f"SELECT opinion_id FROM read_parquet('{LOOK}') WHERE cluster_id = {target_cluster_id}").fetchall()]
    if not ops:
        return []
    idl = ",".join(map(str, ops))
    citer_ops = [r[0] for r in con.execute(f"""
        SELECT DISTINCT CAST(citing_opinion_id AS BIGINT) FROM
        read_csv('{CMAP}', header=true, quote='"',
          columns={{'id':'VARCHAR','depth':'VARCHAR','cited_opinion_id':'BIGINT','citing_opinion_id':'BIGINT'}})
        WHERE cited_opinion_id IN ({idl})""").fetchall()]
    if not citer_ops:
        return []
    citer_clusters = [r[0] for r in con.execute(
        f"SELECT DISTINCT cluster_id FROM read_parquet('{LOOK}') "
        f"WHERE opinion_id IN ({','.join(map(str, citer_ops))})").fetchall()]
    return sorted(set(citer_clusters))


# ---------- 2. RESOLVE (cached) ----------
def _cache():
    db = sqlite3.connect(CACHE)
    db.execute("""create table if not exists cluster_meta(
        cluster_id integer primary key, court_id text, case_name text,
        date_filed text, status text)""")
    return db


def _api_get(path):
    req = urllib.request.Request("https://www.courtlistener.com/api/rest/v4/" + path,
                                 headers={"Authorization": f"Token {KEY}"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def resolve_via_docket(cid):
    """Fallback for clusters missing from the search index: cluster -> docket -> court.
    Returns (court_id, case_name, date_filed, status) or None."""
    try:
        cl = _api_get(f"clusters/{cid}/")
        docket_url = cl.get("docket") or ""
        did = docket_url.rstrip("/").split("/")[-1]
        court_id = None
        if did.isdigit():
            dk = _api_get(f"dockets/{did}/")
            court_id = (dk.get("court") or "").rstrip("/").split("/")[-1] or None
        return (court_id, cl.get("case_name"), cl.get("date_filed"), cl.get("precedential_status"))
    except Exception as e:
        print(f"  ! docket fallback failed for {cid}: {e}", file=sys.stderr)
        return None


def resolve(cluster_ids):
    # One cluster per call: CL's search parser silently truncates OR-batched cluster_id
    # queries (returns partial results with no error) — the exact silent-partial-failure
    # class this project refuses to trust. Per-id + verified count is the honest path.
    # Clusters absent from the search index fall back to cluster->docket->court.
    db = _cache()
    have = {r[0] for r in db.execute("select cluster_id from cluster_meta").fetchall()}
    todo = [c for c in cluster_ids if c not in have]
    via_docket, unresolved = 0, []
    for n, cid in enumerate(todo, 1):
        url = "https://www.courtlistener.com/api/rest/v4/search/?" + urllib.parse.urlencode(
            {"type": "o", "q": f"cluster_id:{cid}", "page_size": 5})
        req = urllib.request.Request(url, headers={"Authorization": f"Token {KEY}"})
        row = None
        try:
            data = json.load(urllib.request.urlopen(req, timeout=60))
            results = data.get("results", [])
            if results:
                r = results[0]
                row = (cid, r.get("court_id"), r.get("caseName"), r.get("dateFiled"), r.get("status"))
        except Exception as e:
            print(f"  ! search error on {cid}: {e}", file=sys.stderr); time.sleep(2)
        if row is None:  # search miss -> docket fallback
            fb = resolve_via_docket(cid)
            if fb:
                row = (cid, *fb); via_docket += 1
            else:
                unresolved.append(cid)
        if row:
            db.execute("insert or replace into cluster_meta values (?,?,?,?,?)", row)
        if n % 20 == 0 or n == len(todo):
            db.commit(); print(f"  resolved {n}/{len(todo)} new clusters", file=sys.stderr)
        time.sleep(0.2)
    db.commit()
    if via_docket:
        print(f"  + {via_docket} resolved via docket fallback (not in search index)", file=sys.stderr)
    if unresolved:
        print(f"  ! {len(unresolved)} truly unresolved: {unresolved[:10]}", file=sys.stderr)
    meta = {}
    for cid, court, name, date, status in db.execute(
            "select cluster_id,court_id,case_name,date_filed,status from cluster_meta").fetchall():
        meta[cid] = {"court_id": court, "case_name": name, "date_filed": date, "status": status}
    return {c: meta[c] for c in cluster_ids if c in meta}


# ---------- 3. TIER ----------
def load_court_auth():
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    ca = {}
    for cid, level, circuit, state in con.execute(
            f"select court_id,level,circuit,state from read_parquet('{COURT_AUTH}')").fetchall():
        ca[cid] = {"level": level, "circuit": circuit, "state": state}
    return ca


def distinctive_parties(name):
    if not name:
        return set()
    parts = re.split(r"\s+v\.?\s+", name.lower())
    tokens = set()
    for p in parts:
        p = p.strip()
        if p in GENERIC_PARTY:
            continue
        for tok in re.findall(r"[a-z][a-z\-']{4,}", p):  # >=5 chars, skip common short words
            if tok not in GENERIC_PARTY:
                tokens.add(tok)
    return tokens


def tier(T, C):
    """T, C: dicts with court_id, level, circuit, state, case_name. All citers postdate T."""
    # same-case lineage (the target's own later proceedings) — flagged for human read
    if T["_tokens"] and C.get("case_name"):
        cl = C["case_name"].lower()
        if any(tok in cl for tok in T["_tokens"]):
            return "SAME-CASE-HISTORY"
    if C["level"] is None:
        return "UNKNOWN"
    if C["level"] == "SCOTUS":
        # SCOTUS is in the binding line only for FEDERAL targets. Over a state court it sits
        # above only on federal questions — a subject-matter call the mechanical layer can't
        # make (e.g. Shepard v. US cites Zackowitz as persuasive; it can't overrule NY law).
        return ("BINDING-ON-TARGET"
                if T["level"] in ("SCOTUS", "FED_APPEALS", "FED_DISTRICT", "FED_BANKRUPTCY")
                else "PERSUASIVE-SISTER")
    if C["court_id"] == T["court_id"]:
        return "BINDING-ON-TARGET"            # same court, later panel/en banc
    # higher court in the target's own line
    if T["level"] in ("FED_DISTRICT", "FED_BANKRUPTCY") and C["level"] == "FED_APPEALS" \
            and C["circuit"] and C["circuit"] == T["circuit"]:
        return "BINDING-ON-TARGET"
    if T["level"] in STATE_RANK and C["state"] and C["state"] == T["state"] \
            and STATE_RANK.get(C["level"], -1) > STATE_RANK.get(T["level"], -1):
        return "BINDING-ON-TARGET"
    # lower court in the target's line (bound BY the target)
    if T["level"] == "SCOTUS":
        return "SAME-LINE-LOWER" if C["level"] in FED_LOWER else "PERSUASIVE-SISTER"
    if T["level"] == "FED_APPEALS":
        if C["level"] in ("FED_DISTRICT", "FED_BANKRUPTCY") and C["circuit"] == T["circuit"]:
            return "SAME-LINE-LOWER"
    if T["level"] in STATE_RANK and C["state"] and C["state"] == T["state"] \
            and STATE_RANK.get(C["level"], 9) < STATE_RANK.get(T["level"], 9):
        return "SAME-LINE-LOWER"
    return "PERSUASIVE-SISTER"


# ---------- 4. REPORT ----------
def run(target_cluster_id, target_name=None):
    load_key()
    ca = load_court_auth()

    citer_clusters = trace(target_cluster_id)
    print(f"trace: {len(citer_clusters)} distinct citing clusters", file=sys.stderr)

    meta = resolve([target_cluster_id] + citer_clusters)
    tmeta = meta.get(target_cluster_id, {})
    tcourt = tmeta.get("court_id")
    T = {"court_id": tcourt, "case_name": target_name or tmeta.get("case_name"),
         **ca.get(tcourt, {"level": None, "circuit": None, "state": None})}
    T["_tokens"] = distinctive_parties(T["case_name"])

    rows = []
    for cid in citer_clusters:
        m = meta.get(cid)
        if not m:
            rows.append((cid, None, None, None, "UNKNOWN", {"level": "UNKNOWN", "circuit": None})); continue
        C = {"court_id": m["court_id"], "case_name": m["case_name"],
             **ca.get(m["court_id"], {"level": None, "circuit": None, "state": None})}
        rows.append((cid, m["case_name"], m["court_id"], m["date_filed"], tier(T, C), C))

    # collapse CourtListener duplicate clusters (same case imported twice under 2 cluster_ids):
    # key on court + date + distinctive party tokens, which survives minor case-name variance.
    seen_case, deduped = set(), []
    for r in rows:
        cid, name, court, date, tl, C = r
        key = (court, date, tuple(sorted(distinctive_parties(name)))) if court and date else ("_", cid)
        if key in seen_case:
            continue
        seen_case.add(key)
        deduped.append(r)
    n_raw = len(rows)
    rows = deduped

    counts = {t: 0 for t in TIER_ORDER}
    for r in rows:
        counts[r[4]] = counts.get(r[4], 0) + 1

    slug = re.sub(r"[^a-z0-9]+", "-", (T["case_name"] or str(target_cluster_id)).lower()).strip("-")[:40]
    out = os.path.join(HERE, "data", f"{slug}_authority.md")
    with open(out, "w") as f:
        f.write(f"# Authority-tier report — {T['case_name']}\n\n")
        f.write(f"**Target:** cluster `{target_cluster_id}` · court `{tcourt}` "
                f"({T['level']}, circuit {T['circuit']}) · {tmeta.get('date_filed')}\n\n")
        f.write(f"**{len(rows)} distinct citing cases** "
                f"({n_raw} raw clusters − {n_raw - len(rows)} CourtListener duplicate clusters; "
                f"mechanical trace, corpus 2025-12-02)\n\n")
        f.write("| Tier | count |\n|---|---|\n")
        for t in TIER_ORDER:
            if counts.get(t):
                f.write(f"| {t} | {counts[t]} |\n")
        f.write("\n---\n\n")
        for t in TIER_ORDER:
            grp = [r for r in rows if r[4] == t]
            if not grp:
                continue
            f.write(f"## {t} ({len(grp)})\n\n| date | court | case |\n|---|---|---|\n")
            for cid, name, court, date, _, C in sorted(grp, key=lambda x: x[3] or ""):
                lvl = C.get("level") or "?"
                circ = f" c{C['circuit']}" if C.get("circuit") else ""
                f.write(f"| {date or '?'} | {court or '?'} ({lvl}{circ}) | {name or cid} |\n")
            f.write("\n")

    print(f"\nTarget: {T['case_name']}  [{tcourt} / {T['level']} / circuit {T['circuit']}]")
    print(f"Citing clusters: {len(citer_clusters)}")
    for t in TIER_ORDER:
        if counts.get(t):
            print(f"  {t:20} {counts[t]}")
    print(f"\nreport -> {out}")
    return rows, T


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: citator_pipeline.py <target_cluster_id> [--name NAME]"); sys.exit(1)
    tid = int(sys.argv[1])
    name = None
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    run(tid, name)
