# AZBMOST Universal Launcher

AZBMOST is a small graphical launcher for three structural-biology tools:

- **BNP-NA** — build and place nucleic-acid helices
- **Re-Helix** — align helices and perform reciprocal exchange
- **Curve It** — sculpt PDB structures along three-dimensional curves

The tools remain independent repositories. This repository contains only the
launcher and its documentation.

## Repository layout

Keep the launcher and tool repositories side by side for the default paths to
work:

```text
parent-folder/
├── azbmost/
│   ├── assets/
│   ├── azbmost.py
│   ├── MANUAL.md
│   └── README.md
├── bnp_na/
├── re_helix/
└── curve_it/
```

The launcher expects these entry scripts by default:

| Tool | Default folder | Entry script |
| --- | --- | --- |
| BNP-NA | `../bnp_na` | `bnp_na.py` |
| Re-Helix | `../re_helix` | `re_helix.py` |
| Curve It | `../curve_it` | `curve_it.py` |

Relative paths are resolved from the folder containing `azbmost.py`, not from
the terminal's current working directory. You can choose different folders in
the launcher; those choices are saved in `~/.azbmost_launcher.json`.

## Requirements

- Python 3.9 or newer
- Tkinter
- Separate local checkouts of the tools you want to launch

Each tool has its own dependencies. See [MANUAL.md](MANUAL.md) and the tool's
own documentation for details.

## Run

```bash
python3 azbmost.py
```

If a tool is not stored in the default sibling location, use **Browse…** to
select its repository folder. The launcher starts each tool from its own folder
so that the tool's internal relative paths work as intended.

## Documentation

See [MANUAL.md](MANUAL.md) for installation guidance, launcher behavior, and
detailed usage of BNP-NA, Re-Helix, and Curve It.
