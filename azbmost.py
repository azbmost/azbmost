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

        try:
            subprocess.Popen(launch_command(script_path), cwd=str(module_dir))
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not launch {self.spec.title}:\n\n{exc}")
            return

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

        self.configure_window()
        self.build_ui()

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

        controls = ttk.Frame(outer)
        controls.grid(row=4, column=0, sticky="ew", pady=(18, 0))
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


def main() -> int:
    root = tk.Tk()
    AzbmostLauncher(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
