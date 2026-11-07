"""
CodePulse HARD-MODE demo / torture test.

Run from the codepulse_backend project root (same folder as main.py):

    python codepulse_hard_demo.py                 # full run
    python codepulse_hard_demo.py --strict        # also exit 1 if known bugs are still present
    python codepulse_hard_demo.py --dump out_dir  # write payload.json + response.json (POST payload to /api/v1/analysis)

What it does
------------
PART A  Builds a deliberately nasty 6-profile persona (LeetCode, Codeforces, CodeChef, GeeksforGeeks,
        AtCoder, HackerRank) and checks the engine against
          1. an INDEPENDENT oracle written from the metric definitions (not copied from the engine),
          2. hand-fixed golden values for every classification boundary (80/65/40 %, 9 vs 10 submissions),
          3. metamorphic / property tests (order-independence, idempotent duplicates, case/whitespace-proof
             canonical IDs, adding an empty profile changes nothing, determinism),
          4. a "perfect data" scenario and a "cold start" scenario.
PART B  Edge-case probes for problems found while reviewing the code. Each prints BUG (still present)
        or OK (fixed). They do not fail the run unless --strict is given.
PART C  End-to-end HTTP checks (FastAPI TestClient): same result as the engine, 422-vs-500 behaviour,
        CORS, and a 100k-submission scale test.

All data is synthetic and deterministic (seeded). Pure ASCII output markers so Windows consoles are happy.
"""

import argparse
import copy
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from models.input_models import AnalysisRequest, SolvedProblem
    from engine.analysis_engine import analyze_user
    from engine.normalizer import normalize_platform_name
    from engine.topic_mapper import normalize_topic
except ImportError as exc:  # pragma: no cover
    sys.exit(f"Run this from the codepulse_backend folder (the one containing main.py). Import failed: {exc}")

# ----------------------------------------------------------------------------------------------
# tiny test harness
# ----------------------------------------------------------------------------------------------
RESULTS: list[tuple[str, str, str, str]] = []  # (part, name, status, detail)


def check(part: str, name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    RESULTS.append((part, name, status, detail))
    line = f"  [{status}] {name}"
    if not ok and detail:
        line += f"\n         -> {detail}"
    print(line)
    return ok


def probe(name: str, bug_present: bool, expected: str, evidence: str) -> None:
    status = "BUG" if bug_present else "OK"
    RESULTS.append(("B", name, status, f"expected: {expected} | observed: {evidence}"))
    print(f"  [{status:>4}] {name}\n         expected: {expected}\n         observed: {evidence}")


def section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


# ----------------------------------------------------------------------------------------------
# persona construction
# ----------------------------------------------------------------------------------------------
PLATFORMS = [
    dict(key="lc", name="LeetCode", user="hard_lc", w=5, complete=True, pages=12, prefix="lc"),
    dict(key="cf", name="Codeforces", user="hard_cf", w=4, complete=True, pages=20, prefix="cf"),
    dict(key="cc", name="CodeChef", user="hard_cc", w=3, complete=True, pages=6, prefix="cc"),
    dict(key="gfg", name="GeeksforGeeks", user="hard_gfg", w=2, complete=False, pages=3, prefix="gfg"),
    dict(key="atc", name="AtCoder", user="hard_atc", w=1, complete=True, pages=2, prefix="atc"),
]
IDX = {p["key"]: i for i, p in enumerate(PLATFORMS)}

# Different spellings per platform. Every variant must map to the topic on the left.
VARIANTS = {
    "Arrays": ["array", "Arrays", "ARRAY", "arrays", "Array"],
    "Strings": ["string", "Strings", "STRING", "strings", "String"],
    "Graphs": ["graph", "Graphs", "GRAPH", "graphs", "Graph"],
    "Dynamic Programming": ["dp", "Dynamic-Programming", "dynamic_programming", "DYNAMIC PROGRAMMING", "DP"],
    "Stacks": ["stack", "Stacks", "STACK", "stacks", "Stack"],
    "Heaps": ["priority queue", "Heap", "priority-queue", "heaps", "HEAP"],
    "Trees": ["tree", "Trees", "TREE", "trees", "Tree"],
    "Sorting": ["sort", "Sorting", "SORT", "sorting", "Sort"],
    "Binary Search": ["binary-search", "Binary Search", "BINARY SEARCH", "binary search", "Binary-Search"],
    "Math": ["mathematics", "Math", "MATH", "math", "Mathematics"],
    "Greedy": ["greedy", "Greedy", "GREEDY", "greedy", "Greedy"],
    "Backtracking": ["backtracking", "Backtracking", "BACKTRACKING", "backtracking", "Backtracking"],
    "Number Theory": ["number theory", "Number Theory", "NUMBER THEORY", "number_theory", "Number  Theory"],
}
EXTRA_TAGS = {"trie": "Tries"}  # additional spellings used outside the judged-submission plan

# TOTAL judged submissions per topic across ALL profiles after de-duplication, INCLUDING multi-tag
# events. (accepted, failed). These produce exact boundary percentages on purpose.
PLAN = {
    "Arrays": (40, 10),               # 50 -> 80.00 %  exactly Strong
    "Strings": (54, 6),               # 60 -> 90.00 %  Strong, biggest sample
    "Number Theory": (18, 2),         # 20 -> 90.00 %  Strong (ties Strings on rate, smaller sample)
    "Graphs": (13, 7),                # 20 -> 65.00 %  exactly Good
    "Dynamic Programming": (8, 12),   # 20 -> 40.00 %  exactly Developing
    "Stacks": (15, 15),               # 30 -> 50.00 %  Developing
    "Heaps": (6, 4),                  # 10 -> 60.00 %  Developing at exactly the 10-submission minimum
    "Trees": (19, 29),                # 48 -> 39.58 %  Needs Improvement (just under the 40 line)
    "Sorting": (3, 7),                # 10 -> 30.00 %  NI
    "Binary Search": (1, 9),          # 10 -> 10.00 %  NI, ties Math on rate, smaller sample
    "Math": (2, 18),                  # 20 -> 10.00 %  NI, worst topic
    "Greedy": (0, 9),                 # 9  ->  0.00 %  Insufficient Data (one short of the minimum)
    "Backtracking": (7, 2),           # 9  -> 77.78 %  Insufficient Data
}
# Multi-tag events: each judged submission counts ONCE in EACH of its topics.
MULTI = [
    (["Arrays", "Strings"], [True, True, True, False]),
    (["Graphs", "Dynamic Programming"], [True, False, False, False, True, False]),
    (["Trees", "Dynamic Programming", "Graphs"], [False, False]),
]
MULTI_PLATFORM = ["lc", "cf", "cc"]

GOLDEN = {  # topic: (accepted, failed, judged, accuracy %, classification)
    "Arrays": (40, 10, 50, 80.0, "Strong"),
    "Strings": (54, 6, 60, 90.0, "Strong"),
    "Number Theory": (18, 2, 20, 90.0, "Strong"),
    "Graphs": (13, 7, 20, 65.0, "Good"),
    "Dynamic Programming": (8, 12, 20, 40.0, "Developing"),
    "Stacks": (15, 15, 30, 50.0, "Developing"),
    "Heaps": (6, 4, 10, 60.0, "Developing"),
    "Trees": (19, 29, 48, 39.58, "Needs Improvement"),
    "Sorting": (3, 7, 10, 30.0, "Needs Improvement"),
    "Binary Search": (1, 9, 10, 10.0, "Needs Improvement"),
    "Math": (2, 18, 20, 10.0, "Needs Improvement"),
    "Greedy": (0, 9, 9, 0.0, "Insufficient Data"),
    "Backtracking": (7, 2, 9, 77.78, "Insufficient Data"),
}


def slug(topic: str) -> str:
    return topic.lower().replace(" ", "-")


def split_counts(n: int, weights: list[int]) -> list[int]:
    """Largest-remainder split of n over weights (deterministic)."""
    total = sum(weights)
    raw = [n * w / total for w in weights]
    base = [int(x) for x in raw]
    order = sorted(range(len(weights)), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[: n - sum(base)]:
        base[i] += 1
    return base


def canonical_for(key: str, topic: str, j: int) -> str:
    """Canonical ID with deliberate cross-platform sharing AND case/whitespace noise."""
    s = slug(topic)
    if j < 2 and key in ("lc", "gfg"):
        base = f"shared:{s}:{j}"
        return f"  {base.upper()}  " if key == "gfg" else base
    if j == 2 and key in ("lc", "cc"):
        base = f"lccc:{s}:{j}"
        return base.upper() if key == "cc" else base
    if j < 2 and key in ("cf", "atc"):
        base = f"cfatc:{s}:{j}"
        return base + " " if key == "atc" else base
    return f"{key}:{s}:{j}"


class IdGen:
    """Submission IDs. Numeric ranges deliberately OVERLAP across platforms (must not be de-duplicated
    across platforms). AtCoder uses lowercase-hex IDs so an UPPERCASE duplicate can be injected."""

    def __init__(self) -> None:
        self.n = defaultdict(lambda: 5_000_000)

    def next(self, key: str) -> str:
        self.n[key] += 1
        return f"atc-{self.n[key]:x}" if key == "atc" else str(self.n[key])


def make_contests(key: str, rng: random.Random) -> list[dict]:
    def build(start, ts_list, changes, rank0):
        rows, rating = [], start
        for i, (ts, chg) in enumerate(zip(ts_list, changes)):
            rows.append({
                "contest_id": f"{key}-{i}", "contest_name": f"{key.upper()} Round {i + 1}",
                "timestamp": ts, "old_rating": rating, "new_rating": rating + chg,
                "rating_change": chg, "rank": rank0 + i * 37,
            })
            rating += chg
        return rows

    if key == "cf":      # last three changes sum to -95 -> rating-dip insight; INPUT ORDER SHUFFLED
        rows = build(1500, [1740000000 + i * 1_000_000 for i in range(5)], [40, 25, -30, -45, -20], 800)
        rng.shuffle(rows)
        return rows
    if key == "lc":      # healthy trend (+49 over last three); one nameless and one id-less contest; SHUFFLED
        rows = build(1800, [1745000000 + i * 604800 for i in range(5)], [30, -10, 45, 12, -8], 300)
        rows[1]["contest_name"] = None
        rows[3]["contest_id"] = None
        rng.shuffle(rows)
        return rows
    if key == "cc":      # first two contests share a timestamp; last three sum to -80 -> second dip
        t = 1746000000
        return build(1700, [t, t, t + 1_000_000, t + 2_000_000, t + 3_000_000], [20, 35, -25, -40, -15], 2000)
    if key == "atc":     # epoch-0 record with no old rating/change, then a rank-1 contest
        return [
            {"contest_id": "atc-0", "contest_name": "Legacy import", "timestamp": 0,
             "old_rating": None, "new_rating": 1100, "rating_change": None, "rank": 4000},
            {"contest_id": "atc-1", "contest_name": "AtCoder Beginner Contest", "timestamp": 1745000000,
             "old_rating": 1100, "new_rating": 1234, "rating_change": 134, "rank": 1},
        ]
    return []


def make_daily(i: int) -> dict[str, int]:
    base = datetime(2026, 9, 1)
    out = {}
    for d in range(44):
        count = (d * 7 + i * 3) % 11
        if (d + i) % 5 == 0:
            count = 0  # explicit zero days
        out[(base + timedelta(days=d)).strftime("%Y-%m-%d")] = count
    return out


def build_persona(seed: int = 2026) -> list[dict]:
    rng = random.Random(seed)
    weights = [p["w"] for p in PLATFORMS]
    ids = IdGen()

    contrib = {t: [0, 0] for t in PLAN}
    for topics, flags in MULTI:
        for t in topics:
            contrib[t][0] += sum(flags)
            contrib[t][1] += len(flags) - sum(flags)
    single = {t: (PLAN[t][0] - contrib[t][0], PLAN[t][1] - contrib[t][1]) for t in PLAN}
    assert all(a >= 0 and f >= 0 for a, f in single.values()), "plan/multi mismatch"

    prof = {p["key"]: {"problems": [], "subs": []} for p in PLATFORMS}
    cc_missing_left = 2

    for topic, (a_tot, f_tot) in single.items():
        a_split, f_split = split_counts(a_tot, weights), split_counts(f_tot, weights)
        for i, p in enumerate(PLATFORMS):
            key = p["key"]
            flags = [True] * a_split[i] + [False] * f_split[i]
            rng.shuffle(flags)
            n = len(flags)
            if not n:
                continue
            slots = (n + 2) // 3
            variant = VARIANTS[topic][i % 5]
            per_slot = defaultdict(list)
            for k, fl in enumerate(flags):
                per_slot[k % slots].append(fl)
            for j in range(slots):
                local = f"{p['prefix']}-{slug(topic)}-{j}"
                canon = canonical_for(key, topic, j)
                tags = [variant]
                if key == "gfg" and j == 0 and topic != "Math":
                    tags.append(VARIANTS["Math"][i % 5])  # same problem, different tag set per platform
                prof[key]["problems"].append({
                    "platform_problem_id": local, "canonical_id": canon, "tags": tags,
                    "solved": any(per_slot[j]), "title": f"{topic} practice #{j}",
                })
                for fl in per_slot[j]:
                    sid = ids.next(key)
                    if topic == "Backtracking" and key == "cc" and cc_missing_left > 0:
                        sid, cc_missing_left = None, cc_missing_left - 1  # judged, tagged, but no ID
                    prof[key]["subs"].append({
                        "submission_id": sid, "platform_problem_id": local, "canonical_id": canon,
                        "tags": [variant], "accepted": fl,
                    })

    # multi-tag problems (3 distinct problems, repeated attempts)
    for g, (topics, flags) in enumerate(MULTI):
        key = MULTI_PLATFORM[g]
        i = IDX[key]
        tags = [VARIANTS[t][i % 5] for t in topics]
        local, canon = f"{key}-multi-{g}", f"multi:{g}"
        prof[key]["problems"].append({"platform_problem_id": local, "canonical_id": canon, "tags": tags,
                                      "solved": any(flags), "title": f"Multi-topic {g}"})
        for fl in flags:
            prof[key]["subs"].append({"submission_id": ids.next(key), "platform_problem_id": local,
                                      "canonical_id": canon, "tags": tags, "accepted": fl})
    # the Graphs+DP problem is also attempted (unsolved) on AtCoder -> union of tags/solved across profiles
    prof["atc"]["problems"].append({"platform_problem_id": "atc-multi-1", "canonical_id": "MULTI:1 ",
                                    "tags": [VARIANTS["Graphs"][4], VARIANTS["Dynamic Programming"][4]],
                                    "solved": False, "title": "Multi-topic 1 (AtCoder copy)"})

    # problems with no judged submissions: Tries (LC), unicode topic (GfG)
    for j, solved in enumerate([True, True, False]):
        prof["lc"]["problems"].append({"platform_problem_id": f"lc-tries-{j}", "canonical_id": f"lc:tries:{j}",
                                       "tags": ["trie"], "solved": solved, "title": f"Trie problem {j}"})
    for j, solved in enumerate([True, False]):
        prof["gfg"]["problems"].append({"platform_problem_id": f"gfg-hi-{j}", "canonical_id": f"gfg:hi:{j}",
                                        "tags": ["संख्या सिद्धांत"],
                                        "solved": solved, "title": "unicode-tagged"})

    # data-quality landmines in problem_activity
    prof["cc"]["problems"].append({"platform_problem_id": "cc-unmapped-1", "canonical_id": None,
                                   "tags": [VARIANTS["Arrays"][2]], "solved": True, "title": "solved, no canonical ID"})
    prof["cf"]["problems"].append({"platform_problem_id": "cf-unmapped-2", "canonical_id": None,
                                   "tags": [], "solved": False, "title": "no canonical ID, no tags"})
    prof["gfg"]["problems"].append({"platform_problem_id": "gfg-untagged-3", "canonical_id": "gfg:untagged:3",
                                    "tags": [" ", ""], "solved": False, "title": "blank tags"})
    # duplicate rows inside LeetCode: stale "unsolved" copy (UPPERCASE canonical) of the first 6 solved problems
    stale = []
    for row in [r for r in prof["lc"]["problems"] if r["solved"]][:6]:
        dup = dict(row)
        dup["canonical_id"] = (row["canonical_id"] or "").upper()
        dup["solved"] = False
        stale.append(dup)
    prof["lc"]["problems"] = stale + prof["lc"]["problems"]

    # untagged / id-less judged events
    for fl in (False, False, True):
        prof["lc"]["subs"].append({"submission_id": ids.next("lc"), "platform_problem_id": "lc-unknown",
                                   "canonical_id": None, "tags": ["  ", ""], "accepted": fl})
    for _ in range(2):
        prof["cf"]["subs"].append({"submission_id": ids.next("cf"), "platform_problem_id": "cf-unknown",
                                   "canonical_id": None, "tags": [], "accepted": False})
    prof["cf"]["subs"].append({"submission_id": None, "platform_problem_id": "cf-noid", "canonical_id": None,
                               "tags": [], "accepted": False})
    prof["gfg"]["subs"].append({"submission_id": ids.next("gfg"), "platform_problem_id": "gfg-unknown",
                                "canonical_id": None, "tags": [], "accepted": False})

    for p in PLATFORMS:
        rng.shuffle(prof[p["key"]]["subs"])

    # importer-style totals are computed BEFORE duplicate rows are injected
    totals = {}
    for p in PLATFORMS:
        subs = prof[p["key"]]["subs"]
        acc = sum(1 for s in subs if s["accepted"])
        totals[p["key"]] = (acc, len(subs) - acc)

    # duplicate submission rows (cross-page repeats): LC exact copies, CF whitespace-padded IDs,
    # AtCoder UPPERCASE-ID copy
    lc_with_id = [s for s in prof["lc"]["subs"] if s["submission_id"]]
    prof["lc"]["subs"].extend(copy.deepcopy(lc_with_id[:5]))
    cf_with_id = [s for s in prof["cf"]["subs"] if s["submission_id"]]
    for s in copy.deepcopy(cf_with_id[:3]):
        s["submission_id"] = f"  {s['submission_id']} "
        prof["cf"]["subs"].append(s)
    atc_copy = copy.deepcopy([s for s in prof["atc"]["subs"] if s["submission_id"]][0])
    atc_copy["submission_id"] = atc_copy["submission_id"].upper()
    prof["atc"]["subs"].append(atc_copy)

    out = []
    for p in PLATFORMS:
        key = p["key"]
        problems = prof[key]["problems"]
        solved_canon = {(r["canonical_id"] or "").strip().casefold() for r in problems if r["solved"] and r["canonical_id"]}
        record = {
            "platform_name": p["name"], "username": p["user"],
            "current_rating": None, "total_solved": len(solved_canon),
            "correct_submissions": totals[key][0], "failed_submissions": totals[key][1],
            "total_attempted": None if key == "gfg" else sum(totals[key]),
            "problem_activity": problems, "submission_activity": prof[key]["subs"],
            "contest_history": make_contests(key, rng), "daily_activity": make_daily(IDX[key]),
            "data_complete": p["complete"], "pagination_pages": p["pages"],
            "duplicate_submission_records": {"lc": 5, "cf": 0, "cc": 0, "gfg": 2, "atc": 0}[key],
            "missing_submission_ids": {"cc": 2}.get(key, 0),
            "problemset_lookup_misses": 2 if key == "cf" else 0,
            "problemset_entries_without_tags": 1 if key in ("cf", "gfg") else 0,
        }
        if key == "lc":
            record["current_rating"] = 1869
            # solved_problems overlaps problem_activity + 5 solved problems that only exist here + 1 unmapped
            record["solved_problems"] = [
                {"platform_problem_id": r["platform_problem_id"], "canonical_id": r["canonical_id"],
                 "title": r["title"], "url": f"https://leetcode.example/{r['platform_problem_id']}", "difficulty": "Medium"}
                for r in problems if r["solved"]
            ]
            record["solved_problems"] += [
                {"platform_problem_id": f"lc-extra-{k}", "canonical_id": f"lc:extra-solved-{k}", "difficulty": "Hard"}
                for k in range(5)
            ]
            record["solved_problems"].append({"platform_problem_id": "lc-legacy-unmapped", "canonical_id": None})
            record["total_solved"] += 5 + 1
        if key == "cf":
            record["current_rating"] = 1470
        if key == "cc":
            record["current_rating"] = 1675
            record["total_solved"] += 1  # the unmapped solved row
        if key == "gfg":
            record["total_solved"] += 7  # platform says 7 more solves than we could list (history incomplete)
        if key == "atc":
            record["current_rating"] = 1234
        out.append(record)

    out.append({  # brand-new account: explicit empty lists (NOT null), complete history
        "platform_name": "HackerRank", "username": "hard_hr", "current_rating": None, "total_solved": 0,
        "correct_submissions": 0, "failed_submissions": 0, "total_attempted": 0, "problem_activity": [],
        "submission_activity": [], "contest_history": [], "daily_activity": {}, "data_complete": True,
        "pagination_pages": 0,
    })
    return out


# ----------------------------------------------------------------------------------------------
# INDEPENDENT ORACLE (written from the documented metric definitions, not from the engine code)
# ----------------------------------------------------------------------------------------------
_TAG_MAP: dict[str, str] = {}


def _k(tag: str) -> str:
    return " ".join(tag.strip().lower().replace("_", " ").split())


for _topic, _vars in VARIANTS.items():
    for _v in _vars:
        _TAG_MAP[_k(_v)] = _topic
for _raw, _topic in EXTRA_TAGS.items():
    _TAG_MAP[_k(_raw)] = _topic


def exp_tag(tag: str) -> str:
    key = _k(tag)
    return _TAG_MAP.get(key) or " ".join(w.capitalize() for w in key.split())


def cid(x):
    if not x:
        return None
    x = str(x).strip().casefold()
    return x or None


def rate(n, d):
    return None if d <= 0 else round(n / d * 100, 2)


def classify(count, acc_rate):
    if count is None or count < 10 or acc_rate is None:
        return "Insufficient Data"
    return "Strong" if acc_rate >= 80 else "Good" if acc_rate >= 65 else "Developing" if acc_rate >= 40 else "Needs Improvement"


def oracle(platforms: list[dict]) -> dict:
    O: dict = {}
    # ---- unique solved ---------------------------------------------------------------
    owners = defaultdict(set)
    unresolved = 0
    for p in platforms:
        pkey = (p["platform_name"].casefold(), p["username"].casefold())
        recs = list(p.get("solved_problems") or []) + [r for r in (p.get("problem_activity") or []) if r["solved"]]
        canon, canon_local, loose = set(), set(), set()
        for r in recs:
            c, l = cid(r.get("canonical_id")), cid(r.get("platform_problem_id"))
            if c:
                canon.add(c)
                canon_local.add(l)
                owners[c].add(pkey)
            elif l:
                loose.add(l)
        loose -= canon_local
        unresolved += len(loose) + max(0, p["total_solved"] - len(canon) - len(loose))
    has_details = any((p.get("solved_problems") or []) or any(r["solved"] for r in (p.get("problem_activity") or [])) for p in platforms)
    history_complete = all(p.get("data_complete", False) for p in platforms)
    reported = sum(p["total_solved"] for p in platforms)
    correct = sum(p["correct_submissions"] for p in platforms)
    failed = sum(p["failed_submissions"] for p in platforms)

    # ---- topic problems --------------------------------------------------------------
    glob: dict = {}
    n_prob = miss_c = miss_t = 0
    for p in platforms:
        recs = p.get("problem_activity")
        if recs is None:
            continue
        local: dict = {}
        for r in recs:
            n_prob += 1
            c = cid(r.get("canonical_id"))
            tags = {exp_tag(t) for t in r.get("tags", []) if t and t.strip()}
            miss_c += not c
            miss_t += not tags
            if not c:
                continue
            d = local.setdefault(c, {"tags": set(), "solved": False})
            d["tags"] |= tags
            d["solved"] |= bool(r["solved"])
        for c, d in local.items():
            g = glob.setdefault(c, {"tags": set(), "solved": False})
            g["tags"] |= d["tags"]
            g["solved"] |= d["solved"]
    t_att, t_sol = defaultdict(set), defaultdict(set)
    for c, g in glob.items():
        for t in g["tags"]:
            t_att[t].add(c)
            if g["solved"]:
                t_sol[t].add(c)

    # ---- topic submissions (per profile de-dupe by submission_id, every attempt counts) ------
    t_acc, t_fail = Counter(), Counter()
    judged = tagged = dup = miss_ids = 0
    for p in platforms:
        subs = p.get("submission_activity")
        if subs is None:
            continue
        seen, obs_dup, obs_miss = set(), 0, 0
        for s in subs:
            sid = cid(s.get("submission_id"))
            if sid and sid in seen:
                obs_dup += 1
                continue
            if sid:
                seen.add(sid)
            else:
                obs_miss += 1
            judged += 1
            tags = {exp_tag(t) for t in s.get("tags", []) if t and t.strip()}
            if not tags:
                continue
            tagged += 1
            for t in tags:
                (t_acc if s["accepted"] else t_fail)[t] += 1
        dup += max(p.get("duplicate_submission_records", 0), obs_dup)
        miss_ids += max(p.get("missing_submission_ids", 0), obs_miss)

    topics = {}
    for t in set(t_att) | set(t_acc) | set(t_fail):
        a, f = t_acc.get(t), t_fail.get(t)
        has_sub = t in t_acc or t in t_fail
        cnt = (t_acc[t] + t_fail[t]) if has_sub else None
        acc_rate = rate(t_acc[t], cnt) if has_sub else None
        att = len(t_att[t]) if t in t_att else None
        topics[t] = {
            "solved": len(t_sol[t]) if t in t_att else None, "attempted": att,
            "completion_rate": rate(len(t_sol[t]), att) if att else None,
            "accepted_submissions": t_acc[t] if has_sub else None,
            "failed_submissions": t_fail[t] if has_sub else None,
            "submission_count": cnt, "submission_success_rate": acc_rate,
            "classification": classify(cnt, acc_rate),
        }
    O["topics"] = topics

    # ---- contests --------------------------------------------------------------------
    contests = {}
    for p in platforms:
        recs = sorted(p["contest_history"], key=lambda r: r["timestamp"])
        changes = [r["rating_change"] for r in recs if r.get("rating_change") is not None]
        ratings = []
        for r in recs:
            rt = r.get("new_rating")
            if rt is None and r.get("old_rating") is not None and r.get("rating_change") is not None:
                rt = r["old_rating"] + r["rating_change"]
            if rt is not None:
                ratings.append(rt)
        last3 = [r["rating_change"] for r in recs if r.get("rating_change") is not None][-3:]
        contests[p["platform_name"].casefold()] = {
            "total_contests": len(recs), "positive_changes": sum(c > 0 for c in changes),
            "negative_changes": sum(c < 0 for c in changes),
            "average_rating_change": round(sum(changes) / len(changes), 2) if changes else None,
            "best_rating": max(ratings) if ratings else None,
            "latest_rating": p["current_rating"] if p["current_rating"] is not None else (ratings[-1] if ratings else None),
            "history_points": len(ratings), "dip": len(last3) >= 3 and sum(last3) < 0,
            "dip_sum": sum(last3),
        }
    O["contests"] = contests

    # ---- daily activity ----------------------------------------------------------------
    daily = defaultdict(int)
    for p in platforms:
        for d, c in p["daily_activity"].items():
            daily[d] += c
    O["daily"] = [{"date": d, "activity_count": daily[d]} for d in sorted(daily)]
    O["active_days"] = sum(1 for v in daily.values() if v > 0) if daily else None

    # ---- overview / data quality -----------------------------------------------------
    O["overview"] = {
        "total_solved": len(owners) if has_details else reported,
        "platform_reported_solved": reported,
        "duplicate_solved_across_platforms": sum(len(v) - 1 for v in owners.values()),
        "unresolved_solved_count": unresolved,
        "unique_solved_complete": bool(has_details and unresolved == 0 and history_complete),
        "correct_submissions": correct, "failed_submissions": failed,
        "total_attempted": None if any(p["total_attempted"] is None for p in platforms) else sum(p["total_attempted"] for p in platforms),
        "success_rate": rate(correct, correct + failed),
        "total_contests": sum(len(p["contest_history"]) for p in platforms),
        "active_days": O["active_days"],
    }
    O["quality"] = {
        "history_complete": history_complete,
        "judged_submission_count": judged, "tagged_submission_count": tagged,
        "untagged_submission_count": judged - tagged, "topic_tag_coverage_rate": rate(tagged, judged),
        "duplicate_submission_records": dup, "missing_submission_ids": miss_ids,
        "pagination_pages": sum(p.get("pagination_pages", 0) for p in platforms),
        "profiles_with_complete_history": sum(1 for p in platforms if p.get("data_complete")),
        "profiles_total": len(platforms), "problem_activity_records": n_prob,
        "missing_problem_activity_canonical_ids": miss_c, "missing_problem_activity_tags": miss_t,
        "problemset_lookup_misses": sum(p.get("problemset_lookup_misses", 0) for p in platforms),
        "problemset_entries_without_tags": sum(p.get("problemset_entries_without_tags", 0) for p in platforms),
        "topic_tag_coverage_complete": history_complete and judged == tagged,
        "canonical_id_coverage_complete": history_complete and miss_c == 0,
    }
    return O


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def run_engine(platforms: list[dict], name: str = "Hard Mode Tester") -> dict:
    req = AnalysisRequest.model_validate({"display_name": name, "platforms": platforms})
    return analyze_user(req.platforms, req.display_name).model_dump(mode="json")


def invariants(out: dict) -> dict:
    """Everything that must NOT depend on input ordering."""
    return {
        "overview": out["overview"],
        "platform_comparison": out["platform_comparison"],
        "topic_analytics": out["topic_analytics"],
        "data_quality": out["data_quality"],
        "chart_platform": out["charts"]["platform_solved"],
        "chart_topics": out["charts"]["topic_distribution"],
        "chart_daily": out["charts"]["daily_activity"],
        "contests": {c["platform"]: c for c in out["contest_analytics"]["platforms"]},
        "insights": sorted((i["type"], i["title"], i["description"]) for i in out["insights"]),
    }


def diff(a, b, path="") -> list[str]:
    if type(a) != type(b):
        return [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: len {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


# ----------------------------------------------------------------------------------------------
# PART A
# ----------------------------------------------------------------------------------------------
def part_a(payload: list[dict], out: dict) -> None:
    section("PART A - ENGINE CORRECTNESS ON THE HARD PERSONA (oracle + golden + metamorphic)")
    exp = oracle(payload)
    ov, dq = out["overview"], out["data_quality"]

    print("\n[A1] payload & shape")
    try:
        AnalysisRequest.model_validate({"display_name": "x", "platforms": payload})
        check("A", "persona payload validates against input_models.py", True)
    except Exception as e:  # noqa: BLE001
        check("A", "persona payload validates against input_models.py", False, str(e)[:300])
    check("A", "6 profiles connected", out["user_summary"]["platforms_connected"] == 6)
    check("A", "display_name (with emoji) preserved", out["user_summary"]["username"] == "Hard Mode Tester")

    print("\n[A2] overview vs independent oracle")
    for k, e in exp["overview"].items():
        check("A", f"overview.{k} == {e!r}", ov[k] == e, f"engine={ov[k]!r} oracle={e!r}")
    check("A", "hand-computed: 9 unresolved solved (LC 1 unmapped + CC 1 unmapped + GfG 7 unlisted)",
          ov["unresolved_solved_count"] == 9, f"engine={ov['unresolved_solved_count']}")
    check("A", "unique solved < reported (cross-platform duplicates removed)",
          ov["total_solved"] < ov["platform_reported_solved"])

    print("\n[A3] platform comparison")
    rows = {r["platform"].casefold(): r for r in out["platform_comparison"]}
    for p in payload:
        r = rows.get(p["platform_name"].casefold())
        want = (p["total_solved"], p["current_rating"], p["correct_submissions"], p["failed_submissions"],
                rate(p["correct_submissions"], p["correct_submissions"] + p["failed_submissions"]), len(p["contest_history"]))
        got = None if r is None else (r["solved"], r["current_rating"], r["correct_submissions"], r["failed_submissions"],
                                       r["submission_success_rate"], r["contests_participated"])
        check("A", f"row {p['platform_name']}", got == want, f"engine={got} expected={want}")
    names = [r["platform"].casefold() for r in out["platform_comparison"]]
    check("A", "platform_comparison sorted alphabetically", names == sorted(names))

    print("\n[A4] topic analytics vs oracle (every topic, every field)")
    got_topics = {r["topic"]: r for r in out["topic_analytics"]}
    check("A", "topic set matches oracle (alias merging across 5 spellings/platform worked)",
          set(got_topics) == set(exp["topics"]),
          f"extra={sorted(set(got_topics) - set(exp['topics']))} missing={sorted(set(exp['topics']) - set(got_topics))}")
    for t in sorted(exp["topics"], key=str.lower):
        r = got_topics.get(t, {})
        bad = {k: (r.get(k), v) for k, v in exp["topics"][t].items() if r.get(k) != v}
        check("A", f"topic {t}", not bad, f"(engine, oracle) mismatches: {bad}")
    ordered = [r["topic"] for r in out["topic_analytics"]]
    check("A", "topic_analytics sorted case-insensitively", ordered == sorted(ordered, key=str.lower))
    check("A", "success_rate alias == completion_rate for every row",
          all(r["success_rate"] == r["completion_rate"] for r in out["topic_analytics"]))

    print("\n[A5] GOLDEN classification boundaries (hand-fixed, oracle-independent)")
    for t, (a, f, n, pct, cls) in GOLDEN.items():
        r = got_topics.get(t, {})
        got = (r.get("accepted_submissions"), r.get("failed_submissions"), r.get("submission_count"),
               r.get("submission_success_rate"), r.get("classification"))
        check("A", f"{t:20} {a}/{n} = {pct}% -> {cls}", got == (a, f, n, pct, cls), f"engine={got}")
    r = got_topics["Tries"]
    check("A", "Tries (problems but zero submissions) -> Insufficient Data, submission fields None",
          r["classification"] == "Insufficient Data" and r["submission_count"] is None and r["attempted"] == 3 and r["solved"] == 2,
          str(r))
    check("A", "unicode topic survives end to end",
          any("संख्या" in t for t in got_topics))
    check("A", "Math problem-count includes GfG shared problems tagged with extra 'Math' (tag union across profiles)",
          got_topics["Math"]["attempted"] == exp["topics"]["Math"]["attempted"], f"attempted={got_topics['Math']['attempted']}")

    print("\n[A6] contests")
    got_c = {c["platform"].casefold(): c for c in out["contest_analytics"]["platforms"]}
    for name, e in exp["contests"].items():
        c = got_c.get(name, {})
        want = {k: e[k] for k in ("total_contests", "positive_changes", "negative_changes", "average_rating_change", "best_rating", "latest_rating")}
        got = {k: c.get(k) for k in want}
        check("A", f"contest stats {name}", got == want, f"engine={got} oracle={want}")
        hist = c.get("rating_history", [])
        check("A", f"{name}: history sorted by time & {e['history_points']} plotted points",
              [h["timestamp"] for h in hist] == sorted(h["timestamp"] for h in hist) and len(hist) == e["history_points"])
    check("A", "epoch-0 contest rendered as 1970-01-01",
          any(h["date"] == "1970-01-01" for c in out["contest_analytics"]["platforms"] for h in c["rating_history"]))
    series = {s["platform"].casefold(): s for s in out["charts"]["contest_rating_by_platform"]}
    check("A", "contest chart has a series only for platforms with ratings (no empty GfG/HackerRank series)",
          set(series) == {n for n, e in exp["contests"].items() if e["history_points"]}, str(sorted(series)))

    print("\n[A7] charts & daily activity")
    check("A", "chart_data.daily_activity == oracle sums (overlapping dates added, zeros kept)", out["charts"]["daily_activity"] == exp["daily"])
    check("A", "platform_solved chart == reported per-platform solved",
          {p["platform"].casefold(): p["solved"] for p in out["charts"]["platform_solved"]} == {p["platform_name"].casefold(): p["total_solved"] for p in payload})
    check("A", "topic_distribution chart matches topic rows",
          {d["topic"]: d["solved"] for d in out["charts"]["topic_distribution"]} == {t: r["solved"] for t, r in got_topics.items()})

    print("\n[A8] insights & recommendations (ranking, tie-breaks, caps)")
    titles = [i["title"] for i in out["insights"]]
    check("A", "strength insight = Strings (90.0 % ties Number Theory; larger sample wins)", "Strong submission accuracy in Strings" in titles, str(titles))
    check("A", "weakness insight = Math (10.0 % ties Binary Search; larger sample wins)", "Math may need more practice" in titles, str(titles))
    dips = sorted(t for t in titles if "rating dip" in t)
    want_dips = sorted(f"Recent {n.title() if n != 'codechef' else 'CodeChef'} rating dip" for n, e in exp["contests"].items() if e["dip"])
    check("A", "rating-dip insights for exactly Codeforces and CodeChef (not LeetCode)",
          dips == ["Recent CodeChef rating dip", "Recent Codeforces rating dip"], f"{dips} (oracle dips: {want_dips})")
    recs = out["recommendations"]
    got_order = [(r["priority"], r["topic"]) for r in recs[:5]]
    check("A", "recs: 3 High (Math, Binary Search, Sorting) then 2 Medium (DP, Stacks); Trees/Heaps cut by caps",
          got_order == [("High", "Math"), ("High", "Binary Search"), ("High", "Sorting"), ("Medium", "Dynamic Programming"), ("Medium", "Stacks")],
          str(got_order))
    check("A", "recommendations capped at 6", len(recs) == 6, f"len={len(recs)}")
    check("A", "no 'enable daily activity' nag when activity exists", not any("daily activity" in r["action"].lower() for r in recs))
    check("A", "Insufficient-Data topics (Greedy 0 %, Backtracking) never get a recommendation",
          not any(r["topic"] in ("Greedy", "Backtracking") for r in recs))
    check("A", "recommendation text quotes the correct counts (Math: 2 of 20)",
          "2 accepted out of 20" in recs[0]["reason"] and "10.0%" in recs[0]["reason"], recs[0]["reason"])

    print("\n[A9] data-quality accounting vs oracle")
    for k, e in exp["quality"].items():
        check("A", f"data_quality.{k} == {e!r}", dq[k] == e, f"engine={dq[k]!r} oracle={e!r}")
    check("A", "partial_data is True and pagination_integrity is False",
          dq["partial_data"] is True and dq["pagination_integrity"] is False)
    for m in ("exact_cross_platform_unique_solved", "complete_unique_topic_analytics",
              "complete_topic_submission_accuracy", "combined_total_attempted"):
        check("A", f"unavailable_metrics contains {m}", m in dq["unavailable_metrics"])
    check("A", "no false alarm for daily_activity_trend / contest_rating_trend",
          not {"daily_activity_trend", "contest_rating_trend"} & set(dq["unavailable_metrics"]))
    check("A", "overlapping numeric submission IDs on different platforms are NOT cross-de-duplicated",
          dq["judged_submission_count"] == exp["quality"]["judged_submission_count"])

    print("\n[A10] metamorphic / property tests")
    inv_base = invariants(out)
    check("A", "deterministic: identical output on a second run", out == run_engine(payload))
    rng = random.Random(99)
    for trial in range(3):
        shuffled = copy.deepcopy(payload)
        rng.shuffle(shuffled)
        for p in shuffled:
            for f in ("problem_activity", "submission_activity", "solved_problems"):
                if p.get(f):
                    rng.shuffle(p[f])
        d = diff(inv_base, invariants(run_engine(shuffled)))
        check("A", f"order-independent: shuffled platforms+records (trial {trial + 1})", not d, "; ".join(d[:3]))

    dup_payload = copy.deepcopy(payload)
    for p in dup_payload:
        p["submission_activity"] = p["submission_activity"] + [s for s in p["submission_activity"] if s["submission_id"]]
        p["problem_activity"] = p["problem_activity"] + copy.deepcopy(p["problem_activity"])
    o2 = run_engine(dup_payload)
    check("A", "idempotent: re-sending every id-bearing submission and every problem row changes no topic stat",
          o2["topic_analytics"] == out["topic_analytics"] and o2["overview"]["total_solved"] == ov["total_solved"],
          "; ".join(diff(out["topic_analytics"], o2["topic_analytics"])[:3]))

    up = copy.deepcopy(payload)
    for r in up[3]["problem_activity"]:  # GfG: SHOUT + pad every canonical ID
        if r["canonical_id"]:
            r["canonical_id"] = f"\t{r['canonical_id'].strip().upper()}  "
    check("A", "canonical IDs are case/whitespace-proof (GfG IDs re-cased+padded -> same unique count)",
          run_engine(up)["overview"]["total_solved"] == ov["total_solved"])

    no_hr = run_engine(payload[:-1])
    check("A", "adding an empty HackerRank profile changes no numbers (overview, topics, contests)",
          no_hr["overview"] == ov and no_hr["topic_analytics"] == out["topic_analytics"] and
          no_hr["contest_analytics"]["total_contests"] == out["contest_analytics"]["total_contests"])

    print("\n[A11] scenario: PERFECT data (everything present, nothing partial)")
    perfect = [
        {
            "platform_name": "LeetCode", "username": "perfect", "current_rating": 2000, "total_solved": 2,
            "correct_submissions": 3, "failed_submissions": 1, "total_attempted": 4,
            "solved_problems": [{"platform_problem_id": "a", "canonical_id": "p:a"}, {"platform_problem_id": "b", "canonical_id": "p:b"}],
            "problem_activity": [{"platform_problem_id": "a", "canonical_id": "p:a", "tags": ["dp"], "solved": True},
                                 {"platform_problem_id": "b", "canonical_id": "p:b", "tags": ["graph"], "solved": True}],
            "submission_activity": [
                {"submission_id": "1", "platform_problem_id": "a", "canonical_id": "p:a", "tags": ["dp"], "accepted": True},
                {"submission_id": "2", "platform_problem_id": "a", "canonical_id": "p:a", "tags": ["dp"], "accepted": False},
                {"submission_id": "3", "platform_problem_id": "b", "canonical_id": "p:b", "tags": ["graph"], "accepted": True},
                {"submission_id": "4", "platform_problem_id": "b", "canonical_id": "p:b", "tags": ["graph"], "accepted": True}],
            "contest_history": [{"timestamp": 1_750_000_000, "old_rating": 1990, "new_rating": 2000, "rating_change": 10}],
            "daily_activity": {"2026-10-01": 4}, "data_complete": True, "pagination_pages": 1,
        },
        {
            "platform_name": "Codeforces", "username": "perfect_cf", "current_rating": 1500, "total_solved": 1,
            "correct_submissions": 1, "failed_submissions": 0, "total_attempted": 1,
            "solved_problems": [{"platform_problem_id": "c", "canonical_id": "p:a"}],  # same underlying problem as LC 'a'
            "problem_activity": [{"platform_problem_id": "c", "canonical_id": "p:a", "tags": ["dp"], "solved": True}],
            "submission_activity": [{"submission_id": "9", "platform_problem_id": "c", "canonical_id": "p:a", "tags": ["dp"], "accepted": True}],
            "contest_history": [{"timestamp": 1_750_100_000, "old_rating": 1490, "new_rating": 1500, "rating_change": 10}],
            "daily_activity": {"2026-10-01": 1, "2026-10-02": 2}, "data_complete": True, "pagination_pages": 1,
        },
    ]
    po = run_engine(perfect)
    pdq = po["data_quality"]
    check("A", "unique solved = 2 (shared problem counted once), 1 duplicate, complete",
          (po["overview"]["total_solved"], po["overview"]["duplicate_solved_across_platforms"], po["overview"]["unique_solved_complete"]) == (2, 1, True),
          str(po["overview"]))
    check("A", "partial_data False and unavailable_metrics == []", pdq["partial_data"] is False and pdq["unavailable_metrics"] == [], str(pdq["unavailable_metrics"]))
    check("A", "pagination_integrity True, coverage flags all True",
          pdq["pagination_integrity"] is True and pdq["topic_tag_coverage_complete"] is True and pdq["canonical_id_coverage_complete"] is True)
    prow = {r["topic"]: r for r in po["topic_analytics"]}
    check("A", "DP: 2 unique problems? no - 1 unique problem, solved, 3 judged (2 accepted)",
          (prow["Dynamic Programming"]["attempted"], prow["Dynamic Programming"]["solved"], prow["Dynamic Programming"]["submission_count"],
           prow["Dynamic Programming"]["accepted_submissions"]) == (1, 1, 3, 2), str(prow["Dynamic Programming"]))

    print("\n[A12] scenario: COLD START (new user, nothing at all)")
    cold = run_engine([{"platform_name": "leetcode", "username": "newbie", "data_complete": True}])
    check("A", "no crash; zero totals; success_rate None; no topics",
          cold["overview"]["total_solved"] == 0 and cold["overview"]["success_rate"] is None and cold["topic_analytics"] == [])
    check("A", "cold start gets the Low-priority 'enable daily activity' recommendation",
          [r["priority"] for r in cold["recommendations"]] == ["Low"])
    check("A", "platform name normalised ('leetcode' -> 'LeetCode')", cold["platform_comparison"][0]["platform"] == "LeetCode")


# ----------------------------------------------------------------------------------------------
# PART B - probes for problems found in review
# ----------------------------------------------------------------------------------------------
def part_b(payload: list[dict]) -> None:
    section("PART B - KNOWN-ISSUE PROBES (BUG = still present, OK = fixed)")
    lc = lambda **k: {"platform_name": "LeetCode", "username": "u", **k}  # noqa: E731

    # B1 float ratings
    try:
        AnalysisRequest.model_validate({"platforms": [lc(current_rating=1823.45)]})
        bug, ev = False, "accepted"
    except Exception as e:  # noqa: BLE001
        bug, ev = True, f"422 validation error: {str(e).splitlines()[2].strip()}"
    probe("B1 LeetCode fractional rating (e.g. 1823.45) is accepted", bug,
          "importer can send LeetCode's float ratings", ev)

    # B2 ms timestamp
    try:
        run_engine([lc(contest_history=[{"timestamp": 1_700_000_000_000, "new_rating": 1500, "rating_change": 10}])])
        bug, ev = False, "handled"
    except Exception as e:  # noqa: BLE001
        bug, ev = True, f"{type(e).__name__}: {e} (would be HTTP 500)"
    probe("B2 millisecond contest timestamp is rejected cleanly (422) or normalised", bug,
          "no unhandled exception", ev)

    # B3 hyphen vs space for unknown tags
    a, b = normalize_topic("divide-and-conquer"), normalize_topic("divide and conquer")
    probe("B3 unknown tags differing only by hyphen/space merge into one topic", a != b,
          "'divide-and-conquer' == 'divide and conquer'", f"{a!r} vs {b!r}")

    # B4 CF/LC vocabulary
    pairs = [("dfs and similar", "Depth-First Search"), ("graph theory", "graphs"), ("bitmasks", "bit manipulation"),
             ("shortest paths", "shortest path"), ("hashing", "hash table"), ("sortings", "sorting"),
             ("heap (priority queue)", "priority queue"), ("divide-and-conquer", "divide and conquer")]
    split = [(x, y) for x, y in pairs if normalize_topic(x) != normalize_topic(y)]
    probe("B4 Codeforces tag names merge with their LeetCode equivalents", bool(split),
          "same concept -> same topic row", f"{len(split)}/{len(pairs)} pairs stay separate: {split}")

    # B5 mixed detail / no detail
    det = lc(total_solved=3, problem_activity=[{"platform_problem_id": f"a{i}", "canonical_id": f"c{i}", "tags": ["math"], "solved": True} for i in range(3)], data_complete=True)
    bare = {"platform_name": "GFG", "username": "g", "total_solved": 200, "data_complete": True}
    o = run_engine([det, bare])["overview"]
    probe("B5 headline total_solved is never below the biggest single-profile count", o["total_solved"] < 200,
          "total_solved >= 200 (unique solves across profiles >= any one profile's solves)",
          f"total_solved={o['total_solved']} while platforms reported {o['platform_reported_solved']}")

    # B6 legacy topics dropped when another profile has problem_activity
    act = lc(total_solved=1, problem_activity=[{"platform_problem_id": "a", "canonical_id": "c1", "tags": ["math"], "solved": True}], data_complete=True)
    leg = {"platform_name": "GFG", "username": "g", "total_solved": 50, "topics": [{"tag_name": "graph", "solved_count": 30, "attempted_count": 40}], "data_complete": True}
    topics = [r["topic"] for r in run_engine([act, leg])["topic_analytics"]]
    probe("B6 a profile that only sends legacy `topics` is not silently dropped from topic analytics", "Graphs" not in topics,
          "Graphs (30/40) present, or an explicit warning", f"topics returned: {topics}")

    # B7 rating_change-only contests
    ch = [-10, -20, -30, 5]
    o = run_engine([lc(contest_history=[{"timestamp": 1_700_000_000 + i * 86400, "rating_change": c} for i, c in enumerate(ch)])])
    cp = o["contest_analytics"]["platforms"][0]
    has_dip = any("rating dip" in i["title"] for i in o["insights"])
    probe("B7 contests with only rating_change (no old/new rating) still feed dip insight/recommendation",
          not has_dip, "dip insight (last three changes sum to -45)",
          f"avg_change={cp['average_rating_change']} but plotted points={len(cp['rating_history'])}, dip insight={has_dip}")

    # B8 contradictory totals
    bad = lc(correct_submissions=500, failed_submissions=10, data_complete=True,
             submission_activity=[{"submission_id": str(i), "platform_problem_id": "p", "tags": ["Trees"], "accepted": False} for i in range(20)])
    o = run_engine([bad])
    flagged = ("consistent_submission_totals" in o["data_quality"]["unavailable_metrics"]) or any(
        w in n.lower() for n in o["data_quality"]["notes"] for w in ("mismatch", "inconsisten", "reconcil", "disagree"))
    probe("B8 platform totals that contradict submission_activity are flagged", not flagged,
          "a data-quality note about the mismatch",
          f"overall success_rate={o['overview']['success_rate']}% but topic accuracy={o['topic_analytics'][0]['submission_success_rate']}%, flagged={flagged}")

    # B9 legacy topics-only never classifies -> the ENGINE is deliberate; the root README is what is stale
    import os
    leg2 = lc(total_solved=100, correct_submissions=60, failed_submissions=140, total_attempted=200, data_complete=True,
              topics=[{"tag_name": "dp", "solved_count": 5, "attempted_count": 60}])
    cls = run_engine([leg2])["topic_analytics"][0]["classification"]
    readme = ""
    if os.path.exists("README.md"):
        with open("README.md", encoding="utf-8") as fh:
            readme = fh.read()
    stale = [m for m in ("sum of platform-reported solved counts", "is at least 5", "returns `user`") if m in readme]
    probe("B9 root README.md matches the real behaviour (legacy `topics` alone never produces a weakness)",
          bool(stale) and cls == "Insufficient Data",
          "README describes the submission-accuracy rules (>=10 judged submissions, user_summary key, unique totals)",
          f"stale claims still in README.md: {stale}" if stale else f"README ok; legacy-only classification={cls} (documented)")

    # B10 platform names
    names = {n: normalize_platform_name(n) for n in ("AtCoder", "HackerRank", "HackerEarth", "CSES")}
    mangled = {k: v for k, v in names.items() if k != v}
    probe("B10 platform display names keep their official capitalisation", bool(mangled), "AtCoder, HackerRank, ...", f"mangled: {mangled}")

    # B11 whitespace-only required id
    try:
        v = SolvedProblem(platform_problem_id="   ").platform_problem_id
        bug, ev = True, f"accepted and silently became {v!r}"
    except Exception as e:  # noqa: BLE001
        bug, ev = False, "rejected with a validation error"
    probe("B11 whitespace-only platform_problem_id is rejected (required field)", bug, "422 validation error", ev)

    # B12 submission-only topic shows solved=0
    sub_only = lc(data_complete=True, submission_activity=[{"submission_id": str(i), "platform_problem_id": "p", "tags": ["Trees"], "accepted": i % 2 == 0} for i in range(20)])
    row = run_engine([sub_only])["topic_analytics"][0]
    probe("B12 topic known only from submissions reports solved=None, not a fake 0", row["solved"] == 0,
          "solved None/unknown (no problem records were supplied)", f"solved={row['solved']}, attempted={row['attempted']}")

    # B13 order dependence
    fwd = run_engine(payload)
    rev = run_engine(list(reversed(payload)))
    rec_f = [r["action"][:40] for r in fwd["recommendations"]]
    rec_r = [r["action"][:40] for r in rev["recommendations"]]
    order_f = [c["platform"] for c in fwd["contest_analytics"]["platforms"]]
    order_r = [c["platform"] for c in rev["contest_analytics"]["platforms"]]
    probe("B13 recommendations and contest_analytics.platforms do not depend on input platform order",
          rec_f != rec_r or order_f != order_r, "identical output for any platform order",
          f"6th recommendation fwd={rec_f[5]!r} vs reversed={rec_r[5]!r}; contest order {order_f[:2]} vs {order_r[:2]}")

    # B14 conflicting duplicate submission ids
    mk = lambda flags: lc(data_complete=True, submission_activity=[  # noqa: E731
        {"submission_id": "1", "platform_problem_id": "p", "tags": ["Trees"], "accepted": f} for f in flags])
    a1 = run_engine([mk([False, True])])["topic_analytics"][0]["accepted_submissions"]
    a2 = run_engine([mk([True, False])])["topic_analytics"][0]["accepted_submissions"]
    probe("B14 same submission_id sent twice with different verdicts gives an order-independent result", a1 != a2,
          "same count either way", f"[fail,ok] -> {a1} accepted, [ok,fail] -> {a2} accepted")

    # B15 hard-coded 'Codeforces' in note
    o = run_engine([lc(data_complete=True, problemset_lookup_misses=2,
                       submission_activity=[{"submission_id": "1", "platform_problem_id": "p", "tags": [], "accepted": True}])])
    leaked = any("Codeforces" in n for n in o["data_quality"]["notes"])
    probe("B15 data-quality note does not mention Codeforces for a LeetCode-only user", leaked,
          "platform-neutral wording", "a note says 'missing from the fetched Codeforces problemset'" if leaked else "ok")

    # B16 nonsense '0 solved entries' note
    o = run_engine([lc(total_solved=1, data_complete=False, problem_activity=[{"platform_problem_id": "a", "canonical_id": "c", "tags": ["math"], "solved": True}])])
    odd = [n for n in o["data_quality"]["notes"] if n.startswith("0 solved entries")]
    probe("B16 no '0 solved entries lack a reliable canonical identity ... lower bound' note", bool(odd),
          "note only when unresolved_solved_count > 0", odd[0][:90] if odd else "ok")


# ----------------------------------------------------------------------------------------------
# PART C - HTTP
# ----------------------------------------------------------------------------------------------
def part_c(payload: list[dict], out: dict) -> None:
    section("PART C - END-TO-END HTTP (FastAPI TestClient) + SCALE")
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:  # noqa: BLE001
        print(f"  (skipped: could not import FastAPI test client: {e})")
        return
    c = TestClient(app, raise_server_exceptions=False)
    body = {"display_name": "Hard Mode Tester", "platforms": payload}

    r = c.post("/api/v1/analysis", json=body)
    check("C", "POST persona -> 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    if r.status_code == 200:
        check("C", "HTTP JSON body == direct engine output", r.json() == json.loads(json.dumps(out)), "; ".join(diff(out, r.json())[:3]))
        check("C", "all 9 top-level dashboard sections present",
              {"user_summary", "overview", "platform_comparison", "topic_analytics", "contest_analytics", "charts", "insights", "recommendations", "data_quality"} <= set(r.json()))
    for path in ("/", "/health", "/openapi.json"):
        check("C", f"GET {path} -> 200", c.get(path).status_code == 200)
    check("C", "OpenAPI documents POST /api/v1/analysis", "/api/v1/analysis" in c.get("/openapi.json").json()["paths"])

    base = lambda: copy.deepcopy(body)  # noqa: E731

    def mutate(fn):
        b = base()
        fn(b["platforms"][0])
        return c.post("/api/v1/analysis", json=b).status_code

    cases = {
        "missing username": lambda p: p.pop("username"),
        "blank username": lambda p: p.update(username="   "),
        "negative total_solved": lambda p: p.update(total_solved=-1),
        "string for total_solved": lambda p: p.update(total_solved="lots"),
        "impossible date 2026-02-30": lambda p: p.update(daily_activity={"2026-02-30": 1}),
        "wrong date format": lambda p: p.update(daily_activity={"01-11-2026": 1}),
        "negative daily count": lambda p: p.update(daily_activity={"2026-11-01": -4}),
        "contest rank 0": lambda p: p["contest_history"][0].update(rank=0),
        "negative timestamp": lambda p: p["contest_history"][0].update(timestamp=-5),
        "submission without accepted flag": lambda p: p["submission_activity"][0].pop("accepted"),
        "tags as a string": lambda p: p["submission_activity"][0].update(tags="dp"),
        "null tag inside list": lambda p: p["submission_activity"][0].update(tags=[None]),
    }
    for name, fn in cases.items():
        code = mutate(fn)
        check("C", f"invalid input '{name}' -> 422 (not 500)", code == 422, f"HTTP {code}")
    check("C", "empty platforms list -> 422", c.post("/api/v1/analysis", json={"platforms": []}).status_code == 422)
    check("C", "null body -> 422", c.post("/api/v1/analysis", json=None).status_code == 422)
    check("C", "non-JSON body -> 422", c.post("/api/v1/analysis", content=b"hello", headers={"content-type": "application/json"}).status_code == 422)
    b = base()
    b["platforms"][0]["totally_unknown_field"] = {"x": 1}
    b["platforms"][0]["submission_activity"][0]["verdict_text"] = "WA on test 7"
    check("C", "unknown extra fields are ignored (forward-compatible importer) -> 200", c.post("/api/v1/analysis", json=b).status_code == 200)
    pre = c.options("/api/v1/analysis", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    check("C", "CORS preflight allows the Vite dev origin", pre.headers.get("access-control-allow-origin") == "http://localhost:5173")
    bad = c.options("/api/v1/analysis", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    check("C", "CORS preflight rejects an unknown origin", bad.headers.get("access-control-allow-origin") is None)

    print("\n[C-scale] 5 profiles x (10k problems + 20k submissions) = 100k judged submissions, 2 tags each")
    rng = random.Random(1)
    tags = ["dp", "graphs", "trees", "math", "greedy", "strings", "arrays", "binary search"]
    big = []
    for i, name in enumerate(["LeetCode", "Codeforces", "CodeChef", "GeeksforGeeks", "AtCoder"]):
        big.append({
            "platform_name": name, "username": f"scale{i}", "total_solved": 6000, "correct_submissions": 10000,
            "failed_submissions": 10000, "total_attempted": 20000, "data_complete": True,
            "problem_activity": [{"platform_problem_id": f"{i}-{k}", "canonical_id": f"c{k % 8000}", "tags": rng.sample(tags, 2), "solved": rng.random() < .6} for k in range(10000)],
            "submission_activity": [{"submission_id": f"{i}-{k}", "platform_problem_id": f"{i}-{k % 10000}", "canonical_id": f"c{k % 8000}", "tags": rng.sample(tags, 2), "accepted": rng.random() < .5} for k in range(20000)],
        })
    t0 = time.perf_counter()
    so = run_engine(big)
    dt = time.perf_counter() - t0
    check("C", f"scale run finished in {dt:.1f}s (limit 30s)", dt < 30)
    check("C", "judged_submission_count == 100000", so["data_quality"]["judged_submission_count"] == 100_000)
    check("C", "sum of per-topic judged counts == 2 x judged (every submission has exactly 2 distinct tags)",
          sum(r["submission_count"] for r in so["topic_analytics"]) == 200_000)
    check("C", "every topic row: accepted + failed == submission_count and solved <= attempted",
          all(r["accepted_submissions"] + r["failed_submissions"] == r["submission_count"] and r["solved"] <= r["attempted"] for r in so["topic_analytics"]))
    check("C", "unique problems capped by canonical pool (<= 8000)", so["overview"]["total_solved"] <= 8000, str(so["overview"]["total_solved"]))


# ----------------------------------------------------------------------------------------------
# report
# ----------------------------------------------------------------------------------------------
def print_report(out: dict) -> None:
    section("HARD PERSONA - ENGINE OUTPUT SNAPSHOT")
    ov = out["overview"]
    print("OVERVIEW")
    for k, v in ov.items():
        print(f"  {k:36} {v}")
    print("\nPLATFORMS")
    for r in out["platform_comparison"]:
        print(f"  {r['platform']:15} solved={r['solved']:4} rating={str(r['current_rating']):5} "
              f"acc/fail={r['correct_submissions']}/{r['failed_submissions']} ({r['submission_success_rate']}%) contests={r['contests_participated']}")
    print("\nTOPICS (judged submissions -> accuracy -> class | unique problems solved/attempted)")
    for r in out["topic_analytics"]:
        print(f"  {r['topic']:22} {str(r['accepted_submissions']):>4}/{str(r['submission_count']):<4} {str(r['submission_success_rate']):>6}%  "
              f"{r['classification']:18} | {r['solved']}/{r['attempted']}")
    print("\nCONTESTS")
    for c in out["contest_analytics"]["platforms"]:
        print(f"  {c['platform']:15} n={c['total_contests']} +{c['positive_changes']}/-{c['negative_changes']} avg={c['average_rating_change']} best={c['best_rating']} latest={c['latest_rating']}")
    print("\nINSIGHTS")
    for i in out["insights"]:
        print(f"  [{i['type']}] {i['title']}")
    print("\nRECOMMENDATIONS")
    for r in out["recommendations"]:
        print(f"  [{r['priority']}] {r['topic'] or '-'}: {r['action'][:88]}")
    print("\nDATA QUALITY:", out["data_quality"]["unavailable_metrics"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 if any Part B bug is still present")
    ap.add_argument("--dump", metavar="DIR", help="write payload.json and response.json to DIR")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    payload = build_persona(args.seed)
    out = run_engine(payload)
    n_sub = sum(len(p["submission_activity"]) for p in payload)
    n_prob = sum(len(p["problem_activity"]) for p in payload)
    print(f"Persona: {len(payload)} profiles, {n_prob} problem rows, {n_sub} submission rows (incl. injected duplicates), "
          f"{sum(len(p['contest_history']) for p in payload)} contest records")
    print_report(out)

    if args.dump:
        import os
        os.makedirs(args.dump, exist_ok=True)
        with open(os.path.join(args.dump, "payload.json"), "w", encoding="utf-8") as fh:
            json.dump({"display_name": "Hard Mode Tester", "platforms": payload}, fh, indent=2, ensure_ascii=False)
        with open(os.path.join(args.dump, "response.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        print(f"\nWrote payload.json / response.json to {args.dump}")

    part_a(payload, out)
    part_b(payload)
    part_c(payload, out)

    section("SCOREBOARD")
    for part, label in (("A", "Part A  engine correctness"), ("C", "Part C  HTTP + scale")):
        rs = [r for r in RESULTS if r[0] == part]
        bad = [r for r in rs if r[2] == "FAIL"]
        print(f"  {label:32} {len(rs) - len(bad)}/{len(rs)} passed")
        for r in bad:
            print(f"      FAIL: {r[1]}  ({r[3][:140]})")
    pb = [r for r in RESULTS if r[0] == "B"]
    bugs = [r for r in pb if r[2] == "BUG"]
    print(f"  {'Part B  known-issue probes':32} {len(bugs)} bug(s) present, {len(pb) - len(bugs)} fixed/OK (of {len(pb)})")
    failed = any(r[2] == "FAIL" for r in RESULTS)
    if failed or (args.strict and bugs):
        return 1
    print("\nNo hard failures in Parts A and C." + ("" if not bugs else f" {len(bugs)} Part B issue(s) still open - see above."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
