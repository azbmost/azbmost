import unittest

from azbmost import extract_other_tools


def tool_section(body: str) -> str:
    return f'''\
def build_gui():
    # --- Other tools frame ---
{body}
    # --- Run log frame ---
'''


class ExtractOtherToolsTests(unittest.TestCase):
    def test_extracts_old_add_tool_button_signature(self) -> None:
        source = tool_section(
            '''\
    add_tool_button(0, "Convert XYZ...", convert_xyz, "xyz_convert")
    add_tool_button(1, "Plane It...", launch_plane_it, "plane_it")'''
        )

        self.assertEqual(extract_other_tools(source), ("Convert XYZ...", "Plane It..."))

    def test_extracts_current_curve_it_signature(self) -> None:
        source = tool_section(
            '''\
    add_tool_button(0, 0, "Convert XYZ...", convert_xyz, "xyz_convert")
    add_tool_button(0, 1, "Generate SC...", launch_generate_sc, "generate_sc")
    add_tool_button(1, 0, "Plane It...", launch_plane_it, "plane_it")'''
        )

        self.assertEqual(
            extract_other_tools(source),
            ("Convert XYZ...", "Generate SC...", "Plane It..."),
        )

    def test_extracts_literal_button_labels(self) -> None:
        source = tool_section(
            '''\
    tk.Button(tools, text="Measure", command=measure)
    ttk.Button(tools, command=align, text='Align')'''
        )

        self.assertEqual(extract_other_tools(source), ("Measure", "Align"))


if __name__ == "__main__":
    unittest.main()
