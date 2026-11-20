"""Tests for the hand-off contract: the schema, the required-from table and the HSG pilot.

Run from the repository root:
  uv run --with pytest --with jsonschema --with pyyaml pytest registry-bridge/tests
"""

import copy
import json
import os
import sys

import pytest

BRIDGE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BRIDGE, "scripts"))

import validate_handoff as vh  # noqa: E402

PILOT = os.path.join(BRIDGE, "pilots", "household-support-grant", "service-handoff.yaml")


@pytest.fixture()
def hsg():
    return vh.load(PILOT)


def test_schema_is_a_valid_json_schema():
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(vh.load_schema())


def test_required_from_table_covers_the_13_gaps_at_every_level():
    table = vh.load_required_from()
    assert [g["id"] for g in table["gaps"]] == list(range(1, 14))
    for g in table["gaps"]:
        assert set(g["requires"]) == {"alpha", "beta", "live"}, g["id"]
        assert all(g["requires"][lvl].strip() for lvl in ("alpha", "beta", "live"))


def test_hsg_pilot_is_valid(hsg):
    assert vh.validate(hsg) == []


def test_hsg_pilot_is_alpha_and_names_its_prototype(hsg):
    assert hsg["level"] == "alpha"
    proto = hsg["sources"]["prototype"]
    assert proto["name"] == "prototype-1-once-only"
    assert proto["iteration"] == 4
    assert proto["why"].strip()


def test_hsg_pilot_declares_no_form_spec(hsg):
    assert hsg["sources"]["form_spec"] is None
    assert "form-spec" in [m["part"] for m in hsg["missing_parts"]]
    assert hsg["form_items"] == []


def test_hsg_pilot_paths_exist(hsg):
    repo = os.path.dirname(BRIDGE)
    for path in vh.source_paths(hsg):
        assert os.path.exists(os.path.join(repo, path)), path


def errors_for(doc):
    return "\n".join(vh.validate(doc))


def test_rejects_unknown_level(hsg):
    hsg["level"] = "discovery"
    assert "level" in errors_for(hsg)


def test_rejects_unknown_map_value(hsg):
    hsg["questions"][0]["map"] = "lookup"
    assert "map" in errors_for(hsg)


def test_rejects_unknown_tag(hsg):
    hsg["questions"][0]["tags"] = ["[VERIFY WITH SOMEONE]"]
    assert "tags" in errors_for(hsg)


def test_rejects_duplicate_question_id(hsg):
    hsg["questions"].append(copy.deepcopy(hsg["questions"][0]))
    assert "duplicate question id" in errors_for(hsg)


def test_rejects_page_that_asks_an_unknown_question(hsg):
    hsg["pages"][0]["asks"] = ["no-such-question"]
    assert "unknown question 'no-such-question'" in errors_for(hsg)


def test_rejects_branch_to_an_unknown_page(hsg):
    hsg["pages"][0]["next"] = [{"to": "no-such-page"}]
    assert "unknown page 'no-such-page'" in errors_for(hsg)


def test_rejects_known_question_without_attribute(hsg):
    known = next(q for q in hsg["questions"] if q["map"] == "known")
    known["attribute"] = None
    assert f"question '{known['id']}'" in errors_for(hsg)


def test_rejects_missing_gap_row(hsg):
    hsg["gaps"] = [g for g in hsg["gaps"] if g["id"] != 8]
    assert "gap 8" in errors_for(hsg)


def test_rejects_form_items_when_form_spec_is_declared_missing(hsg):
    hsg["form_items"] = [{"id": "1", "paper_asks": "Name", "category": "lookup"}]
    assert "form-spec" in errors_for(hsg)


def test_rejects_unknown_form_item_category(hsg):
    hsg["sources"]["form_spec"] = "form-spec.md"
    hsg["missing_parts"] = [m for m in hsg["missing_parts"] if m["part"] != "form-spec"]
    hsg["form_items"] = [{"id": "1", "paper_asks": "Name", "category": "maybe"}]
    assert "category" in errors_for(hsg)


def test_rejects_back_office_row_on_a_citizen_page(hsg):
    row = hsg["back_office"][0]["id"]
    hsg["pages"][0]["asks"] = [row]
    assert errors_for(hsg)


def test_rejects_back_office_id_that_is_also_a_question_id(hsg):
    hsg["back_office"][0]["id"] = hsg["questions"][0]["id"]
    assert f"'{hsg['questions'][0]['id']}' is both a question and a back-office row" in errors_for(hsg)


def test_rejects_journey_with_no_page_that_submits(hsg):
    for p in hsg["pages"]:
        p.pop("submits", None)
    assert "exactly one page must submit" in errors_for(hsg)


def test_rejects_journey_with_two_pages_that_submit(hsg):
    for p in hsg["pages"][:2]:
        p["submits"] = True
    assert "exactly one page must submit" in errors_for(hsg)


def test_rejects_page_that_cannot_be_reached(hsg):
    hsg["pages"].append({"id": "orphan", "title": "Orphan", "kind": "notice", "asks": [], "shows": [], "next": []})
    assert "page 'orphan' cannot be reached" in errors_for(hsg)


def test_unresolved_rows_must_point_at_something_real(hsg):
    hsg["unresolved"] = [{"ref": "questions/not-there", "reason": "x"}]
    assert "unresolved" in errors_for(hsg)


def test_cli_reports_valid_file(capsys):
    assert vh.main([PILOT]) == 0
    assert "valid" in capsys.readouterr().out


def test_cli_fails_on_invalid_file(tmp_path, hsg, capsys):
    import yaml

    hsg["level"] = "discovery"
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(hsg), encoding="utf-8")
    assert vh.main([str(bad)]) == 1
    assert "level" in capsys.readouterr().out


def test_required_from_is_readable_as_json():
    with open(os.path.join(BRIDGE, "references", "required-from.json"), encoding="utf-8") as f:
        json.load(f)


def test_hsg_pilot_pages_and_fields_exist_in_the_prototype(hsg):
    import re

    repo = os.path.dirname(BRIDGE)
    with open(os.path.join(repo, hsg["sources"]["prototype"]["page"]), encoding="utf-8") as f:
        html = f.read()
    sections = set(re.findall(r'<section id="page-([a-z0-9-]+)"', html))
    controls = set(re.findall(r'\b(?:name|id)="([A-Za-z0-9_-]+)"', html))
    missing_pages = [p["id"] for p in hsg["pages"] if p["id"] not in sections]
    missing_fields = [f for q in hsg["questions"] for f in q["fields"] if f not in controls]
    assert missing_pages == []
    assert missing_fields == []
