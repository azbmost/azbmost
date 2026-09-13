#!/usr/bin/env python3
"""AZBMOST universal launcher for the three GUI modules.

The launcher keeps module locations configurable while defaulting to sibling
directories next to this script:

    ../bnp_na/
    ../re_helix/
    ../curve_it/
"""
from __future__ import annotations

import ast
import json
import os
import platform
import re
import subprocess
import sys
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional


APP_NAME = "AZBMOST"
APP_TITLE = "AZBMOST Universal Launcher"
AZBMOST_REPO_URL = "https://github.com/azbmost"
SCRIPT_DIR = Path(__file__).resolve().parent
APP_ICON_FILE = SCRIPT_DIR / "assets" / "azbmost_icon.png"
CONFIG_PATH = Path.home() / ".azbmost_launcher.json"


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    title: str
    subtitle: str
    default_dir: str
    entry_script: str
    icon_candidates: tuple[str, ...]


@dataclass(frozen=True)
class ModuleMetadata:
    version: str = "unknown"
    other_tools: tuple[str, ...] = ()


MODULES: tuple[ModuleSpec, ...] = (
    ModuleSpec(
        key="bnp_na",
        title="BNP-NA",
        subtitle="Build and place nucleic acid helices",
        default_dir="../bnp_na",
        entry_script="bnp_na.py",
        icon_candidates=(
            "assets/bnp_na_icon.png",
            "assets/icon.png",
            "assets/bnp_na_icon.gif",
        ),
    ),
    ModuleSpec(
        key="re_helix",
        title="Re-Helix",
        subtitle="Reciprocal exchange and helix alignment",
        default_dir="../re_helix",
        entry_script="re_helix.py",
        icon_candidates=(
            "assets/icon.png",
            "assets/re_helix_icon.png",
            "assets/icon.gif",
        ),
    ),
    ModuleSpec(
        key="curve_it",
        title="Curve It",
        subtitle="Sculpt PDB structures along 3D curves",
        default_dir="../curve_it",
        entry_script="curve_it.py",
        icon_candidates=(
            "assets/icon.png",
            "assets/curve_it_icon.png",
            "assets/plane_it_icon.png",
            "assets/icon.gif",
        ),
    ),
)


VERSION_NAMES = ("__version__", "APP_VERSION", "SOFTWARE_VERSION")
OTHER_TOOLS_SECTION_MARKERS = (
    'text="Other tools"',
    "text='Other tools'",
    "# --- Other tools frame ---",
)
OTHER_TOOLS_END_MARKERS = (
    "\n        log_frame =",
    "\n    log_frame =",
    "\n    log_box =",
    "\n    buttons =",
    "# --- Run log frame ---",
    'text="Log output"',
    'text="Run log"',
    "text='Log output'",
    "text='Run log'",
)


def default_module_dir(spec: ModuleSpec) -> Path:
    return (SCRIPT_DIR / spec.default_dir).resolve()


def resolve_user_path(path_text: str) -> Path:
    path = Path(path_text.strip()).expanduser()
    if not path.is_absolute():
        path = (SCRIPT_DIR / path).resolve()
    return path


def load_config() -> Dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if isinstance(value, str)}


def save_config(paths: Dict[str, tk.StringVar]) -> None:
    data = {key: value.get().strip() for key, value in paths.items()}
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        messagebox.showwarning(APP_TITLE, f"Could not save launcher settings:\n\n{exc}")


# --------------------------------------------------------------- shared path
# "Shared Python path" lets the three modules import each other. One .pth file in
# the running interpreter's user site-packages holds the three REPO ROOTS, so each
# library is reached package-qualified -- curve_it_lib.x, re_helix_lib.y -- and the
# two copies of edit_pdb_atom stay distinct modules.
#
# Repo ROOTS, never the *_lib directories. Putting a lib dir on the path exposes its
# modules under bare names as well, so one file becomes two module objects with two
# different classes and isinstance() silently fails across them. re_helix_lib's
# re_helix_ccgV3_1 / re_helix_cckV3_1 already insert their own lib dir at sys.path[0]
# on import, which is exactly how that would happen here.
#
# State is never stored: save_config() rewrites ~/.azbmost_launcher.json wholesale
# from the path variables, and load_config() drops non-string values, so any flag
# kept there would be erased on the next Save. The panel measures instead.

PTH_FILENAME = "azbmost_paths.pth"
PTH_HEADER = "# Written by the AZBMOST launcher: Shared Python path. Delete to disable."

# What each module must expose for sharing to be useful. The second entry is a real
# submodule, because importing the bare package proves almost nothing.
PROBE_TARGETS: Dict[str, tuple[str, str]] = {
    "bnp_na": ("bnp_na_lib", "bnp_na_lib.build_arna"),
    "curve_it": ("curve_it_lib", "curve_it_lib.interpolate_xyz"),
    "re_helix": ("re_helix_lib", "re_helix_lib.edit_pdb_atom"),
}


def user_site_dir() -> Optional[Path]:
    """The user site-packages of the interpreter running this launcher.

    Returns None when user site is disabled -- inside a venv, or under python3 -s.
    site.getusersitepackages() still answers there, but with the BASE interpreter's
    directory, so writing to it would switch sharing on machine-wide for a Python
    this launcher is not even using.
    """
    try:
        import site

        if not getattr(site, "ENABLE_USER_SITE", False):
            return None
        return Path(site.getusersitepackages())
    except Exception:
        return None


def pth_file_path() -> Optional[Path]:
    site_dir = user_site_dir()
    return None if site_dir is None else site_dir / PTH_FILENAME


def configured_roots(path_vars: Dict[str, tk.StringVar]) -> Dict[str, Path]:
    """Configured repo root per module key, canonicalised.

    resolve() matters here: /Users/diliu/AllDropbox holds several spellings of the
    same tree ("ASU Dropbox/Di Liu", "Dropbox (ASU)"), and two spellings of one
    folder on sys.path would import every module twice.
    """
    roots: Dict[str, Path] = {}
    for spec in MODULES:
        var = path_vars.get(spec.key)
        if var is None:
            continue
        try:
            roots[spec.key] = resolve_user_path(var.get()).resolve()
        except Exception:
            continue
    return roots


def usable_roots(path_vars: Dict[str, tk.StringVar]) -> Dict[str, Path]:
    """Only the roots that exist and hold their entry script.

    Kept per-module on purpose: one moved folder must not strip the other two off
    the path of everything the launcher starts.
    """
    good: Dict[str, Path] = {}
    for spec in MODULES:
        root = configured_roots(path_vars).get(spec.key)
        if root is not None and root.is_dir() and (root / spec.entry_script).is_file():
            good[spec.key] = root
    return good


def read_pth_roots() -> list[Path]:
    path = pth_file_path()
    if path is None or not path.exists():
        return []
    roots: list[Path] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                roots.append(Path(line))
    except Exception:
        return []
    return roots


def write_pth(roots: Dict[str, Path]) -> Path:
    path = pth_file_path()
    if path is None:
        raise RuntimeError(
            "This interpreter has user site-packages disabled (a virtual environment, "
            "or python3 -s), so there is nowhere safe to write the shared path file.\n\n"
            "Start the launcher with the Python you use for the modules."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    # A .pth line is taken verbatim, so the spaces in the Dropbox paths need no quoting.
    body = [PTH_HEADER] + [str(root) for _key, root in sorted(roots.items())]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def remove_pth() -> Optional[Path]:
    path = pth_file_path()
    if path is None or not path.exists():
        return None
    path.unlink()
    return path


def shared_child_env(path_vars: Dict[str, tk.StringVar]) -> Optional[Dict[str, str]]:
    """Environment for a launched tool, with the usable roots put on PYTHONPATH.

    Given to tools the launcher starts so sharing works even before the .pth is
    written, and regardless of which interpreter ends up running the child.
    """
    roots = usable_roots(path_vars)
    if not roots:
        return None
    env = dict(os.environ)
    existing = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p.strip()]
    entries = [str(root) for _key, root in sorted(roots.items())]
    for item in existing:
        if item not in entries:
            entries.append(item)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env


_PROBE_CODE = """
import json, sys
targets = json.loads(sys.argv[1])
out = {}
for key, (pkg, submodule) in targets.items():
    entry = {"package": False, "submodule": False, "error": "", "file": ""}
    try:
        mod = __import__(pkg)
        entry["package"] = True
        entry["file"] = getattr(mod, "__file__", "") or ""
    except Exception as exc:
        entry["error"] = "%s: %s" % (type(exc).__name__, exc)
        out[key] = entry
        continue
    try:
        __import__(submodule)
        entry["submodule"] = True
    except Exception as exc:
        entry["error"] = "%s: %s" % (type(exc).__name__, exc)
    out[key] = entry
# A module reachable under both a bare and a dotted name is two objects with two
# sets of classes; report it rather than let it corrupt data silently.
twins = sorted(n for n in ("edit_pdb_atom", "align2z", "build_common", "core_BZ",
                           "na_placer", "interpolate_xyz", "geometry_utils")
               if n in sys.modules)
print("<<AZBMOST>>" + json.dumps({"modules": out, "flat_twins": twins}))
"""


def probe_shared_imports() -> Dict[str, object]:
    """Ask a fresh interpreter what it can actually import.

    Deliberately measured rather than inferred from the .pth file existing. The
    child starts from the home directory with PYTHONPATH stripped, so neither the
    launcher's own sys.path nor the empty PYTHONPATH entry that ~/.zprofile
    currently produces (a leading ':' puts the working directory on sys.path) can
    make a module look importable when it is not.
    """
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    try:
        completed = subprocess.run(
            [sys.executable or "python3", "-c", _PROBE_CODE, json.dumps(PROBE_TARGETS)],
            capture_output=True,
            text=True,
            cwd=str(Path.home()),
            env=env,
            timeout=60,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc), "modules": {}, "flat_twins": []}
    for line in (completed.stdout or "").splitlines():
        if line.startswith("<<AZBMOST>>"):
            try:
                payload = json.loads(line[len("<<AZBMOST>>"):])
            except Exception:
                break
            payload["ok"] = True
            return payload
    return {
        "ok": False,
        "error": (completed.stderr or "no output from the probe").strip()[:300],
        "modules": {},
        "flat_twins": [],
    }


def module_script_path(spec: ModuleSpec, module_dir: Path) -> Path:
    return module_dir / spec.entry_script


def find_icon_path(spec: ModuleSpec, module_dir: Path) -> Optional[Path]:
    for relative_path in spec.icon_candidates:
        icon_path = module_dir / relative_path
        if icon_path.exists():
            return icon_path
    return None


def literal_string(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract_version(source: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                value = literal_string(node.value)
                if value is None:
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in VERSION_NAMES:
                        return value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                value = literal_string(node.value) if node.value is not None else None
                if value is not None and node.target.id in VERSION_NAMES:
                    return value

    for name in VERSION_NAMES:
        match = re.search(rf"^\s*{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", source, re.MULTILINE)
        if match:
            return match.group(1)
    return "unknown"


def extract_other_tools_section(source: str) -> str:
    starts = [source.find(marker) for marker in OTHER_TOOLS_SECTION_MARKERS]
    starts = [index for index in starts if index >= 0]
    if not starts:
        return ""

    start = min(starts)
    end = len(source)
    for marker in OTHER_TOOLS_END_MARKERS:
        index = source.find(marker, start + 1)
        if index >= 0:
            end = min(end, index)
    return source[start:end]


def extract_other_tools(source: str) -> tuple[str, ...]:
    section = extract_other_tools_section(source)
    if not section:
        return ()

    labels: list[str] = []
    patterns = (
        r"(?:ttk|tk)\.Button\([^)]*?text\s*=\s*['\"]([^'\"]+)['\"]",
        # The helper's layout arguments may change (for example, from
        # ``column, label`` to ``row, column, label``).  Treat the first
        # string-literal positional argument as the displayed tool label.
        r"\badd_tool_button\((?:\s*[^,'\"\n]+,\s*)+['\"]([^'\"]+)['\"]",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, section, re.DOTALL):
            label = match.group(1).strip()
            if label and label not in labels:
                labels.append(label)
    return tuple(labels)


def read_module_metadata(spec: ModuleSpec, module_dir: Path) -> ModuleMetadata:
    script_path = module_script_path(spec, module_dir)
    if not script_path.is_file():
        return ModuleMetadata(version="unavailable")

    try:
        source = script_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ModuleMetadata(version="unreadable")

    return ModuleMetadata(
        version=extract_version(source),
        other_tools=extract_other_tools(source),
    )


def launch_command(script_path: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        python_exe = "python3"
    else:
        python_exe = sys.executable or "python3"
    return [python_exe, str(script_path)]


def open_in_file_manager(path: Path) -> None:
    if platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ModuleRow:
    def __init__(
        self,
        app: "AzbmostLauncher",
        parent: ttk.Frame,
        spec: ModuleSpec,
        row_index: int,
        initial_dir: Path,
    ) -> None:
        self.app = app
        self.spec = spec
        self.path_var = tk.StringVar(value=str(initial_dir))
        self.status_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.tools_var = tk.StringVar()
        self.icon_image: Optional[tk.PhotoImage] = None

        frame = ttk.Frame(parent, padding=(0, 10))
        frame.grid(row=row_index, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1)

        self.icon_label = ttk.Label(frame, width=8, anchor="center")
        self.icon_label.grid(row=0, column=0, rowspan=5, sticky="n", padx=(0, 12))

        title_frame = ttk.Frame(frame)
        title_frame.grid(row=0, column=1, columnspan=4, sticky="ew")
        ttk.Label(title_frame, text=spec.title, style="ModuleTitle.TLabel").pack(side="left")
        ttk.Label(title_frame, text=f"  {spec.subtitle}", style="Subtitle.TLabel").pack(side="left")

        entry = ttk.Entry(frame, textvariable=self.path_var)
        entry.grid(row=1, column=1, sticky="ew", pady=(6, 3))
        entry.bind("<FocusOut>", lambda _event: self.on_path_changed())
        entry.bind("<Return>", lambda _event: self.on_path_changed())

        ttk.Button(frame, text="Browse...", command=self.browse).grid(row=1, column=2, padx=(8, 0), pady=(6, 3))
        ttk.Button(frame, text="Launch", command=self.launch).grid(row=1, column=3, padx=(8, 0), pady=(6, 3))
        ttk.Button(frame, text="Open Folder", command=self.open_folder).grid(
            row=1, column=4, padx=(8, 0), pady=(6, 3)
        )

        ttk.Label(frame, textvariable=self.status_var, style="Status.TLabel").grid(
            row=2, column=1, columnspan=4, sticky="w"
        )
        ttk.Label(frame, textvariable=self.version_var, style="Metadata.TLabel").grid(
            row=3, column=1, columnspan=4, sticky="w"
        )
        ttk.Label(
            frame,
            textvariable=self.tools_var,
            style="Metadata.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=4, column=1, columnspan=4, sticky="w")

        self.path_var.trace_add("write", lambda *_args: self.refresh(save=False))
        self.refresh(save=False)

    def browse(self) -> None:
        directory = filedialog.askdirectory(
            title=f"Choose {self.spec.title} folder",
            initialdir=str(resolve_user_path(self.path_var.get())),
            mustexist=True,
        )
        if directory:
            self.path_var.set(directory)
            self.on_path_changed()

    def on_path_changed(self) -> None:
        self.refresh(save=True)
        # The .pth holds the folders as they were when Enable ran. Re-point a module
        # and it goes stale, so re-measure rather than leave the panel claiming a
        # state that no longer matches what a fresh interpreter would import.
        self.app.on_module_paths_changed()

    def open_folder(self) -> None:
        module_dir = resolve_user_path(self.path_var.get())
        if not module_dir.exists():
            messagebox.showerror(APP_TITLE, f"Folder not found:\n\n{module_dir}")
            return
        try:
            open_in_file_manager(module_dir)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not open folder:\n\n{exc}")

    def launch(self) -> None:
        module_dir = resolve_user_path(self.path_var.get())
        script_path = module_script_path(self.spec, module_dir)

        if not module_dir.is_dir():
            messagebox.showerror(APP_TITLE, f"{self.spec.title} folder not found:\n\n{module_dir}")
            return
        if not script_path.is_file():
            messagebox.showerror(
                APP_TITLE,
                f"Could not find {self.spec.entry_script} in:\n\n{module_dir}\n\n"
                "Please choose the module repository folder.",
            )
            return

        env = shared_child_env(self.app.path_vars)
        try:
            subprocess.Popen(launch_command(script_path), cwd=str(module_dir), env=env)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch {self.spec.title}:\n\n{exc}")
            return

        shared_count = len(usable_roots(self.app.path_vars))
        if env is not None and shared_count > 1:
            self.app.set_footer(
                f"Launched {self.spec.title} with {shared_count} module folders on its Python path."
            )
        else:
            self.app.set_footer(f"Launched {self.spec.title}.")
        self.on_path_changed()

    def refresh(self, *, save: bool) -> None:
        module_dir = resolve_user_path(self.path_var.get())
        script_path = module_script_path(self.spec, module_dir)
        icon_path = find_icon_path(self.spec, module_dir)
        metadata = read_module_metadata(self.spec, module_dir)

        if script_path.is_file():
            status = f"Ready: {script_path}"
        elif module_dir.is_dir():
            status = f"Folder found, but {self.spec.entry_script} is missing."
        else:
            status = "Folder not found."
        if icon_path:
            status += f"  Icon: {icon_path.name}"
        else:
            status += "  Icon: not found"
        self.status_var.set(status)
        self.version_var.set(f"Version: {metadata.version}")
        if metadata.other_tools:
            self.tools_var.set(f"Other tools: {', '.join(metadata.other_tools)}")
        else:
            self.tools_var.set("Other tools: none detected")

        self.set_icon(icon_path)
        if save:
            save_config(self.app.path_vars)

    def set_icon(self, icon_path: Optional[Path]) -> None:
        if not icon_path:
            self.icon_image = self.app.placeholder_icon
            self.icon_label.configure(image=self.icon_image, text="")
            return

        try:
            image = tk.PhotoImage(file=str(icon_path))
        except Exception:
            self.icon_image = self.app.placeholder_icon
            self.icon_label.configure(image=self.icon_image, text="")
            return

        max_size = 56
        max_dimension = max(image.width(), image.height())
        factor = max(1, (max_dimension + max_size - 1) // max_size)
        if factor > 1:
            image = image.subsample(factor, factor)
        self.icon_image = image
        self.icon_label.configure(image=self.icon_image, text="")


class AzbmostLauncher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.app_icon: Optional[tk.PhotoImage] = None
        self.path_vars: Dict[str, tk.StringVar] = {}
        self.placeholder_icon = self.make_placeholder_icon()
        self.footer_var = tk.StringVar(value="Choose module folders if they are not in the default sibling locations.")
        self.shared_var = tk.StringVar(value="Shared Python path: checking…")
        self.shared_detail_var = tk.StringVar(value="")

        self.configure_window()
        self.build_ui()
        # Measure after the window is up; the probe spawns an interpreter.
        self.root.after(150, self.recheck_shared)

    def configure_window(self) -> None:
        self.root.title(APP_TITLE)
        self.root.minsize(880, 560)
        self.set_window_icon()

        style = ttk.Style()
        if platform.system() == "Darwin":
            style.theme_use("aqua")
        style.configure("ModuleTitle.TLabel", font=("", 15, "bold"))
        style.configure("Subtitle.TLabel", foreground="#555555")
        style.configure("Status.TLabel", foreground="#666666")
        style.configure("Metadata.TLabel", foreground="#444444")
        style.configure("Footer.TLabel", foreground="#333333")
        style.configure("Link.TLabel", foreground="#0b66c3")

    def set_window_icon(self) -> None:
        if not APP_ICON_FILE.exists():
            return
        try:
            self.app_icon = tk.PhotoImage(file=str(APP_ICON_FILE))
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            self.app_icon = None

    def build_ui(self) -> None:
        config = load_config()

        outer = ttk.Frame(self.root, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(outer, text=APP_TITLE, font=("", 20, "bold")).grid(row=0, column=0, sticky="w")
        repo_link = ttk.Label(outer, text=AZBMOST_REPO_URL, cursor="hand2", style="Link.TLabel")
        repo_link.grid(row=1, column=0, sticky="w", pady=(3, 0))
        repo_link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(AZBMOST_REPO_URL))
        ttk.Label(
            outer,
            text="Set the location of each module repository, then launch its GUI with one click.",
            style="Subtitle.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(4, 14))

        rows_frame = ttk.Frame(outer)
        rows_frame.grid(row=3, column=0, sticky="nsew")
        rows_frame.columnconfigure(0, weight=1)

        for row_index, spec in enumerate(MODULES):
            initial = Path(config.get(spec.key, str(default_module_dir(spec))))
            row = ModuleRow(self, rows_frame, spec, row_index * 2, initial)
            self.path_vars[spec.key] = row.path_var
            if row_index < len(MODULES) - 1:
                ttk.Separator(rows_frame).grid(row=row_index * 2 + 1, column=0, sticky="ew", pady=(1, 0))

        shared = ttk.Frame(outer)
        shared.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        shared.columnconfigure(0, weight=1)
        ttk.Separator(shared).grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        ttk.Label(shared, textvariable=self.shared_var, style="Metadata.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Button(shared, text="Enable", command=self.enable_shared).grid(row=1, column=1, padx=(8, 0))
        ttk.Button(shared, text="Disable", command=self.disable_shared).grid(row=1, column=2, padx=(8, 0))
        ttk.Button(shared, text="Re-check", command=self.recheck_shared).grid(row=1, column=3, padx=(8, 0))
        ttk.Label(shared, textvariable=self.shared_detail_var, style="Status.TLabel").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(4, 0)
        )

        controls = ttk.Frame(outer)
        controls.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        controls.columnconfigure(0, weight=1)
        ttk.Label(controls, textvariable=self.footer_var, style="Footer.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(controls, text="Reset Defaults", command=self.reset_defaults).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(controls, text="Save Settings", command=self.save_settings).grid(row=0, column=2, padx=(8, 0))

    def make_placeholder_icon(self) -> tk.PhotoImage:
        image = tk.PhotoImage(width=56, height=56)
        image.put("#f1f5f9", to=(0, 0, 56, 56))
        image.put("#64748b", to=(4, 4, 52, 52))
        image.put("#ffffff", to=(8, 8, 48, 48))
        image.put("#94a3b8", to=(18, 18, 38, 38))
        return image

    def reset_defaults(self) -> None:
        for spec in MODULES:
            self.path_vars[spec.key].set(str(default_module_dir(spec)))
        self.save_settings()
        self.set_footer("Restored default sibling module locations.")

    def save_settings(self) -> None:
        save_config(self.path_vars)
        self.set_footer(f"Saved settings to {CONFIG_PATH}.")

    def set_footer(self, text: str) -> None:
        self.footer_var.set(text)

    # ----------------------------------------------------------- shared path
    def on_module_paths_changed(self) -> None:
        """A module folder moved. Rewrite the .pth if sharing is on, then re-measure."""
        if pth_file_path() is not None and read_pth_roots():
            roots = usable_roots(self.path_vars)
            if roots:
                try:
                    write_pth(roots)
                except Exception:
                    pass
        self.recheck_shared()

    def recheck_shared(self) -> None:
        result = probe_shared_imports()
        pth = pth_file_path()
        installed = bool(read_pth_roots())

        if not result.get("ok"):
            self.shared_var.set("Shared Python path: could not measure")
            self.shared_detail_var.set(str(result.get("error", ""))[:160])
            return

        modules = result.get("modules", {})
        full, partial, missing = [], [], []
        for spec in MODULES:
            entry = modules.get(spec.key, {})
            if entry.get("submodule"):
                full.append(spec.title)
            elif entry.get("package"):
                partial.append(spec.title)
            else:
                missing.append(spec.title)

        if not full and not partial:
            self.shared_var.set("Shared Python path: OFF")
            self.shared_detail_var.set(
                "The modules cannot import each other outside the launcher. "
                + (f"Enable writes {pth}." if pth else "No user site-packages on this interpreter.")
            )
            return

        state = "ON" if installed else "ON (from something other than this launcher)"
        self.shared_var.set(f"Shared Python path: {state} — {len(full)} of {len(MODULES)} fully importable")
        bits = []
        if full:
            bits.append("importable: " + ", ".join(full))
        if partial:
            bits.append(
                "package only: " + ", ".join(partial)
                + " (its library imports its own modules by bare name, so submodules need migrating)"
            )
        if missing:
            bits.append("not importable: " + ", ".join(missing))
        twins = result.get("flat_twins") or []
        if twins:
            bits.append("WARNING duplicate module identities: " + ", ".join(twins))
        self.shared_detail_var.set("  ·  ".join(bits)[:400])

    def enable_shared(self) -> None:
        roots = usable_roots(self.path_vars)
        if not roots:
            messagebox.showerror(
                APP_TITLE,
                "None of the module folders could be found, so there is nothing to share.\n\n"
                "Set the folders above first.",
            )
            return
        target = pth_file_path()
        if target is None:
            messagebox.showerror(
                APP_TITLE,
                "This interpreter has user site-packages disabled (a virtual environment, or "
                "python3 -s), so writing the shared path file would affect a different Python "
                "than the one running here.\n\nStart the launcher with the Python you use for "
                "the modules.",
            )
            return
        skipped = [s.title for s in MODULES if s.key not in roots]
        listing = "\n".join(f"    {root}" for _key, root in sorted(roots.items()))
        note = f"\n\nNot included (folder or entry script missing): {', '.join(skipped)}" if skipped else ""
        if not messagebox.askokcancel(
            APP_TITLE,
            f"Write this one file:\n\n    {target}\n\ncontaining these folders:\n\n{listing}{note}\n\n"
            "Every Python program run with this interpreter will then be able to import them. "
            "Disable removes the file.",
        ):
            return
        try:
            written = write_pth(roots)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not enable the shared path:\n\n{exc}")
            return
        self.recheck_shared()
        self.set_footer(f"Wrote {written}.")

    def disable_shared(self) -> None:
        try:
            removed = remove_pth()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not remove the shared path file:\n\n{exc}")
            return
        self.recheck_shared()
        if removed is None:
            self.set_footer("No shared path file written by this launcher was found.")
        else:
            self.set_footer(f"Removed {removed}.")


def main() -> int:
    root = tk.Tk()
    AzbmostLauncher(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
