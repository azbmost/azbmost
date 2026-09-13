import unittest

import pathlib
import pytest
import azbmost as azbmost_module
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


# --------------------------------------------------------------- shared path
def test_pth_roundtrip_is_clean(tmp_path, monkeypatch):
    """Enable writes one file; disable leaves nothing behind."""
    monkeypatch.setattr(azbmost_module, "user_site_dir", lambda: tmp_path)
    roots = {"curve_it": tmp_path / "curve_it", "re_helix": tmp_path / "re_helix"}
    written = azbmost_module.write_pth(roots)
    assert written.exists()
    assert azbmost_module.read_pth_roots() == sorted(roots.values())
    assert azbmost_module.remove_pth() == written
    assert not written.exists()
    assert azbmost_module.read_pth_roots() == []


def test_pth_holds_repo_roots_not_lib_dirs(tmp_path, monkeypatch):
    """Lib dirs on the path would expose modules under bare names too, making one
    file two module objects with two sets of classes."""
    monkeypatch.setattr(azbmost_module, "user_site_dir", lambda: tmp_path)
    roots = {"bnp_na": tmp_path / "bnp_na"}
    azbmost_module.write_pth(roots)
    for line in azbmost_module.read_pth_roots():
        assert not str(line).endswith("_lib"), line


def test_pth_survives_spaces_in_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(azbmost_module, "user_site_dir", lambda: tmp_path)
    spaced = tmp_path / "ASU Dropbox" / "Di Liu" / "curve_it"
    azbmost_module.write_pth({"curve_it": spaced})
    assert azbmost_module.read_pth_roots() == [spaced]


def test_write_pth_refuses_when_user_site_disabled(monkeypatch):
    """A venv reports the BASE user site, so writing there would switch sharing on
    for an interpreter the launcher is not using."""
    monkeypatch.setattr(azbmost_module, "user_site_dir", lambda: None)
    assert azbmost_module.pth_file_path() is None
    with pytest.raises(RuntimeError):
        azbmost_module.write_pth({"curve_it": pathlib.Path("/tmp/curve_it")})


def test_probe_reports_each_module_separately():
    result = azbmost_module.probe_shared_imports()
    assert result["ok"] is True
    assert set(result["modules"]) == {"bnp_na", "curve_it", "re_helix"}
    for entry in result["modules"].values():
        assert {"package", "submodule", "error", "file"} <= set(entry)
