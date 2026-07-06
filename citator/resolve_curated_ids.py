#!/home/sage/.venvs/lawdata/bin/python
"""resolve_curated_ids.py — canonically re-resolve every curated case id against the corpus.

The curated JSON's courtlistener_ids were fuzzy-matched and are unreliable: its "Brown v.
Board" was Brown & Root v. NLRB, its "Brown v. Kendall" a Kendall Brown habeas, and ids
sometimes point at cert grants or table affirmances instead of merits opinions. Only the
curated NAME is ground truth (dates/citations for bad entries came from the wrong cluster).

    python resolve_curated_ids.py            # phase 1: resolve + write report (no changes)
    python resolve_curated_ids.py --apply    # phase 2: patch JSON + create site rows

Method per case: (1) candidates = corpus clusters sharing the case's rarest name token
(one tokenized pass, name_token_df picks the token); (2) keep candidates whose caption
matches ORDER-AWARE (plaintiff-side tokens vs plaintiff side, defendant vs defendant);
(3) among survivors, the cluster with the most citation-map citers wins (merits opinions
dwarf procedural orders). Output: data/curated_id_resolution.json + printed report.
"""
import duckdb, json, os, re, sys

HERE = os.path.dirname(__file__)
CURATED = "/mnt/d/backups/ai-law-research/data/1L_core_cases.json"
CMAP = "/mnt/d/backups/ai-law-research/data/courtlistener/citation-map-2025-12-02.csv"
LOOK = "/home/sage/lawdata/opinion_cluster.parquet"
CC = os.path.join(HERE, "data", "cluster_court.parquet")
TOKEN_DF = os.path.join(HERE, "data", "name_token_df.parquet")
OUT = os.path.join(HERE, "data", "curated_id_resolution.json")

sys.path.insert(0, HERE)
from citator_pipeline import distinctive_parties, GENERIC_PARTY

# matching tokens: >=3 chars (so 'tice','fox','dole','york' count — 5-char minimum let
# short-name sides go empty and auto-pass, hijacking to famous look-alikes), minus
# procedural/institutional words that appear in every caption
MATCH_GENERIC = set(GENERIC_PARTY) | {
    "america", "american", "plaintiff", "defendant", "appellee", "appellant",
    "petitioner", "respondent", "cross-appellant", "cross-appellee", "intervenor",
    "company", "corporation", "incorporated", "co", "inc", "ltd", "llc",
    "the", "and", "of", "for", "et", "al", "ex", "rel", "re",
}


def match_tokens(text):
    return {t for t in re.findall(r"[a-z][a-z\-']{2,}", text.lower())
            if t not in MATCH_GENERIC}


def sides(name):
    parts = re.split(r"\s+v\.?\s+", name, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    return match_tokens(parts[0]), match_tokens(parts[1])


def caption_matches(curated_name, corpus_name, strict=False):
    """Loose: harvest filter. Strict: a side matches only if the token sets intersect,
    OR both are generic-empty (so 'United States v. Virginia' matches another
    'United States v. Virginia' but never 'Jackson v. Virginia')."""
    ca, sa = sides(curated_name), sides(corpus_name or "")
    if ca and sa:
        (cp, cd), (sp, sd) = ca, sa
        if strict:
            p_ok = bool(cp & sp) or (not cp and not sp)
            d_ok = bool(cd & sd) or (not cd and not sd)
        else:
            p_ok = not cp or not sp or bool(cp & sp)
            d_ok = not cd or not sd or bool(cd & sd)
        return p_ok and d_ok
    if strict:
        # non-adversarial captions (In re ...) need >=2 shared distinctive tokens
        a, b = match_tokens(curated_name), match_tokens(corpus_name or "")
        return len(a & b) >= 2
    a, b = match_tokens(curated_name), match_tokens(corpus_name or "")
    return bool(a & b) if a and b else False


def main(apply=False):
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    con.execute("SET threads=3"); con.execute("SET memory_limit='5GB'")

    # ---- curated entries (dedup by id, keep max casebook_count) ----
    d = json.load(open(CURATED))
    cases = {}
    for subj, v in d.items():
        for c in v["cases"]:
            cid = c.get("courtlistener_id")
            if cid and (cid not in cases or c["casebook_count"] > cases[cid]["count"]):
                cases[cid] = {"id": cid, "name": c["name"], "subject": subj,
                              "count": c["casebook_count"]}
    entries = list(cases.values())
    print(f"{len(entries)} curated entries", flush=True)

    # ---- rarest token per case ----
    df = dict(con.execute(f"SELECT token, df FROM read_parquet('{TOKEN_DF}')").fetchall())
    want_tokens = {}
    for e in entries:
        toks = distinctive_parties(e["name"])
        e["tokens"] = toks
        if toks:
            e["rare"] = min(toks, key=lambda t: df.get(t, 0))
            want_tokens.setdefault(e["rare"], []).append(e["id"])
    print(f"{len(want_tokens)} distinct rare tokens; harvesting candidates...", flush=True)

    # ---- one tokenized pass: clusters containing any wanted token ----
    con.execute("CREATE TEMP TABLE want(token VARCHAR)")
    con.executemany("INSERT INTO want VALUES (?)", [(t,) for t in want_tokens])
    rows = con.execute(rf"""
        WITH toks AS (
          SELECT cluster_id, case_name, court_id, date_filed,
                 unnest(list_distinct(regexp_extract_all(lower(case_name), '[a-z][a-z\-'']{{4,}}'))) AS token
          FROM read_parquet('{CC}') WHERE case_name IS NOT NULL
        )
        SELECT t.token, t.cluster_id, t.case_name, t.court_id, t.date_filed
        FROM toks t JOIN want w USING (token)
    """).fetchall()
    by_token = {}
    for tok, cid, nm, ct, dt in rows:
        by_token.setdefault(tok, []).append((int(cid), nm, ct, str(dt)))
    print(f"harvested {len(rows):,} candidate rows", flush=True)

    # ---- order-aware refinement ----
    for e in entries:
        pool = by_token.get(e.get("rare"), [])
        e["cands"] = {c[0]: c for c in pool if caption_matches(e["name"], c[1])}
    n_cands = sum(len(e["cands"]) for e in entries)
    print(f"{n_cands:,} candidates survive caption matching; counting citers...", flush=True)

    # ---- one citation-map scan over all survivors + current ids ----
    all_ids = sorted({c for e in entries for c in e["cands"]} |
                     {int(e["id"]) for e in entries if e["id"].isdigit()})
    idl = ",".join(map(str, all_ids))
    counts = dict(con.execute(f"""
        WITH tops AS (SELECT opinion_id, cluster_id FROM read_parquet('{LOOK}')
                      WHERE cluster_id IN ({idl})),
        cites AS (SELECT t.cluster_id AS cand, CAST(m.citing_opinion_id AS BIGINT) AS op
                  FROM read_csv('{CMAP}', header=true, quote='"',
                       columns={{'id':'VARCHAR','depth':'VARCHAR','cited_opinion_id':'BIGINT','citing_opinion_id':'BIGINT'}}) m
                  JOIN tops t ON m.cited_opinion_id = t.opinion_id)
        SELECT c.cand, count(DISTINCT l.cluster_id)
        FROM cites c JOIN read_parquet('{LOOK}') l ON l.opinion_id = c.op
        GROUP BY 1""").fetchall())

    # ---- decide: only STRICT caption matches are eligible to win ----
    results = {"verified": [], "remapped": [], "review": [], "unresolved": []}
    for e in entries:
        cur = int(e["id"]) if e["id"].isdigit() else None
        strict = {c: v for c, v in e["cands"].items()
                  if caption_matches(e["name"], v[1], strict=True)}
        pool = strict or e["cands"]
        if not pool:
            results["unresolved"].append(e); e["status"] = "unresolved"; continue
        best = max(pool, key=lambda c: counts.get(c, 0))
        e["winner"] = best
        e["winner_name"] = e["cands"][best][1]
        e["winner_citers"] = counts.get(best, 0)
        e["current_citers"] = counts.get(cur, 0) if cur else 0
        if best == cur:
            results["verified"].append(e); e["status"] = "verified"
        elif strict:
            results["remapped"].append(e); e["status"] = "remapped"
        else:
            # only loose matches exist — a human should look before we touch it
            results["review"].append(e); e["status"] = "review"

    print(f"\nVERIFIED  {len(results['verified'])}   (curated id is the citer-rich strict match)")
    print(f"REMAPPED  {len(results['remapped'])}  (strict caption match, auto-applicable)")
    print(f"REVIEW    {len(results['review'])}  (only loose matches — held for human review)")
    print(f"UNRESOLVED {len(results['unresolved'])}  (no caption-matching cluster found)\n")
    for e in sorted(results["remapped"], key=lambda x: -x["count"]):
        print(f"  {e['count']:>2}bk {e['name'][:44]:46} {e['id']:>9} -> {e['winner']:<9} "
              f"({e['current_citers']:,} -> {e['winner_citers']:,} citers) {e['winner_name'][:40]}")
    print("\n--- review bucket ---")
    for e in sorted(results["review"], key=lambda x: -x["count"]):
        print(f"  {e['count']:>2}bk {e['name'][:44]:46} {e['id']:>9} ?? {e['winner']:<9} "
              f"{e['winner_name'][:45]}")
    for e in results["unresolved"]:
        print(f"  ?? {e['name'][:60]} (id {e['id']})")

    json.dump({k: [{x: e[x] for x in e if x not in ("cands", "tokens")} for e in v]
               for k, v in results.items()}, open(OUT, "w"), indent=1)
    print(f"\nwrote {OUT}")

    if apply:
        apply_fixes(results)


def apply_fixes(results):
    import shutil
    shutil.copy2(CURATED, CURATED + ".bak-resolve")
    d = json.load(open(CURATED))
    remap = {(e["name"], e["id"]): e for e in results["remapped"]}
    n = 0
    for subj in d.values():
        for c in subj["cases"]:
            e = remap.get((c.get("name"), c.get("courtlistener_id")))
            if e:
                c["courtlistener_id"] = str(e["winner"])
                c["id_fixed"] = f"canonical re-resolution (was {e['id']})"
                n += 1
    json.dump(d, open(CURATED, "w"), indent=2)
    print(f"APPLIED: patched {n} JSON entries (backup {CURATED}.bak-resolve)")
    print("NOTE: run insert rows + S3 opinions for new ids next (see task notes).")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
