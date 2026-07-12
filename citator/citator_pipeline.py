#!/home/sage/.venvs/lawdata/bin/python
"""citator_pipeline.py — authority-tier citator for one target case.

    python citator_pipeline.py <target_cluster_id> [--name "United States v. Trenkler"]

Pipeline (all mechanical — NO LLM, the treatment layer is a later stage):
  1. TRACE   target cluster -> citing cluster_ids   (local: citation-map + opinion_cluster.parquet)
  2. RESOLVE each cluster -> court_id/name/date/status (LOCAL: cluster_court.parquet, no API)
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
import duckdb, sys, os, re

HERE = os.path.dirname(__file__)
CMAP = "/mnt/d/backups/ai-law-research/data/courtlistener/citation-map-2025-12-02.csv"
LOOK = "/home/sage/lawdata/opinion_cluster.parquet"
COURT_AUTH = os.path.join(HERE, "data", "court_authority.parquet")
CLUSTER_COURT = os.path.join(HERE, "data", "cluster_court.parquet")
TOKEN_DF = os.path.join(HERE, "data", "name_token_df.parquet")

# A party token is "distinctive" only if rare across the corpus (build_token_df.py):
# 'palsgraf' (df 3) identifies its case; 'railroad' (df 66k) flagged every
# "...Railroad..." citer as Erie's own history.
RARE_MAX = 5000

TIER_ORDER = ["BINDING-ON-TARGET", "SAME-LINE-LOWER", "PERSUASIVE-SISTER",
              "SAME-CASE-HISTORY", "UNKNOWN"]
STATE_RANK = {"STATE_TRIAL": 0, "STATE_APPEALS": 1, "STATE_SUPREME": 2}
FED_LOWER = {"FED_APPEALS", "FED_DISTRICT", "FED_BANKRUPTCY"}
GENERIC_PARTY = {"united states", "united states of america", "u.s.", "us", "state", "people",
                 "commonwealth", "in re", "ex parte", "matter", "et al", "estate", "city", "county"}


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


def trace_cited(target_cluster_id):
    """Return clusters cited by every opinion in the target cluster."""
    con = duckdb.connect(); con.execute("SET threads=3"); con.execute("SET memory_limit='4GB'")
    con.execute("SET enable_progress_bar=false")
    ops = [r[0] for r in con.execute(
        f"SELECT opinion_id FROM read_parquet('{LOOK}') WHERE cluster_id = {target_cluster_id}").fetchall()]
    if not ops:
        return []
    idl = ",".join(map(str, ops))
    cited_ops = [r[0] for r in con.execute(f"""
        SELECT DISTINCT CAST(cited_opinion_id AS BIGINT) FROM
        read_csv('{CMAP}', header=true, quote='"',
          columns={{'id':'VARCHAR','depth':'VARCHAR','cited_opinion_id':'BIGINT','citing_opinion_id':'BIGINT'}})
        WHERE citing_opinion_id IN ({idl})""").fetchall()]
    if not cited_ops:
        return []
    cited_clusters = [r[0] for r in con.execute(
        f"SELECT DISTINCT cluster_id FROM read_parquet('{LOOK}') "
        f"WHERE opinion_id IN ({','.join(map(str, cited_ops))})").fetchall()]
    return sorted(set(cited_clusters) - {target_cluster_id})


# ---------- 2. RESOLVE (local — cluster_court.parquet, no API) ----------
def resolve(cluster_ids):
    """Local court/name/date/precedential lookup from cluster_court.parquet — no CourtListener API.
    Built once from the dockets bulk file (build_cluster_court.py); 100% court coverage on the
    2025-12-02 corpus. Returns {cluster_id: {court_id, case_name, date_filed, status}}."""
    if not cluster_ids:
        return {}
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false"); con.execute("SET threads=4")
    con.execute("CREATE TEMP TABLE want(cluster_id BIGINT)")
    con.executemany("INSERT INTO want VALUES (?)", [(int(c),) for c in cluster_ids])
    rows = con.execute(f"""
        SELECT cc.cluster_id, cc.court_id, cc.case_name, cc.date_filed, cc.precedential_status
        FROM read_parquet('{CLUSTER_COURT}') cc JOIN want w ON w.cluster_id = cc.cluster_id
    """).fetchall()
    out = {cid: {"court_id": court, "case_name": name, "date_filed": date, "status": status}
           for cid, court, name, date, status in rows}
    missing = [c for c in cluster_ids if int(c) not in out]
    if missing:
        print(f"  ! {len(missing)} clusters not in corpus (post-cutoff?): {missing[:10]}", file=sys.stderr)
    return {c: out[int(c)] for c in cluster_ids if int(c) in out}
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


def token_df(tokens):
    """Corpus document frequency for the given name tokens (targeted parquet lookup)."""
    if not tokens:
        return {}
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    ph = ",".join("?" * len(tokens))
    return dict(con.execute(
        f"SELECT token, df FROM read_parquet('{TOKEN_DF}') WHERE token IN ({ph})",
        list(tokens)).fetchall())


def history_matcher(name):
    """(tokens, match_all) for same-case-history detection, rarity-gated.

    Rare tokens (df <= RARE_MAX) identify the case alone — any one matching a citer
    name means the target's own later proceedings. A target with only common tokens
    (International Shoe: 'international' 49k, 'washington' 36k) falls back to requiring
    ALL of them together; with a single common token (US v. Virginia -> 'virginia'),
    detection is off — better to under-flag than mark thousands of strangers."""
    toks = distinctive_parties(name)
    df = token_df(toks)
    rare = {t for t in toks if df.get(t, 0) <= RARE_MAX}
    if rare:
        return rare, False
    if len(toks) >= 2:
        return toks, True
    return set(), False


def tier(T, C):
    """T, C: dicts with court_id, level, circuit, state, case_name. All citers postdate T."""
    # same-case lineage (the target's own later proceedings) — flagged for human read
    if T["_tokens"] and C.get("case_name"):
        cl = C["case_name"].lower()
        hit = all if T.get("_match_all") else any
        if hit(tok in cl for tok in T["_tokens"]):
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
    ca = load_court_auth()

    citer_clusters = trace(target_cluster_id)
    print(f"trace: {len(citer_clusters)} distinct citing clusters", file=sys.stderr)

    meta = resolve([target_cluster_id] + citer_clusters)
    tmeta = meta.get(target_cluster_id, {})
    tcourt = tmeta.get("court_id")
    T = {"court_id": tcourt, "case_name": target_name or tmeta.get("case_name"),
         **ca.get(tcourt, {"level": None, "circuit": None, "state": None})}
    T["_tokens"], T["_match_all"] = history_matcher(T["case_name"])

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
