# Tree rendering and colour coding

`budgie.tree` turns a *flat* table of budget terms into a nested
[`BudgetNode`](../src/budgie/tree.py) tree and renders it three ways:

| Renderer            | Function                       | Colour coded? |
| ------------------- | ------------------------------ | ------------- |
| Plain text          | `render_ascii(node)`           | no            |
| LaTeX / TikZ tree   | `render_tikz(node)`            | **yes**       |
| Notebook display    | `display_tree(node)`           | **yes** (via `render_tikz` + `pdflatex`) |

Colour coding has two independent parts, and downstream consumers can take one
without the other:

1. **Per-`Type` fill** — every node is filled by its `Type`. Emitted by
   `_tikz_style_block`.
2. **Allocation cues** — per-leaf alerts and confirmations baked into the node
   *labels* by `render_tikz`'s label builders.

The exposure-time calculator in
[`schmidt_ESP_template`](https://github.com/douglase/schmidt_ESP_template) — which
pins `budgie` at `copilot/refine-forest-rendering` — uses **part 1 only**. See
[Downstream contract](#downstream-contract-schmidt_esp_template) before changing
anything in this file's scope.

If the code and this document ever disagree, the code is authoritative and this
file should be updated to match it.

## Quick start

```python
import pandas as pd
from budgie.tree import build_tree, render_ascii, render_tikz, display_tree

table = pd.DataFrame([
    {"Name": "coherent_1",   "Allocation": 4.0e-9, "CBE": 3.0e-9, "Type": "Static, Coherent"},
    {"Name": "incoherent_1", "Allocation": 0.5e-9, "CBE": 1.0e-9, "Type": "Static, Incoherent"},
    {"Name": "dynamic_1",    "Allocation": 2.0e-9, "CBE": 2.0e-9, "Type": "Dynamic"},
])
config = {
    "post_processing_chain": [
        {"op": "rss", "label": "Total raw value", "op_label": "RSS"},
    ],
}
node = build_tree(table, config=config)

print(render_ascii(node))                         # plain text, no colour
tex = render_tikz(node, show="both")              # standalone LaTeX document
display_tree(node, show="both", layout="forest")  # compiles + shows in a notebook
```

The three required columns are generic — **CBE**, **Allocation**, and **Type** —
and their actual column names can be remapped through `field_map` (see the
`build_tree` docstring).

## 1. Per-`Type` category fill

Every node — leaf term, category subtotal, and post-processing roll-up — is
filled according to its `Type`. `_tikz_style_block` walks the tree, collects the
distinct `Type` values via `_collect_types`, and assigns each the next colour
from this fixed palette:

| Order | Fill        |
| ----- | ----------- |
| 1     | `blue!15`   |
| 2     | `green!15`  |
| 3     | `orange!20` |
| 4     | `purple!15` |
| 5     | `teal!15`   |
| 6     | `gray!20`   |
| 7     | `cyan!15`   |

The `!NN` suffix is TikZ/`xcolor` percentage mixing (e.g. `blue!15` is 15% blue,
85% white), which is why the fills read as pale tints. One named TikZ style is
generated per `Type` (`type_<slug>/.style={fill=<colour>}`), so adding a new
`Type` to the input table automatically picks up a palette colour with no code
change.

### Assignment is positional — two consequences

`_collect_types` returns types in **pre-order tree-walk order** (root first, then
depth-first through children), and the palette is indexed by `position % 7`.
That means the colour of a `Type` is a property of *the tree being rendered*, not
of the `Type` itself:

- **Colours are not stable across separate renders.** Rendering a subtree, or a
  differently-shaped tree, restarts the palette at `blue!15`. In the ETC's
  paginated output, `Exoplanet Host Stars` is `orange!20` on the combined
  overview page but `blue!15` on its own per-section page. Do **not** rely on a
  colour as a persistent legend key across figures.
- **More than 7 types collide.** The 8th distinct type wraps back to `blue!15`,
  reusing the 1st type's colour. The ETC's overview tree has 8 types, so
  `type_rollup` and `type_reference_stars` are both `blue!15`.

Because the generated post-processing spine is walked first, `rollup` and
`scalar` normally consume palette slots 1 and 2, and the first real category
`Type` starts at `orange!20`.

## 2. Allocation cues (`render_tikz` labels only)

These are produced by `render_tikz`'s label builders
(`_format_leaf_value_text`, `_styled_node_name`) and the `overallocated` style.
A consumer that builds its own node labels — as the ETC does — will **not** get
any of them.

### Over-allocated leaves

When a **leaf** term's CBE **exceeds** its Allocation (`CBE > Allocation`) and
`alert_on_exceedances=True` (the default), three negative cues are added on top
of the `Type` fill:

- **Red bold border** — the node gets the `overallocated` style
  (`draw=red, very thick, font=\bfseries`).
- **Warning prefix** — a `$\triangle!$` warning triangle is prepended to the
  node name.
- **Yellow value highlight** — the CBE value is wrapped in
  `\colorbox{yellow!50}{…}`.

These cues apply to **leaf** nodes only; category subtotals and post-processing
roll-ups are never flagged, even if their aggregated value exceeds their
allocation.

### Within-allocation leaves

When a **leaf** term's CBE is **within** its Allocation (`CBE <= Allocation`),
its CBE value is `\underline{…}` underlined. This positive cue is **not**
affected by `alert_on_exceedances`.

### Turning alerts off

`render_tikz(node, alert_on_exceedances=False)` (and the same keyword on
`display_tree` and `_tikz_style_block`) suppresses **only** the negative cues —
no red border, no warning triangle, no yellow highlight, and the `overallocated`
style is not even defined. The per-`Type` fills and the within-allocation
underline are unaffected.

### Summary table

| Condition                  | Applies to | Cue                                        | Emitted by         | Suppressed by `alert_on_exceedances=False`? |
| -------------------------- | ---------- | ------------------------------------------ | ------------------ | ------------------------------------------- |
| Node `Type`                | all nodes  | pale fill from the 7-colour palette        | `_tikz_style_block` | no                                          |
| `CBE > Allocation`         | leaves     | red bold border + `△!` prefix + yellow CBE | `render_tikz` labels + `overallocated` style | yes                        |
| `CBE <= Allocation`        | leaves     | underlined CBE value                       | `render_tikz` labels | no                                        |

## Downstream contract (`schmidt_ESP_template`)

The exposure-time calculator's
`budgets/exposure_time/render_tree.py` does **not** call `render_tikz` for its
TikZ output. It reimplements the outline layout with absolute coordinates (to
control sibling spacing and pagination) and imports these budgie names directly:

```python
from budgie.tree import (
    BudgetNode, _style_name, _tikz_style_block, build_tree, render_ascii,
)
```

Two of those — **`_style_name` and `_tikz_style_block`** — are underscore-private
but are a *de facto public API* for that consumer. Renaming them, changing
`_style_name`'s slug format, or changing `_tikz_style_block`'s signature or its
`\tikzset{…}` output shape will break the ETC build. Change them only
deliberately, and update the pinned branch together with the template.

Consequences for what the ETC figures actually show:

- It calls `_tikz_style_block(node, alert_on_exceedances=False)`, so the
  `overallocated` style is never defined.
- It builds its own node labels (`\textbf` values, `\textcolor{gray}` filter
  tags, `\textcolor{black!50}` notes), so **none** of the section-2 cues appear —
  no `\colorbox`, no `△!`, and **no `\underline`** either.
- Its figures are therefore coloured by **`Type` fill alone**, and are subject to
  both positional caveats above.

`render_ascii` is used for the plain-text sidecar output and, as always, carries
no colour.

## Layouts

`render_tikz` accepts `layout="forest"` (default) or `layout="outline"`. Both
emit the **same** `\tikzset` colour block and the same alert cues; they differ
only in geometry:

- **`forest`** — boxed nodes in a top-down tree (uses the `forest` package).
- **`outline`** — a directory-style indented outline (uses a plain
  `tikzpicture`); combine-operation edge labels are drawn in gray.

## Which fields are shown

`show` selects the numeric fields printed inside each node:

- `"both"` (default) — CBE and Allocation.
- `"cbe"` — CBE only.
- `"allocation"` — Allocation only.

The cues in section 2 are driven by the CBE-vs-Allocation comparison regardless
of `show`, but the yellow highlight and underline decorate the **CBE** text, so
they are visible only when CBE is shown (`"both"` or `"cbe"`).

## Required LaTeX packages

Standalone output from `render_tikz(..., standalone=True)` pulls in `forest` and
`xcolor`. When embedding a fragment (`standalone=False`) into a larger document —
as `schmidt_ESP_template` does — that host document must load `forest` and
`xcolor` itself. The palette and highlights rely only on base `xcolor` percentage
mixing (`blue!15`, `yellow!50`, …), so no `xcolor` package options are required.

## Plain-text renderer

`render_ascii` deliberately carries **no** colour or alert styling — it is a
simple `├──`/`└──` hierarchy meant for quick terminal inspection and diff-able
snapshots. Use `render_tikz` / `display_tree` whenever the colour coding matters.
