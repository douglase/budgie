"""docs/examples/report.py builds and reports a YAML budget on budgie.tree without a budget class."""

import importlib.util
from pathlib import Path

import pytest
import yaml

from budgie.tree import BudgetTreeError, build_tree

EXAMPLES = Path(__file__).parents[1] / "docs" / "examples"
DM_STROKE = EXAMPLES / "dm_stroke" / "dm_stroke.yaml"


@pytest.fixture(scope="module")
def report():
    spec = importlib.util.spec_from_file_location("report", EXAMPLES / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.report


def _budget(tmp_path, groups, available=1000):
    """Two terms (30 and 40) per group; ``groups`` maps Type -> combine rule."""
    terms = [{"Name": f"{g}_{v}", "Type": g, "Allocation": v, "CBE": v} for g in groups for v in (30, 40)]
    data = {
        "budget": {"available": available, "units": "nm"},
        "config": {"category_combine_ops": groups, "post_processing_chain": [{"op": "sum"}]},
        "terms": terms,
    }
    path = tmp_path / "budget.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_dm_stroke_groups_sum_their_terms():
    data = yaml.safe_load(DM_STROKE.read_text())
    root = build_tree(data["terms"], config=data["config"])
    static = next(node for node in root.children if node.metadata["Type"] == "static")
    assert (static.allocation, static.value) == (pytest.approx(400), pytest.approx(372))
    assert (root.allocation, root.value) == (pytest.approx(500), pytest.approx(457))


def test_dm_stroke_report(report, tmp_path):
    text = report(DM_STROKE, tmp_path).read_text()
    expected = ("Allocated: 500.0 nm", "CBE: 457.0 nm", "Margin: 43.0 nm", "Available: 1400.0 nm", "reserve: 900.0 nm")
    assert all(line in text for line in expected)
    assert "WARNING" not in text
    assert (tmp_path / "dm_stroke_tree.txt").exists() and (tmp_path / "dm_stroke_tree.tex").exists()


def test_groups_can_mix_rss_and_sum(report, tmp_path):
    text = report(_budget(tmp_path, {"random": "rss", "systematic": "sum"})).read_text()
    assert "Allocated: 120.0 nm" in text          # rss(30, 40) = 50, sum(30, 40) = 70


def test_over_allocation_warns(report, tmp_path):
    assert "WARNING" in report(_budget(tmp_path, {"systematic": "sum"}, available=50)).read_text()


def test_unknown_combine_rule_raises(report, tmp_path):
    with pytest.raises(BudgetTreeError):
        report(_budget(tmp_path, {"systematic": "average"}))


def test_report_without_available(report, tmp_path):
    path = _budget(tmp_path, {"systematic": "sum"})
    data = yaml.safe_load(path.read_text())
    del data["budget"]["available"]
    path.write_text(yaml.safe_dump(data))
    assert "reserve" not in report(path).read_text()
