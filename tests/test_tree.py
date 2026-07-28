from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from budgie.tree import (
    BudgetTreeError,
    _style_name,
    _tikz_style_block,
    build_tree,
    display_tree,
    register_combine_op,
    render_ascii,
    render_tikz,
)


FIXTURES_DIR = Path(__file__).parent.joinpath("fixtures")


def _sample_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Name": "coherent_1",
                "Allocation": 4.0e-9,
                "CBE": 3.0e-9,
                "Type": "Static, Coherent",
                "Description": "first coherent term",
                "CBE Trace": "trace-a",
            },
            {
                "Name": "coherent_2",
                "Allocation": 4.0e-9,
                "CBE": 4.0e-9,
                "Type": "Static, Coherent",
                "Description": "second coherent term",
                "CBE Trace": "trace-b",
            },
            {
                "Name": "incoherent_1",
                "Allocation": 0.5e-9,
                "CBE": 1.0e-9,
                "Type": "Static, Incoherent",
                "Description": "incoherent term",
                "CBE Trace": "trace-c",
            },
            {
                "Name": "dynamic_1",
                "Allocation": 2.0e-9,
                "CBE": 2.0e-9,
                "Type": "Dynamic",
                "Description": "dynamic term",
                "CBE Trace": "trace-d",
            },
        ]
    )


def _sample_config() -> dict:
    return {
        "pp_gain": 0.1,
        "post_processing_chain": [
            {"op": "rss", "label": "Total raw value", "op_label": "RSS"},
            {
                "op": "scalar_multiply",
                "factor_key": "pp_gain",
                "label": "Post-processed value",
                "op_label": r"$\times g_{pp}$",
            },
            {"op": "scalar_multiply", "factor": 5, "label": "5σ Post-processed value", "op_label": "5×"},
        ],
    }


def _count_edge_labels(node) -> int:
    parent_edge_count = len(node.children) if node.op_label else 0
    child_edge_count = sum(_count_edge_labels(child) for child in node.children)
    return parent_edge_count + child_edge_count


class TestTreeRendering(TestCase):
    def test_ascii_snapshot(self):
        node = build_tree(_sample_table(), config=_sample_config())
        actual = render_ascii(node, show="both")
        expected = FIXTURES_DIR.joinpath("tree_ascii_snapshot.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(actual.strip(), expected)

    def test_tikz_structure_edge_labels_and_overallocation(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, show="both", standalone=False)

        self.assertIn("\\begin{forest}", tikz)
        self.assertIn("\\end{forest}", tikz)
        self.assertIn("align=center", tikz)
        self.assertIn("overallocated", tikz)
        self.assertIn("\\underline{", tikz)
        self.assertIn("\\colorbox{yellow!50}{", tikz)
        self.assertIn("coherent\\_1", tikz)
        self.assertNotIn("coherent\\\\_1", tikz)
        self.assertEqual(tikz.count("edge label={"), _count_edge_labels(node))

    def test_render_tikz_outline_layout(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, show="both", standalone=False, layout="outline")

        self.assertIn("\\begin{tikzpicture}", tikz)
        self.assertIn("grow via three points", tikz)
        self.assertIn("edge from parent path", tikz)
        self.assertIn("type_static_coherent/.style", tikz)
        self.assertIn("type_static_incoherent/.style", tikz)
        self.assertIn("type_dynamic/.style", tikz)
        self.assertIn("RSS", tikz)
        self.assertIn(r"$\times g_{pp}$", tikz)
        self.assertIn("5×", tikz)
        self.assertIn("text=gray", tikz)
        self.assertIn("\\underline{", tikz)
        self.assertIn("\\colorbox{yellow!50}{", tikz)

    def test_render_tikz_invalid_layout_raises(self):
        node = build_tree(_sample_table(), config=_sample_config())
        with self.assertRaises(BudgetTreeError):
            render_tikz(node, layout="unknown-layout")

    def test_alert_on_exceedances_disabled_forest(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, layout="forest", standalone=False, alert_on_exceedances=False)

        self.assertNotIn("\\colorbox{yellow", tikz)
        self.assertNotIn("overallocated", tikz)
        self.assertNotIn("$\\triangle", tikz)
        self.assertNotIn("\\triangle!", tikz)
        self.assertIn("\\underline{", tikz)

    def test_alert_on_exceedances_disabled_outline(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, layout="outline", standalone=False, alert_on_exceedances=False)

        self.assertNotIn("\\colorbox{yellow", tikz)
        self.assertNotIn("overallocated", tikz)
        self.assertNotIn("$\\triangle", tikz)
        self.assertNotIn("\\triangle!", tikz)
        self.assertIn("\\underline{", tikz)

    def test_alert_on_exceedances_default_enabled(self):
        node = build_tree(_sample_table(), config=_sample_config())
        tikz = render_tikz(node, layout="forest", standalone=False)

        self.assertIn("\\colorbox{yellow", tikz)
        self.assertIn("overallocated", tikz)
        self.assertIn("$\\triangle!$", tikz)

    def test_display_tree_passes_alert_flag_through(self):
        node = build_tree(_sample_table(), config=_sample_config())

        with patch("budgie.tree.render_tikz", return_value="tex") as mock_render_tikz:
            display_tree(node, alert_on_exceedances=False)

        self.assertFalse(mock_render_tikz.call_args.kwargs["alert_on_exceedances"])

    def test_display_tree_passes_layout_through(self):
        node = build_tree(_sample_table(), config=_sample_config())
        with patch("budgie.tree.render_tikz", return_value="ok") as mock_render:
            display_tree(node, layout="outline")
        mock_render.assert_called_once()
        self.assertEqual(mock_render.call_args.kwargs["layout"], "outline")

    def test_requires_post_processing_chain(self):
        with self.assertRaises(BudgetTreeError) as ctx:
            build_tree(_sample_table(), config={})
        self.assertIsInstance(ctx.exception, BudgetTreeError)
        message = str(ctx.exception)
        self.assertIn("post_processing_chain", message)
        self.assertIn("<combine_op>", message)
        self.assertNotIn("Total raw value", message)

    def test_new_type_auto_generates_style(self):
        table = _sample_table()
        table = pd.concat(
            [
                table,
                pd.DataFrame(
                    [
                        {
                            "Name": "new_type_leaf",
                            "Allocation": 1.0e-9,
                            "CBE": 0.8e-9,
                            "Type": "New Type",
                            "Description": "new type term",
                            "CBE Trace": "trace-z",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        node = build_tree(table, config=_sample_config())
        tikz = render_tikz(node, standalone=False)
        self.assertIn("type_new_type/.style", tikz)

    def test_field_map_supports_legacy_column_names(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )
        mapped_node = build_tree(
            legacy_table,
            config=_sample_config(),
            field_map={"cbe": "Contrast CBE", "allocation": "Contrast Allocation", "type": "Type"},
        )
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_adapter_auto_maps_suffix_cbe_allocation_columns(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )

        class _LegacyBudgetLike:
            def __init__(self, table, config):
                self._table = table
                self.budget = config

            def get_pandas_table(self):
                return self._table

        mapped_node = build_tree(_LegacyBudgetLike(legacy_table, _sample_config()))
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_field_map_from_config(self):
        generic_node = build_tree(_sample_table(), config=_sample_config())
        legacy_table = _sample_table().rename(
            columns={"CBE": "Contrast CBE", "Allocation": "Contrast Allocation"}
        )
        config = dict(_sample_config())
        config["field_map"] = {"cbe": "Contrast CBE", "allocation": "Contrast Allocation", "type": "Type"}
        mapped_node = build_tree(legacy_table, config=config)
        self.assertEqual(render_ascii(mapped_node, show="both"), render_ascii(generic_node, show="both"))

    def test_only_generic_required_columns(self):
        minimal_table = _sample_table()[["Name", "Allocation", "CBE", "Type"]]
        node = build_tree(minimal_table, config=_sample_config())
        self.assertIsNotNone(node.value)
        self.assertIsNotNone(node.allocation)

        def _find_first_leaf(current):
            if current.kind == "leaf":
                return current
            for child in current.children:
                leaf = _find_first_leaf(child)
                if leaf is not None:
                    return leaf
            return None

        leaf = _find_first_leaf(node)
        self.assertIsNotNone(leaf)
        self.assertNotIn("Description", leaf.metadata)
        self.assertNotIn("CBE Trace", leaf.metadata)

    def test_missing_required_column_in_later_row_raises_clear_error(self):
        records = _sample_table().to_dict("records")
        records[1].pop("CBE")
        with self.assertRaises(BudgetTreeError) as ctx:
            build_tree(records, config=_sample_config())
        message = str(ctx.exception)
        self.assertIn("Missing required table column 'CBE' mapped from 'cbe'", message)
        self.assertIn("row index 1", message)

    def test_custom_combine_op_registration(self):
        def _range(values, **_):
            return max(values) - min(values)

        register_combine_op("range", _range, r"$\max-\min$")
        config = {
            "post_processing_chain": [
                {"op": "range", "label": "Range total"},
            ]
        }
        node = build_tree(_sample_table(), config=config, default_category_combine_op="sum")
        self.assertEqual(node.combine_op, "range")
        self.assertGreater(node.value, 0)


class TestDownstreamStyleContract(TestCase):
    """Lock the colour-styling API that ``schmidt_ESP_template`` depends on.

    Its ``budgets/exposure_time/render_tree.py`` lays the tree out itself but
    imports ``_style_name`` and ``_tikz_style_block`` from budgie to colour it.
    Those names are underscore-private yet are a de facto public API for that
    consumer, so changes here must be deliberate. See ``docs/tree_rendering.md``.
    """

    def test_exposure_time_calculator_import_surface_exists(self):
        import budgie.tree as tree_module

        for name in ("BudgetNode", "_style_name", "_tikz_style_block", "build_tree", "render_ascii"):
            self.assertTrue(hasattr(tree_module, name), f"schmidt_ESP_template imports {name}")

    def test_style_name_slug_format(self):
        self.assertEqual(_style_name("Exoplanet Host Stars"), "type_exoplanet_host_stars")
        self.assertEqual(_style_name("Static, Coherent"), "type_static_coherent")

    def test_style_block_matches_exposure_time_calculator_output(self):
        """Reproduces the committed ``exposure_time_tree.tex`` style block exactly."""
        types = [
            "Exoplanet Host Stars",
            "Benchmark",
            "Extreme Debris Systems",
            "Habitable Zone Disks",
            "Warm Debris Disks",
            "Reference Stars",
        ]
        records = [
            {"Name": f"tgt_{index}", "Allocation": 10.0, "CBE": 5.0, "Type": type_name}
            for index, type_name in enumerate(types)
        ]
        config = {
            "field_map": {"cbe": "CBE", "allocation": "Allocation", "type": "Type"},
            "category_combine_ops": {type_name: "sum" for type_name in sorted(types)},
            "post_processing_chain": [
                {"op": "sum", "label": "Sum of target integration times"},
                {"op": "scalar_multiply", "factor": 1.0 / 0.9, "label": "Wall-clock budget"},
            ],
        }
        node = build_tree(records, config=config)

        expected = (
            "\\tikzset{\n"
            "type_rollup/.style={fill=blue!15},\n"
            "type_scalar/.style={fill=green!15},\n"
            "type_exoplanet_host_stars/.style={fill=orange!20},\n"
            "type_benchmark/.style={fill=purple!15},\n"
            "type_extreme_debris_systems/.style={fill=teal!15},\n"
            "type_habitable_zone_disks/.style={fill=gray!20},\n"
            "type_warm_debris_disks/.style={fill=cyan!15},\n"
            # An 8th type wraps the 7-colour palette back to the 1st colour.
            "type_reference_stars/.style={fill=blue!15},\n"
            "}\n"
        )
        self.assertEqual(_tikz_style_block(node, False), expected)

    def test_style_block_without_alerts_omits_overallocated_style(self):
        node = build_tree(_sample_table(), config=_sample_config())
        self.assertNotIn("overallocated", _tikz_style_block(node, False))
        self.assertIn("overallocated", _tikz_style_block(node, True))

    def test_palette_assignment_is_per_render_not_global(self):
        """A subtree restarts the palette, so colours are not stable across figures."""
        node = build_tree(_sample_table(), config=_sample_config())
        subtree = node.children[0]

        self.assertNotEqual(_tikz_style_block(node, False), _tikz_style_block(subtree, False))
        self.assertIn("fill=blue!15", _tikz_style_block(subtree, False))
