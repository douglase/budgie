# Budgie
_Budgie the budget tool_

**NOTE:** In order for this to work, data yaml files must be added to the data directory (currently) but will be able to specify in the future via command line. Name of package is budgets currently but will be changed over to budgie per opened issues.

Use the `test.sh` and edit the data file names with the names of the actual ones added to the data directory to run a report test for the budgets added. This will install the budgie package as well in the process.

## Plantuml Diagrams
A 'demo' for visualizing the initial budget yaml files is added to this tool and requires [`plantuml`](https://plantuml.com) (plantuml.jar is provided).

**Future Implementation:** Using just graphviz or something similar will require some modifications on the `budgets.py` to prevent repeating of some code aspects and improve reporting mechanics. Plantuml will no longer be needed for the diagram portion in that implementation. In order to use `budgie`, you do **not** need to have plantuml for the other functions.

## Tree Rendering
`budgie.tree` builds a hierarchical budget tree from a flat table of terms and
renders it as plain-text ASCII, as a colour-coded LaTeX/TikZ figure, or inline in
a notebook via `display_tree`. The TikZ renderers colour each node by its `Type`
from a 7-colour palette, and flag over-allocated leaves (`CBE > Allocation`) with
a red border, a `△!` prefix, and a yellow highlight, while underlining leaves that
stay within allocation.

Downstream renderers that lay out their own TikZ trees consume the per-`Type`
fill via `_tikz_style_block`/`_style_name`. Those two underscore-private helpers
are a de facto public API for such consumers — see the Downstream contract
section of the reference before changing them.

See [Tree rendering and colour coding](docs/tree_rendering.md) for the full
reference and [`docs/tree_rendering.ipynb`](docs/tree_rendering.ipynb) for a
runnable example. [`docs/examples/report.py`](docs/examples/report.py) reports any budget
defined only in YAML (terms, per-group `sum`/`rss` rules, post-processing chain,
optional `available` total) through `budgie.tree` with no budget class;
[`docs/examples/dm_stroke`](docs/examples/dm_stroke) is a worked
deformable-mirror stroke budget, with a standalone notebook
([`dm_stroke.ipynb`](docs/examples/dm_stroke/dm_stroke.ipynb)) that walks through it.

## Related Documents
- [STP Budget Package Description](docs/design_description.md)
- [Tree rendering and colour coding](docs/tree_rendering.md)

