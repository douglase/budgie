"""Report any YAML budget through ``budgie.tree``: ``python docs/examples/report.py BUDGET.yaml [OUT_DIR]``.

The YAML holds ``terms`` (rows with Name, Type, Allocation, CBE), ``config``
(``category_combine_ops``, ``post_processing_chain``, optional ``field_map``) and
an optional ``budget`` block with ``name``, ``units`` and ``available``, the
total the allocations draw from. No budget class is needed.
"""

import sys
from pathlib import Path

import yaml

from budgie.tree import build_tree, render_ascii, render_tikz


def report(budget_yaml, out_dir=None):
    """Write ``<stem>_report.md``, ``<stem>_tree.txt`` and ``<stem>_tree.tex``; return the report path."""
    path = Path(budget_yaml)
    out = Path(out_dir or path.parent)
    out.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    meta = data.get("budget", {})
    units = meta.get("units", "")
    root = build_tree(data["terms"], config=data["config"])
    tree = render_ascii(root)
    (out / f"{path.stem}_tree.txt").write_text(tree + "\n", encoding="utf-8")
    (out / f"{path.stem}_tree.tex").write_text(render_tikz(root), encoding="utf-8")
    lines = [
        f"# {meta.get('name', path.stem)}",
        "",
        f"- Allocated: {root.allocation:.1f} {units}",
        f"- CBE: {root.value:.1f} {units}",
        f"- Margin: {root.allocation - root.value:.1f} {units}",
    ]
    if "available" in meta:
        reserve = meta["available"] - root.allocation
        lines += [f"- Available: {meta['available']:.1f} {units}", f"- Unallocated reserve: {reserve:.1f} {units}"]
        if reserve < 0:
            lines.append(f"- **WARNING:** allocations exceed the available {meta['available']:.1f} {units}.")
    lines += ["", "```", tree, "```", ""]
    (out / f"{path.stem}_report.md").write_text("\n".join(lines), encoding="utf-8")
    return out / f"{path.stem}_report.md"


if __name__ == "__main__":
    print(report(*sys.argv[1:]).read_text(encoding="utf-8"))
