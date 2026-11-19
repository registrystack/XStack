#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Scripted checks for design-to-handoff eval runs.

Usage:
  uv run registry-bridge/skills/design-to-handoff/evals/grade.py GENERATED.yaml --eval-id N [--out grading.json]

Reads evals.json next to this script, which names the hand-written ground
truth for each eval. Compares a generated service-handoff.yaml with it:

  1. valid against the hand-off contract
  2. same level
  3. same prototype and iteration
  4. same missing parts
  5. coverage: every ground-truth question has a matching row
  6. known, derived or ask agrees on every matched question
  7. attribute key agrees on every matched question
  8. every attribute key is in the profile's data catalogue
  9. every ground-truth tag is kept on its question
 10. form controls agree on every matched question
 11. a fallback wherever the ground truth has one
 12. same pages in the same order
 13. every ground-truth branch is there
 14. each page asks and shows the same questions
 15. back-office rows: at least 80% of the ground truth's are found
 16. open items: same number, and tags agree on at least 90%
 17. gaps: status agrees on at least 10 of 13
 18. every unresolved row in the ground truth is also flagged

A question is matched by attribute key first, then by shared form controls,
then by id. Writes grading.json in the skill-creator format:
{expectations: [{text, passed, evidence}], summary}.
Wording of labels, notes and texts is for a person or a grader agent.
"""

import argparse
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.dirname(BRIDGE)
sys.path.insert(0, os.path.join(BRIDGE, "scripts"))

import validate_handoff  # noqa: E402

WORD = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "of", "to", "and", "or", "for", "in", "on", "at", "is", "it", "by", "with", "when", "their", "its", "that", "this", "from"}

# The 18 checks, in order. grade() uses these words, except that coverage names the count.
CHECKS = [
    "Valid against the hand-off contract",
    "Same level as the ground truth",
    "Same prototype and iteration",
    "Same missing parts declared",
    "Coverage: all ground-truth questions have a matching row",
    "Known, derived or ask agrees on every matched question",
    "Attribute key agrees on every matched question",
    "Every attribute key is in the profile's data catalogue",
    "Every ground-truth tag is kept on its question",
    "Form controls agree on every matched question",
    "A fallback wherever the ground truth has one",
    "Same pages in the same order",
    "Every ground-truth branch is there",
    "Each page asks and shows the same questions",
    "Back-office rows: at least 80% of the ground truth's are found",
    "Open items: same number, and tags agree on at least 90%",
    "Gaps: status agrees on at least 10 of 13",
    "Every unresolved row in the ground truth is also flagged",
]


def load(path):
    return validate_handoff.load(path)


def catalogue_keys(profile_dir):
    """Attribute keys in the profile's data catalogue (dpi.md), or None without a profile."""
    if not profile_dir:
        return None
    path = os.path.join(REPO, profile_dir, "dpi.md")
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^## Data catalogue\s*$(.*?)(?=^## )", text, re.M | re.S)
    body = m.group(1) if m else text
    return set(re.findall(r"^\|\s*`([A-Za-z0-9_]+)`\s*\|", body, re.M))


def match_questions(gen, truth):
    """Return {truth_id: gen_question} for every truth question that has a match."""
    pairs, used = {}, set()
    for t in truth["questions"]:
        cands = [g for g in gen["questions"] if g["id"] not in used]
        hit = None
        if t["attribute"]:
            hit = next((g for g in cands if g["attribute"] == t["attribute"]), None)
        if hit is None and t["fields"]:
            hit = max(cands, key=lambda g: len(set(g["fields"]) & set(t["fields"])), default=None)
            if hit is not None and not set(hit["fields"]) & set(t["fields"]):
                hit = None
        if hit is None:
            hit = next((g for g in cands if g["id"] == t["id"]), None)
        if hit is not None:
            pairs[t["id"]] = hit
            used.add(hit["id"])
    return pairs


def words(*texts):
    return {w for t in texts for w in WORD.findall((t or "").lower()) if w not in STOP}


def match_back_office(gen, truth, threshold=0.25):
    found, used = [], set()
    for t in truth["back_office"]:
        tw = words(t["what"], t["trigger"])
        best, score = None, 0.0
        for g in gen["back_office"]:
            if g["id"] in used:
                continue
            gw = words(g["what"], g["trigger"])
            s = len(tw & gw) / len(tw | gw) if tw | gw else 0.0
            if s > score:
                best, score = g, s
        if best is not None and score >= threshold:
            found.append(t["id"])
            used.add(best["id"])
    return found


def edges(doc):
    return {(p["id"], n["to"]) for p in doc["pages"] for n in p["next"]}


def grade(gen, truth):
    results = []

    def add(text, passed, evidence):
        results.append({"text": text, "passed": bool(passed), "evidence": evidence})

    errors = validate_handoff.validate(gen)
    add("Valid against the hand-off contract", not errors, "; ".join(errors[:5]) or "valid")
    if validate_handoff.schema_errors(gen):
        # The wrong shape: nothing below can be compared, so every other check fails.
        for text in CHECKS[1:]:
            add(text, False, "not compared: the file does not match the contract's schema")
        return summarise(results)

    add("Same level as the ground truth", gen["level"] == truth["level"], f"{gen['level']} vs {truth['level']}")

    gp, tp = gen["sources"]["prototype"], truth["sources"]["prototype"]
    same = (gp["name"], gp["iteration"]) == (tp["name"], tp["iteration"])
    add("Same prototype and iteration", same, f"{gp['name']} iteration {gp['iteration']} vs {tp['name']} iteration {tp['iteration']}")

    gm = sorted(m["part"] for m in gen["missing_parts"])
    tm = sorted(m["part"] for m in truth["missing_parts"])
    add("Same missing parts declared", gm == tm, f"{gm} vs {tm}")

    pairs = match_questions(gen, truth)
    missing = [t["id"] for t in truth["questions"] if t["id"] not in pairs]
    add(f"Coverage: all {len(truth['questions'])} ground-truth questions have a matching row",
        not missing, f"missing: {missing}" if missing else f"all matched ({len(gen['questions'])} rows generated)")

    tq = {q["id"]: q for q in truth["questions"]}
    bad_map = [f"{t}: {g['map']} not {tq[t]['map']}" for t, g in pairs.items() if g["map"] != tq[t]["map"]]
    add("Known, derived or ask agrees on every matched question", not bad_map, "; ".join(bad_map) or "all agree")

    bad_attr = [f"{t}: {g['attribute']} not {tq[t]['attribute']}" for t, g in pairs.items() if g["attribute"] != tq[t]["attribute"]]
    add("Attribute key agrees on every matched question", not bad_attr, "; ".join(bad_attr) or "all agree")

    keys = catalogue_keys(gen["sources"]["profile"])
    used_keys = sorted({q["attribute"] for q in gen["questions"] if q["attribute"]})
    if keys is None:
        add("Every attribute key is in the profile's data catalogue", not used_keys,
            f"no catalogue, keys used: {used_keys}" if used_keys else "no catalogue and no keys used")
    else:
        invented = [k for k in used_keys if k not in keys]
        add("Every attribute key is in the profile's data catalogue", not invented,
            f"not in the catalogue: {invented}" if invented else f"{len(used_keys)} keys, all in the catalogue")

    lost = []
    for t, g in pairs.items():
        gone = sorted(set(tq[t]["tags"]) - set(g["tags"]))
        if gone:
            lost.append(f"{t}: {gone}")
    add("Every ground-truth tag is kept on its question", not lost, "; ".join(lost) or "all kept")

    bad_fields = [f"{t}: {sorted(g['fields'])} not {sorted(tq[t]['fields'])}" for t, g in pairs.items()
                  if set(g["fields"]) != set(tq[t]["fields"])]
    add("Form controls agree on every matched question", not bad_fields, "; ".join(bad_fields) or "all agree")

    no_fb = [t for t, g in pairs.items() if tq[t]["fallback"] and not g["fallback"]]
    add("A fallback wherever the ground truth has one", not no_fb, f"no fallback: {no_fb}" if no_fb else "all present")

    gids = [p["id"] for p in gen["pages"]]
    tids = [p["id"] for p in truth["pages"]]
    add("Same pages in the same order", gids == tids,
        "same" if gids == tids else f"generated: {gids}; ground truth: {tids}")

    lost_edges = sorted(edges(truth) - edges(gen))
    add("Every ground-truth branch is there", not lost_edges,
        f"missing: {lost_edges}" if lost_edges else f"{len(edges(truth))} branches, all there")

    rename = {g["id"]: t for t, g in pairs.items()}
    gpages = {p["id"]: p for p in gen["pages"]}
    bad_pages = []
    for p in truth["pages"]:
        g = gpages.get(p["id"])
        if g is None:
            continue
        for key in ("asks", "shows"):
            got = {rename.get(q, q) for q in g[key]}
            if got != set(p[key]):
                bad_pages.append(f"{p['id']}.{key}: {sorted(got)} not {sorted(p[key])}")
    add("Each page asks and shows the same questions", not bad_pages, "; ".join(bad_pages) or "all agree")

    found = match_back_office(gen, truth)
    need = 0.8 * len(truth["back_office"])
    lost_bo = [b["id"] for b in truth["back_office"] if b["id"] not in found]
    add("Back-office rows: at least 80% of the ground truth's are found", len(found) >= need,
        f"{len(found)} of {len(truth['back_office'])} found; not found: {lost_bo}")

    gtags = {o["id"]: set(o["tags"]) for o in gen["open_items"]}
    agree = sum(1 for o in truth["open_items"] if gtags.get(o["id"]) == set(o["tags"]))
    n = len(truth["open_items"])
    add("Open items: same number, and tags agree on at least 90%",
        len(gen["open_items"]) == n and agree >= 0.9 * n,
        f"{len(gen['open_items'])} generated vs {n}; tags agree on {agree}")

    gs = {g["id"]: g["status"] for g in gen["gaps"]}
    gap_agree = [g["id"] for g in truth["gaps"] if gs.get(g["id"]) == g["status"]]
    differ = [f"{g['id']}: {gs.get(g['id'])} not {g['status']}" for g in truth["gaps"] if g["id"] not in gap_agree]
    add("Gaps: status agrees on at least 10 of 13", len(gap_agree) >= 10,
        f"{len(gap_agree)} agree; differ: {differ}")

    gref = {u["ref"] for u in gen["unresolved"]}
    trefs = []
    for u in truth["unresolved"]:
        section, _, key = u["ref"].partition("/")
        if section == "questions" and key in pairs:
            trefs.append(f"questions/{pairs[key]['id']}")
        else:
            trefs.append(u["ref"])
    hidden = [r for r in trefs if r not in gref]
    add("Every unresolved row in the ground truth is also flagged", not hidden,
        f"not flagged: {hidden}" if hidden else f"{len(trefs)} flagged; generated flags {len(gref)}")

    return summarise(results)


def summarise(results):
    passed = sum(r["passed"] for r in results)
    return {"expectations": results,
            "summary": {"passed": passed, "failed": len(results) - passed, "total": len(results),
                        "pass_rate": round(passed / len(results), 3)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("generated")
    ap.add_argument("--eval-id", type=int, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    evals = {e["id"]: e for e in json.load(open(os.path.join(HERE, "evals.json"), encoding="utf-8"))["evals"]}
    truth = load(os.path.join(REPO, evals[a.eval_id]["ground_truth"]))
    res = grade(load(a.generated), truth)
    s = json.dumps(res, indent=2, ensure_ascii=False)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(s)
    print(s)


if __name__ == "__main__":
    main()
