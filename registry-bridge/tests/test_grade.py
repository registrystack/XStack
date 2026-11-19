"""Tests for the design-to-handoff grader.

Run from the repository root:
  uv run --with pytest --with jsonschema --with pyyaml pytest registry-bridge/tests
"""

import copy
import importlib.util
import os

import pytest

BRIDGE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRADE = os.path.join(BRIDGE, "skills", "design-to-handoff", "evals", "grade.py")
TRUTH = os.path.join(BRIDGE, "pilots", "household-support-grant", "service-handoff.yaml")

spec = importlib.util.spec_from_file_location("grade", GRADE)
grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade)


@pytest.fixture()
def truth():
    return grade.load(TRUTH)


def failed(result):
    return [e["text"] for e in result["expectations"] if not e["passed"]]


def failed_about(result, word):
    return [t for t in failed(result) if word in t.lower()]


def test_ground_truth_against_itself_passes_everything(truth):
    result = grade.grade(copy.deepcopy(truth), truth)
    assert failed(result) == []
    assert result["summary"]["pass_rate"] == 1.0
    assert result["summary"]["total"] == len(grade.CHECKS) == 18


def test_invalid_file_fails_the_schema_check(truth):
    gen = copy.deepcopy(truth)
    gen["level"] = "discovery"
    assert failed_about(grade.grade(gen, truth), "valid")


def test_schema_invalid_file_scores_0_of_18(truth):
    gen = copy.deepcopy(truth)
    gen["level"] = "discovery"
    summary = grade.grade(gen, truth)["summary"]
    assert (summary["passed"], summary["total"]) == (0, 18)


def test_wrong_iteration_fails_the_source_check(truth):
    gen = copy.deepcopy(truth)
    gen["sources"]["prototype"]["iteration"] = 3
    assert failed_about(grade.grade(gen, truth), "prototype")


def test_dropped_question_fails_coverage(truth):
    gen = copy.deepcopy(truth)
    gen["questions"] = [q for q in gen["questions"] if q["id"] != "programmes"]
    gen["pages"] = [dict(p, shows=[s for s in p["shows"] if s != "programmes"]) for p in gen["pages"]]
    assert failed_about(grade.grade(gen, truth), "coverage")


def test_question_matched_by_attribute_even_with_another_id(truth):
    gen = copy.deepcopy(truth)
    for q in gen["questions"]:
        if q["id"] == "payout-account":
            q["id"] = "where-we-pay"
    for p in gen["pages"]:
        p["asks"] = ["where-we-pay" if a == "payout-account" else a for a in p["asks"]]
        p["shows"] = ["where-we-pay" if a == "payout-account" else a for a in p["shows"]]
    result = grade.grade(gen, truth)
    assert not failed_about(result, "coverage")


def test_wrong_map_fails_map_agreement(truth):
    gen = copy.deepcopy(truth)
    next(q for q in gen["questions"] if q["id"] == "hsg-assessment")["map"] = "known"
    assert failed_about(grade.grade(gen, truth), "known, derived or ask")


def test_lost_tag_fails_tag_check(truth):
    gen = copy.deepcopy(truth)
    next(q for q in gen["questions"] if q["id"] == "household")["tags"] = []
    assert failed_about(grade.grade(gen, truth), "tag")


def test_swapped_pages_fail_page_order(truth):
    gen = copy.deepcopy(truth)
    gen["pages"][1], gen["pages"][2] = gen["pages"][2], gen["pages"][1]
    assert failed_about(grade.grade(gen, truth), "order")


def test_lost_branch_fails_branching(truth):
    gen = copy.deepcopy(truth)
    start = next(p for p in gen["pages"] if p["id"] == "start")
    start["next"] = [n for n in start["next"] if n["to"] != "no-kuin"]
    assert failed_about(grade.grade(gen, truth), "branch")


def test_invented_attribute_fails(truth):
    gen = copy.deepcopy(truth)
    next(q for q in gen["questions"] if q["id"] == "household")["attribute"] = "welfareBand"
    assert failed_about(grade.grade(gen, truth), "catalogue")


def test_missing_open_items_fail(truth):
    gen = copy.deepcopy(truth)
    gen["open_items"] = gen["open_items"][:30]
    assert failed_about(grade.grade(gen, truth), "open item")


def test_hidden_unresolved_row_fails(truth):
    gen = copy.deepcopy(truth)
    gen["unresolved"] = []
    assert failed_about(grade.grade(gen, truth), "unresolved")


def test_back_office_row_lost_is_reported(truth):
    gen = copy.deepcopy(truth)
    gen["back_office"] = gen["back_office"][:5]
    assert failed_about(grade.grade(gen, truth), "back-office")
