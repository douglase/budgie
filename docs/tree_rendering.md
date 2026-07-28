# Tree rendering and colour coding

`budgie.tree` turns a *flat* table of budget terms into a nested
[`BudgetNode`](../src/budgie/tree.py) tree and renders it three ways:

| Renderer            | Function                       | Colour coded? |
| ------------------- | ------------------------------ | ------------- |
| Plain text          | `render_ascii(node)`           | no            |
| LaTeX / TikZ tree   | `render_tikz(node)`            | **yes**       |
| Notebook display    | `display_tree(node)`           | **yes** (via `render_tikz` + `pdflatex`) |

The colour coding described below is emitted by `render_tikz` (and therefore by
`display_tree`, which compiles its output). It is the exact scheme consumed by
the exposure-time-calculator budget figures in
[`schmidt_ESP_template`](https://github.com/douglase/schmidt_ESP_template),
which pins `budgie` at the `copilot/refine-forest-rendering` branch. This
document is the reference for that scheme; if the code and this document ever
disagree, the code in `render_tikz` is authoritative and this file should be
updated to match it.

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

print(render_ascii(node))                       # plain text, no colour
tex = render_tikz(node, show="both")            # standalone LaTeX document
display_tree(node, show="both", layout="forest")  # compiles + shows in a notebook
```

The three required columns are generic — **CBE**, **Allocation**, and **Type** —
and their actual column names can be remapped through `field_map` (see the
`build_tree` docstring). The colour coding keys off two things only: a node's
**Type** (which drives its fill colour) and, for leaves, whether **CBE** exceeds
**Allocation** (which drives the alert cues).

## Colour coding reference

### 1. Per-`Type` category fill

Every node — leaf term, category subtotal, and post-processing roll-up — is
filled according to its `Type`. `render_tikz` walks the tree, collects the
distinct `Type` values in first-seen order, and assigns each one the next colour
from this fixed palette, cycling if there are more than seven types:

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
`Type` to the input table automatically picks up the next palette colour with no
code change. Colours are assigned by tree-walk order, not by input-row order, so
the generated post-processing spine (roll-up / scalar nodes) is coloured first.

### 2. Over-allocation alerts (leaves only)

When a **leaf** term's CBE **exceeds** its Allocation (`CBE > Allocation`) and
`alert_on_exceedances=True` (the default), three negative cues are added on top
of the Type fill:

- **Red bold border** — the node gets the `overallocated` style
  (`draw=red, very thick, font=\bfseries`).
- **Warning prefix** — a `$\triangle!$` warning triangle is prepended to the
  node name.
- **Yellow value highlight** — the CBE value is wrapped in
  `\colorbox{yellow!50}{…}`.

These cues apply to **leaf** nodes only; category subtotals and post-processing
roll-ups are never flagged, even if their aggregated value exceeds their
allocation.

### 3. Meets-allocation confirmation (leaves only)

When a **leaf** term's CBE is **within** its Allocation (`CBE <= Allocation`),
its CBE value is `\underline{…}` underlined. This positive cue is **always**
rendered and is **not** affected by `alert_on_exceedances`.

### 4. Turning alerts off

`render_tikz(node, alert_on_exceedances=False)` (and the same keyword on
`display_tree`) suppresses **only** the negative cues from section 2 — no red
border, no warning triangle, no yellow highlight, and the `overallocated` style
is not even defined. The per-`Type` fills (section 1) and the meets-allocation
underline (section 3) are unaffected. Use this for a clean, purely categorical
view.

### Summary table

| Condition                                   | Applies to | Cue                                         | Suppressed by `alert_on_exceedances=False`? |
| ------------------------------------------- | ---------- | ------------------------------------------- | ------------------------------------------- |
| Node `Type`                                 | all nodes  | pale fill from the 7-colour palette         | no                                          |
| `CBE > Allocation`                          | leaves     | red bold border + `△!` prefix + yellow CBE  | yes                                         |
| `CBE <= Allocation`                         | leaves     | underlined CBE value                        | no                                          |

## Layouts

`render_tikz` accepts `layout="forest"` (default) or `layout="outline"`. Both
layouts emit the **same** `\tikzset` colour block and the same alert cues; they
differ only in geometry:

- **`forest`** — boxed nodes in a top-down tree (uses the `forest` package).
- **`outline`** — a directory-style indented outline (uses a plain
  `tikzpicture`); combine-operation edge labels are drawn in gray.

## Which fields are shown

`show` selects the numeric fields printed inside each node:

- `"both"` (default) — CBE and Allocation.
- `"cbe"` — CBE only.
- `"allocation"` — Allocation only.

The alert and confirmation cues in sections 2–3 are driven by the CBE-vs-
Allocation comparison regardless of `show`, but the yellow highlight and
underline decorate the **CBE** text, so they are visible only when CBE is shown
(`"both"` or `"cbe"`).

## Required LaTeX packages

Standalone output from `render_tikz(..., standalone=True)` pulls in `forest` and
`xcolor`. When embedding a fragment (`standalone=False`) into a larger document —
as `schmidt_ESP_template` does — that host document must load `forest` and
`xcolor` itself. The palette and highlights rely only on base `xcolor`
percentage mixing (`blue!15`, `yellow!50`, …), so no `xcolor` package options
are required.

## Plain-text renderer

`render_ascii` deliberately carries **no** colour or alert styling — it is a
simple `├──`/`└──` hierarchy meant for quick terminal inspection and diff-able
snapshots. Use `render_tikz` / `display_tree` whenever the colour coding matters.
