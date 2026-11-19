#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Validate a service-handoff.yaml against the hand-off contract.

Usage:
  uv run registry-bridge/scripts/validate_handoff.py path/to/service-handoff.yaml

Checks the JSON Schema (references/handoff.schema.json), then what a schema
cannot: unique ids, pages that ask or show known questions, branches to known
pages, one row for each of the 13 gaps, form items only when a form spec is a
source, and unresolved rows that point at something real.

Exit code 0 when valid, 1 when not. Errors go to stdout, one per line.
"""

import json
import os
import sys

import yaml
from jsonschema import Draft202012Validator

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema():
    with open(os.path.join(REFS, "handoff.schema.json"), encoding="utf-8") as f:
        return json.load(f)


def load_required_from():
    with open(os.path.join(REFS, "required-from.json"), encoding="utf-8") as f:
        return json.load(f)


def source_paths(doc):
    """Every file path the hand-off cites as a source, relative to the repo root."""
    s = doc["sources"]
    paths = [s[k] for k in ("profile", "service_sheet", "brief", "shared_assumptions", "form_spec") if s.get(k)]
    paths += [s["prototype"]["page"], s["prototype"]["assumptions"]]
    return paths


def _dupes(ids):
    seen, out = set(), []
    for i in ids:
        if i in seen:
            out.append(i)
        seen.add(i)
    return out


def schema_errors(doc):
    errors = []
    for e in sorted(Draft202012Validator(load_schema()).iter_errors(doc), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(p) for p in e.absolute_path) or "(top)"
        errors.append(f"{where}: {e.message}")
    return errors


def validate(doc):
    errors = schema_errors(doc)
    if errors:
        return errors

    q_ids = [q["id"] for q in doc["questions"]]
    p_ids = [p["id"] for p in doc["pages"]]
    b_ids = [b["id"] for b in doc["back_office"]]
    o_ids = [o["id"] for o in doc["open_items"]]
    f_ids = [f["id"] for f in doc["form_items"]]
    for kind, ids in (("question", q_ids), ("page", p_ids), ("back-office", b_ids), ("open item", o_ids), ("form item", f_ids)):
        errors += [f"duplicate {kind} id '{i}'" for i in _dupes(ids)]

    questions = set(q_ids)
    pages = set(p_ids)
    for q in doc["questions"]:
        if q["map"] in ("known", "derived") and not q["source"]:
            errors.append(f"question '{q['id']}': a {q['map']} question needs a source")
        if q["map"] == "known" and not q["attribute"]:
            errors.append(f"question '{q['id']}': a known question needs an attribute key")
        for f in q.get("form_items", []):
            if f not in f_ids:
                errors.append(f"question '{q['id']}': unknown form item '{f}'")

    for p in doc["pages"]:
        for q in p["asks"] + p["shows"]:
            if q not in questions:
                errors.append(f"page '{p['id']}': unknown question '{q}'")
        for n in p["next"]:
            if n["to"] not in pages:
                errors.append(f"page '{p['id']}': branch to unknown page '{n['to']}'")

    for f in doc["form_items"]:
        if f.get("question") and f["question"] not in questions:
            errors.append(f"form item '{f['id']}': unknown question '{f['question']}'")

    gap_ids = sorted(g["id"] for g in doc["gaps"])
    errors += [f"gaps: more than one row for gap {g}" for g in _dupes(gap_ids)]
    for g in range(1, 14):
        if g not in gap_ids:
            errors.append(f"gaps: no row for gap {g}")

    missing = {m["part"] for m in doc["missing_parts"]}
    has_spec = doc["sources"]["form_spec"] is not None
    if has_spec and "form-spec" in missing:
        errors.append("missing_parts: lists form-spec, but sources.form_spec is set")
    if not has_spec and "form-spec" not in missing:
        errors.append("missing_parts: sources.form_spec is null, so declare form-spec as missing")
    if not has_spec and doc["form_items"]:
        errors.append("form_items: there is no form spec (form-spec is missing), so form_items must be empty")

    known_refs = {
        "questions": questions, "pages": pages, "back_office": set(b_ids), "open_items": set(o_ids),
        "form_items": set(f_ids), "gaps": {str(g) for g in gap_ids}, "sources": set(doc["sources"]),
    }
    def check_ref(where, ref):
        section, _, key = ref.partition("/")
        if key and key not in known_refs[section]:
            errors.append(f"{where}: '{ref}' points at nothing")
    for u in doc["unresolved"]:
        check_ref("unresolved", u["ref"])
    for o in doc["open_items"]:
        for r in o.get("refs", []):
            check_ref(f"open item '{o['id']}'", r)
    for g in doc["gaps"]:
        for r in g.get("refs", []):
            check_ref(f"gap {g['id']}", r)
    return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip())
        return 2
    errors = validate(load(argv[0]))
    if errors:
        print(f"{argv[0]}: {len(errors)} error(s)")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"{argv[0]}: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
