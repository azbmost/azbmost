# AZBMOST Package Manual

**AZBMOST** (from DiLiuLab) is a small suite of Python tools for building, editing,
and reshaping atomic models of nucleic acids (and, in places, proteins) for
structural DNA/RNA nanotechnology and structural-biology model building. This
manual covers the three tools distributed with the package, their scientific
principles, and their day-to-day usage.

| # | Tool | Folder | Version | One-line purpose |
| --- | --- | --- | --- | --- |
| 1 | **BNP-NA** (`bnp_na`) | `../bnp_na/` | V13.9 | Build and place B/A/Z-DNA and A-RNA helices; B-Z, triplex, and analysis helpers |
| 2 | **Re-Helix** (`re_helix`) | `../re_helix/` | V3.18 | Align helices and perform reciprocal exchanges (crossovers/junctions) |
| 3 | **Curve It** (`curve_it`) | `../curve_it/` | V3_4 | Sculpt a straight PDB structure so its axis follows any 3D curve |

The `azbmost.py` script in this folder is a universal launcher: it lets you point
at each module's folder and start its GUI with one click. This manual is the
single combined reference for all three tools; each tool folder also ships its
own `README.md` and `CHANGELOG.md` with the fine-grained, version-by-version
details.

---

## Table of Contents

1. [How the package fits together](#1-how-the-package-fits-together)
2. [Shared concepts and file formats](#2-shared-concepts-and-file-formats)
3. [Installation and dependencies](#3-installation-and-dependencies)
4. [The AZBMOST launcher](#4-the-azbmost-launcher)
5. [Tool 1 — BNP-NA: build and place nucleic acid helices](#5-tool-1--bnp-na-build-and-place-nucleic-acid-helices)
6. [Tool 2 — Re-Helix: align helices and reciprocal exchange](#6-tool-2--re-helix-align-helices-and-reciprocal-exchange)
7. [Tool 3 — Curve It: sculpt structures along a 3D curve](#7-tool-3--curve-it-sculpt-structures-along-a-3d-curve)
8. [A worked cross-tool example](#8-a-worked-cross-tool-example)
9. [Troubleshooting quick reference](#9-troubleshooting-quick-reference)

---

## 1. How the package fits together

The three tools are independent programs, but they are designed to hand PDB
files to one another in a natural pipeline:

```
        BNP-NA                     Re-Helix                    Curve It
  build a straight helix  ->  align helices and cut/    ->  bend the finished
  (B/A/Z-DNA, A-RNA),         reconnect their backbones     assembly so its axis
  place it in space           into crossovers, junctions,   follows an arbitrary
                              bowties; symmetrize, add       3D curve (rings,
                              LINK records, restraints       super-helices, knots)
```

A typical design starts by generating idealized helical building blocks with
**BNP-NA**, wires them together into the intended nanostructure topology with
**Re-Helix**, and (when a curved or closed geometry is wanted) reshapes the
result along a designed path with **Curve It**. Each tool is also fully useful on
its own, and each bundles a set of smaller stand-alone utilities.

Every tool runs in two modes:

- A **Tkinter GUI**, launched with no arguments (or `--gui`), which is the
  primary interface and exposes an embedded run log.
- A **command line** interface for scripting and reproducibility.

All three write provenance and are conservative about your inputs: they operate
on copies and write new files rather than editing sources in place.

---

## 2. Shared concepts and file formats

Understanding a handful of shared ideas makes all three tools easier to use.

### PDB coordinate files

The common currency of the package is the **PDB** file: a plain-text atomic
coordinate format with `ATOM`/`HETATM` records (element coordinates), `TER`
records (chain-end markers), `LINK` records (explicit inter-atom bonds),
`CONECT` records (connectivity), and `REMARK` records (annotations). AZBMOST
tools read these records, transform coordinates, and rewrite them while keeping
chain IDs, residue numbers, and topology consistent.

### Nucleic-acid geometry and DSSR

Double-helical nucleic acids are described by a small set of **base-pair and
helical step parameters** (shear, stretch, stagger, buckle, propeller, opening,
x-displacement, y-displacement, rise, inclination, tip, and twist). BNP-NA uses
these 12 parameters to generate idealized helices through **DSSR**
(`x3dna-dssr`), the analysis/rebuild engine from the 3DNA/DSSR software. DSSR is
also used across the package to extract a helix's **helical axis** (the straight
line the base-pair centers spiral around). Several tools accept or report axis
start/end points and unit vectors.

DSSR is required by BNP-NA for real model building and by a few optional
features elsewhere (e.g., Plane It base-pair lines). Install `x3dna-dssr` and
make sure it is on your `PATH`, or at `/usr/local/bin/x3dna-dssr`.

### Handedness, B/A/Z forms, and L-nucleic acids

Right-handed **B-DNA** is the canonical form; **A-DNA/A-RNA** are right-handed
but more compact and inclined; **Z-DNA** is a left-handed form with an
alternating-backbone zig-zag. Beyond backbone conformation, the sugars
themselves have a fixed chirality; a full mirror image (an **L-nucleic acid**)
requires an *improper* transform (determinant −1), which BNP-NA supports through
its inversion/reflection ("L-form") option. See BNP-NA's principles below for
why inversion combined with a 180° rotation yields a true reflection.

### Reciprocal exchange (crossovers and junctions)

Structural DNA nanotechnology, founded by Nadrian C. Seeman, treats DNA as a
programmable building material: designed sequence asymmetry creates *immobile*
branched junctions that act as predictable vertices for objects, arrays, and
lattices. A **reciprocal exchange** is the corresponding modeling operation — it
cuts the backbone graph of two strands at chosen sites and reconnects them so
the strands trade partners, producing a crossover, junction, or bowtie without
rebuilding every atom by hand. Re-Helix is the tool for this operation.

### Phenix geometry restraints and minimization

After topology edits, models are often relaxed with
`phenix.geometry_minimization`. BNP-NA can call it directly for freshly built
helices, and Re-Helix's *Get Phenix Restraints* helper turns `LINK` records into
Phenix restraint files so custom junctions and linkers minimize with correct
bonds and angles. These features are optional and only used when Phenix is
installed.

### BILD drawings for Chimera / ChimeraX

Several analysis helpers write Chimera/ChimeraX **`.bild`** files — simple
scene-description files of arrows, spheres, and colors — so you can overlay a
fitted axis, radial vectors, coordinate axes, or a symmetry axis on your model
in a molecular viewer.

### XYZ / coordinate curve files

Curve It and its helpers use lightweight **XYZ / plain-coordinate** files: one
`x y z` point per line, optionally with an XYZ header and element labels, and
optionally with several components separated by blank lines (labeled `A`, `B`,
`C`, …). These define the 3D path a structure is bent onto.

### Arithmetic in numeric GUI fields

Numeric fields in the GUIs generally accept simple arithmetic expressions
(e.g., `360/10.5`, `6*4`, `(20+10)/2`) in addition to plain numbers, which is
convenient for entering derived geometric values.

---

## 3. Installation and dependencies

**Python:** 3.9 or newer for all three tools.

**Per-tool Python packages:**

| Tool | Required | Optional |
| --- | --- | --- |
| BNP-NA | NumPy, Tkinter | Phenix (external) |
| Re-Helix | (none for CLI); Tkinter for GUI | Phenix (external) |
| Curve It | NumPy | SciPy (curvature/writhe), Matplotlib (curve viewer/plots), Tkinter (GUI) |

**External programs:**

- **`x3dna-dssr`** — required for BNP-NA model generation and axis extraction;
  optional for Curve It's Plane It base-pair lines. Put it on `PATH` or at
  `/usr/local/bin/x3dna-dssr`.
- **Phenix** (`phenix.geometry_minimization`) — optional. Put it on `PATH`, or
  set `PHENIX_ENV` to a Phenix environment script.

**Tkinter note:** Tkinter ships with most python.org and system Python installs
and is only needed for GUI mode. All three tools can print their version and run
their command-line features without a display. (`python3 bnp_na.py --version`,
`python3 re_helix.py --version`, and `python3 curve_it.py --version` all work
without Tkinter.)

**Install per tool:**

```bash
python3 -m pip install -r bnp_na/requirements.txt      # NumPy
python3 -m pip install -r curve_it/requirements.txt    # NumPy (+ optional extras)
# re_helix needs no third-party packages for its CLI workflow
```

**Cloning and updating** (each tool is its own Git repository):

```bash
git clone https://github.com/azbmost/bnp_na.git
git clone https://github.com/azbmost/re_helix.git
git clone https://github.com/azbmost/curve_it.git
# later, inside a clone:
git pull
```

---

## 4. The AZBMOST launcher

`azbmost.py` (in this folder) is a Tkinter front end that starts each tool's GUI.

**Run it:**

```bash
python3 azbmost.py
```

For each of the three modules it shows a row with:

- an editable **folder path** (defaults to the sibling folders `../bnp_na`,
  `../re_helix`, `../curve_it`);
- **Browse…**, **Launch**, and **Open Folder** buttons;
- a status line that reports whether the entry script and icon were found;
- the detected **version** and any **"Other tools"** buttons parsed from the
  module.

Paths you set are remembered in `~/.azbmost_launcher.json`. **Reset Defaults**
restores the sibling locations; **Save Settings** writes the current paths.
**Launch** runs the module's entry script (`bnp_na.py`, `re_helix.py`, or
`curve_it.py`) from its own folder so relative library paths resolve correctly.

Use the launcher when you keep the three repositories side by side and want a
single click to open any of them; otherwise, run each tool's script directly.

---

## 5. Tool 1 — BNP-NA: build and place nucleic acid helices

> Folder `../bnp_na/` · entry `bnp_na.py` · version **V13.9** ·
> GUI title *"AZBMOST Package Module #1 — Build and Place Nucleic Acid"*

### 5.1 Principle

BNP-NA generates **idealized, parameter-defined helices** and then puts them
where you want them in space. Model building is delegated to DSSR: for B-DNA,
A-DNA, and A-RNA the tool writes a 12-column base-pair/helical-step parameter
table and calls `x3dna-dssr rebuild ... --par-type=heli`; for Z-DNA it uses
DSSR's built-in fiber model (`x3dna-dssr fiber --model=Z-DNA`). Because the
geometry comes from an explicit parameter table, every helix is reproducible and
tunable rather than copied from a reference structure.

After building, BNP-NA runs a fixed, inspectable **pipeline**:

```
build (DSSR)  ->  standardize residue/atom names  ->  optional Phenix minimization
   ->  align helix axis to +Z (via DSSR axis)  ->  optional L-form mirror
   ->  orient and place (roll, phi, theta, x, y, z)
```

Aligning the axis to **+Z** first is the key design decision: once the helix
starts at the origin and points along +Z, the placement controls (a roll about
the axis, a `phi` tilt, a `theta` swing, and a final translation) have a
predictable, composable meaning, and the optional mirror operation acts in a
known frame.

**Why the L-form uses inversion + rotation.** Changing chirality (making a true
mirror-image, L-nucleic-acid model) requires an improper transform — determinant
−1. A pure rotation has determinant +1 and can never produce a mirror image.
Point inversion `(x,y,z) → (−x,−y,−z)` has determinant −1, so BNP-NA composes
inversion with optional 180° rotations to realize a chosen reflection plane
(e.g., `oyz` = inversion + a 180° rotation about x = reflection across the yz
plane). After align-to-Z, `oyz`/`oxz` preserve the +Z sense while `oxy`/plain
`i` reverse it.

Every final model carries machine-readable `REMARK BNP_NA…` provenance,
including the tool version, repository link, and (for mirror models) explicit
L-residue annotations.

### 5.2 The main build workflow

**Launch:** `python3 bnp_na.py` (GUI) or `python3 bnp_na.py --version`.

Steps in the GUI:

1. Check the startup status line for `x3dna-dssr` (`FOUND`/`NOT FOUND`).
2. Choose **B-DNA**, **A-DNA**, **A-RNA**, or **Z-DNA**.
3. For B/A-DNA and A-RNA, enter a 5'→3' sequence (DNA uses `A T C G`; RNA uses
   `A U C G`). Whitespace is ignored, and compact counts are supported —
   `A10T5C2G` expands to ten A, five T, two C, one G. For Z-DNA the sequence
   field is disabled; enter a **positive even** helix length instead (the tool
   passes `length/2` as the DSSR repeat count).
4. Optionally set a **helix name** (blank yields a default like `B-DNA25`).
5. Choose an **output folder**.
6. Adjust DSSR parameters, minimization, hydrogen deletion, L-form mirror, and
   placement values as needed.
7. Click **Generate** and read the embedded log — it records every command,
   intermediate file, and the final placed PDB path.

**Outputs.** The final placed model is written directly in the output folder as
`<helix-name>_oriented_placed.pdb` (mirror models add an L-form label such as
`_L_o_yz`). All intermediates (DSSR tables, rebuilt/normalized/minimized/aligned
PDBs, DSSR reports) go in `<output folder>/tmp_file/`. For B-DNA, the `rb` number
in intermediate names is the helical repeat `360 / h-Twist` (default twist
34.2857° → `rb10.5`).

### 5.3 Helix types at a glance

| Type | DSSR command | 12-parameter table | Default minimization |
| --- | --- | --- | --- |
| B-DNA | `rebuild --backbone=B-DNA --par-type=heli` | yes | on |
| A-DNA | `rebuild --backbone=A-DNA --par-type=heli` | yes | off |
| A-RNA | `rebuild --backbone=RNA --par-type=heli` | yes | off |
| Z-DNA | `fiber --model=Z-DNA` | no | not available |

### 5.4 DSSR parameter customization

**Customize DSSR parameters** opens a 12-column table (Shear, Stretch, Stagger,
Buckle, Propeller, Opening, X-disp, Y-disp, h-Rise, Incl., Tip, h-Twist), stored
separately per nucleic-acid type. The first six are local base-pair parameters;
the last six are local helical-step parameters (the final row uses `999999` for
step values because there is no next base pair). Translations are in Å, angles in
degrees, written with four decimals. Blank fields fall back to the built-in
defaults:

| NA | Shear | Stretch | Stagger | Buckle | Propeller | Opening | X-disp | Y-disp | h-Rise | Incl. | Tip | h-Twist |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B-DNA | 0.0000 | −0.1500 | 0.0900 | 0.5000 | −11.4000 | 0.6000 | 0.0500 | 0.0200 | 3.4000 | 2.1000 | 0.0000 | 34.2857 |
| A-DNA | 0.0001 | −0.1448 | 0.0638 | 0.0003 | −10.5158 | −1.8170 | −4.4616 | 0.0001 | 2.5466 | 22.6460 | 0.0001 | 32.7273 |
| A-RNA | 0.0137 | −0.0848 | 0.0126 | −0.0044 | −2.0765 | −1.6676 | −4.0513 | 0.0678 | 2.8120 | 15.5148 | 0.7866 | 32.7273 |

Only values you change from the defaults are logged as GUI overrides.

### 5.5 Placement and orientation

After align-to-Z, the placement controls transform the aligned model in this
fixed order:

1. shift along local +Z by `delta_z` (usually leave at 0);
2. `roll` about the local +Z axis;
3. `phi` rotation about the Y axis (tilt away from +Z);
4. `theta` rotation about the Z axis (swing the tilt around);
5. translate by `x`, `y`, `z`.

Distances (`x,y,z,delta_z`) are in Å; angles (`roll,phi,theta`) in degrees. A GUI
note reminds you that a roll copied from GIDEON should be entered as
`roll = roll_at_GIDEON − 111.25`.

### 5.6 Phenix minimization, name standardization, delete-H

- **Phenix minimization** (defaults: B-DNA on; A/RNA off; Z-DNA N/A) relaxes the
  normalized PDB before align-to-Z using the bundled
  `bnp_na_lib/min_P_C5.params` (a deliberately small params file that relaxes the
  link-distance cutoff and selects phosphate/near-sugar atoms). If Phenix is not
  found, add it to `PATH` or set `PHENIX_ENV`.
- **Name standardization** (`bnp_na_lib/pdb_name_standard.py`) cleans the
  DSSR-generated PDB: DNA `A/T/C/G → DA/DT/DC/DG`, canonicalizes 3-letter names,
  preserves RNA (`O2'`), renames `O2*→O2'`, `O1P/O2P→OP1/OP2`, and DT methyl
  atoms to `C7/H7*`; optionally deletes hydrogens.
- **Delete hydrogens** removes H atoms during standardization for all four types
  when you want a heavy-atom-only starting model.

### 5.7 Mirror-image L-form modeling

Enable **Apply inv/rot after align-to-Z** to build L-nucleic-acid mirror models.
Two labeling styles are offered:

- **`i` mode** — inversion plus optional 180° rotations: `i`, `ix`, `iy`, `iz`,
  `ixy`, `ixz`, `iyz`, `ixyz`.
- **`o` mode** — name the reflection plane directly: `oxy`, `oyz` (GUI default),
  `oxz`, implemented internally as inversion plus a 180° rotation about the
  perpendicular axis.

The final PDB name includes the L-form label and the file carries
`REMARK BNP_NA_L_FORM YES` plus per-residue L-DNA/L-RNA annotations.

### 5.8 Bundled tools (the "Other tools" and builder buttons)

BNP-NA ships several stand-alone helpers, reachable from GUI buttons and also
runnable directly from `bnp_na_lib/`:

- **B-Z structure builder** (`make_BZV2_3.py`, `core_BZ.py`). Joins already-built
  B-DNA and Z-DNA PDBs through bundled B-Z junction cores. Inputs are given in
  strict alternating order starting with B (`B1 Z1 B2 Z2 …`), fitted with sugar
  atoms, with **axis correction** (`codirectional` default / `collinear` /
  `none`), an **axis source** (`auto`/`dssr`/`pca`), and optional **Z-DNA
  terminal auto-trim** (each Z chain should start pyrimidine, end purine; prepare
  Z inputs 2 bp long so at most one bp can be trimmed per end).
- **Triplex converter** (`convert_to_triplex_pdbV2_1.py`). Adds a Hoogsteen /
  reverse-Hoogsteen third strand over a chosen strand-I range, writing triplets
  `Z·X-Y`. Modes: `antiparallel` (`G·G-C`, strand-I range all G) and `parallel`
  (`T·A-T`, strand-I range all A). Output defaults to `<name>_2TH.pdb`.
- **Measure angle around axis** (`angle_helical_axisV2_2.py`). Reports radial
  distances/vectors and the signed/unsigned angle between two points around a
  helical axis (fitted from a PDB by PCA/SVD on `C1'`, or custom), and can fit a
  local **2-fold symmetry axis** for paired residue regions; writes a `.bild`.
- **Align helix to z** (`align2z.py`). Uses DSSR `--more` axis endpoints to
  translate a helix's axis start to the origin and rotate the axis onto +Z.
- **Get helical-axis info** (`helical_axis_info.py`). Filters a PDB to two chains,
  runs DSSR `--more`, and reports axis start/end/vector/unit-vector, distance,
  the angle to a reference vector, and an estimated full helix length; optional
  `.bild`.
- **Add phosphates** (`add_phosphates.py`). Reports and adds missing terminal 5'
  and 3' phosphates using local neighbor geometry; renumbers and remaps `CONECT`.
- **Write XYZ axes BILD** (`xyz_bild.py`). Writes a coordinate-axis `.bild`
  (origin sphere; red X, yellow Y, blue Z arrows) with configurable length/width.

**Representative CLI usage:**

```bash
python3 bnp_na.py --version
python3 bnp_na_lib/make_BZV2_3.py --axis-mode codirectional --out multi_BZ.pdb B1.pdb Z1.pdb B2.pdb
python3 bnp_na_lib/convert_to_triplex_pdbV2_1.py duplex.pdb --strand-I A --range 10:18 --mode antiparallel
python3 bnp_na_lib/angle_helical_axisV2_2.py -i helix.pdb --point1 "A:5:C1*" --point2 "B:18:C1*"
python3 bnp_na_lib/helical_axis_info.py -i model.pdb --chains "C D" --helix-bp 24 --bild axis.bild
python3 bnp_na_lib/add_phosphates.py model.pdb -o model_add_phosphates.pdb --chains "A B" --ends both
python3 bnp_na_lib/xyz_bild.py -o xyz_axes.bild --length 30 --width 0.75
```

*(See `bnp_na/README.md` for the exhaustive option lists and the full field
guide.)*

---

## 6. Tool 2 — Re-Helix: align helices and reciprocal exchange

> Folder `../re_helix/` · entry `re_helix.py` · version **V3.18** ·
> *"AZBMOST Package Module #2 — Align Helices and Performing Reciprocal Exchanges"*

### 6.1 Principle

Re-Helix does two related things: it **aligns** nucleic-acid helices to a
target relative geometry, and it performs **reciprocal exchanges** on the aligned
(or original) structure.

A **reciprocal exchange** is a virtual topology edit. Given residues on two
strands or helices, the tool cuts the backbone graph at those sites and
reconnects it so the strand continuities are exchanged — turning two separate
duplexes into a crossover, a branched junction, or a bowtie. This is a *design*
operation, not an enzymatic simulation; it produces the intended strand routing
(atom records, chain breaks, residue numbering, `TER`, and `LINK` records) that
you would otherwise have to build by hand before refinement, sequence design,
synthesis, or visualization. The approach follows Seeman's structural-DNA-
nanotechnology tradition of building immobile junctions as programmable vertices.

Three exchange kinds are supported:

- **`double` (`d`)** — exchange both local backbone continuities between two
  residues.
- **`single` (`s`)** — exchange one strand-continuity relationship, leaving the
  complementary one unchanged.
- **`bowtie` (`b`)** — create paired 3'-3' and 5'-5' junction behavior, including
  `LINK` records and phosphate-only linker residues (by default written as
  `HETATM X33`; optionally a custom name or regular `ATOM DA`).

**Alignment** estimates each helix's axis from `P` atoms (or a user-supplied
axis line) and moves the movable helix to a target inter-axis geometry described
by four intuitive quantities: `tau` (axial spin of the moving helix), `phi`
(orbital azimuth around the fixed helix), `beta` (interhelical tilt/bend), and
`d` (axial slide), with a target `--axis_dist`.

### 6.2 Usage

**Launch the GUI:** `python3 re_helix.py`. The GUI exposes pair rows (or a
combined `CLI pair args` field), the alignment options, and an `Other tools`
area that opens the bundled helpers with the current input pre-filled. The main
run log mirrors stdout/stderr from helpers launched through it.

**Alignment + reciprocal exchange (CLI):**

```bash
python3 re_helix.py input.pdb '(AB)' '(CD)' 30A 8D d 13B 24C s -o model
# writes model_aligned.pdb and model_aligned_rex.pdb
```

**Reciprocal exchange only (no alignment):**

```bash
python3 re_helix.py input.pdb 9C 23A d 23C 23F b --re_only -o model
# writes model_rex.pdb
```

**Exchange syntax.** Residue tokens may be written `30A`, `A30`, `A.30`, or
`30.A`. Each exchange is `<pos1> <pos2> <kind>`, where kind is `d/double`,
`s/single`, or `b/bowtie`. In alignment mode with `--axis_parallel n`, a
single-site inter-helix pair can carry a fixed tilt: `<pos1> <pos2> <beta_deg>
<kind>` (`rho_deg` is accepted as a legacy alias for `beta_deg`):

```bash
python3 re_helix.py input.pdb '(AB)' '(CD)' 26A 9C 90 d --axis_parallel n -o angled_model
```

**Key options:** `-o/--output` (output base), `--re_only` (RE without
alignment), `--axis_dist` (target inter-axis distance, Å), `--axis_parallel y|n`,
`--axis_range`/`--axis_move` (residue windows or whole chains for axis fitting /
moving), `--user_axis_dir`/`--user_axis_point` (define the alignment axis
directly), `--fix` (hold a helix fixed), `--replicate`, `--cir_shift` (residue
shift for circular RE strands), `--linker_phosphate_resname`/`_record` (control
bowtie linker residues).

### 6.3 Bundled tools (`re_helix_lib/`)

- **Bend Helix** (`bend_helix.py`). Bends a straight two-chain helix at a chosen
  P residue: piece #1 stays fixed while piece #2 is moved by a `beta` bend, a
  `phi` hinge direction, and an optional `tau` twist. Options include
  `--axis_range` (local axis for already-bent inputs), `--sep y` (new chain IDs
  for the moved piece), and `--origin y` (origin-overlay comparison PDB).
- **Do Symmetry** (`do_symmetry.py`). Averages a pseudosymmetric homomeric
  assembly into an idealized symmetric model. It builds cyclic chain
  permutations, reorders each symmetry copy, rigidly aligns copies with a
  pure-Python quaternion/Kabsch least-squares fit, and averages matching atoms.
  Use `--groups` for custom chain organization or `--fold N --chains A-X` for
  continuous evenly-divisible chains; `--fit-atoms`, `--keep-intermediate`,
  `--no-align`, `--ignore-resname`, and `--allow-missing` tune the fit.
- **Add PDB LINK Record** (`add_pdb_link_record.py`). Stages P/O3' `LINK` records
  (terminal circularization automatically; internal/inter-chain links manually)
  and rebuilds chain topology, IDs, `TER` records, residue numbering, and `LINK`
  records in one pass, preserving and remapping existing links.
- **Insert Virtual Resi** (`insert_virtual_resi.py`). Inserts residue-numbering
  gaps after selected residues (no new atoms), updating coordinate records, `TER`
  records, and both endpoints of fixed-column `LINK` records.
- **Generate Lattice** (`generate_lattice.py`). Writes/replaces the P1 `CRYST1`
  record from three lattice directions and distances, and by default rotates
  coordinates/`ANISOU` into the standard crystallographic Cartesian frame.
- **Get Phenix Restraints** (`get_phenix_restraints.py`). Converts `LINK` records
  into a `*_links.params` file of Phenix bond and phosphate-angle restraints,
  emits `*_junctions.params` from `REMARK 950 RE_SCRIPT JUNCTION` lines, and,
  for true standalone 3'-to-3' linker phosphates, writes matching CIF/safe-params
  support files. Use exactly one movement-selection params file when minimizing.

**Representative CLI usage:**

```bash
python3 re_helix_lib/bend_helix.py --input straight_helix.pdb --pivot A36 --beta 30
python3 re_helix_lib/do_symmetry.py model.pdb --fold 3 --chains A-X -o model_C3
python3 re_helix_lib/add_pdb_link_record.py input.pdb --chains A B -o input_linked.pdb
python3 re_helix_lib/insert_virtual_resi.py input.pdb --insert A55 3 -o input_vresi.pdb
python3 re_helix_lib/generate_lattice.py input.pdb --u1 1 0 0 --d1 80 --u2 0 1 0 --d2 80 --u3 0 0 1 --d3 80 -o input_cryst.pdb
python3 re_helix_lib/get_phenix_restraints.py model_rex.pdb --output-base model_rex
```

*(See `re_helix/README.md` for the full option reference and the Seeman
background reading.)*

---

## 7. Tool 3 — Curve It: sculpt structures along a 3D curve

> Folder `../curve_it/` · entry `curve_it.py` · version **V3_4** ·
> *"AZBMOST Package Module #3 — Curve It: Sculpt PDB Structures Along Any 3D Curve"*

### 7.1 Principle

Curve It takes a roughly **straight** PDB structure (a DNA/RNA helix, a protein
alpha-helix/coiled-coil, or any elongated filament) and bends it so its principal
axis follows a user-supplied **3D curve**. It works by transporting a
**rotation-minimizing frame** along the target curve and mapping the structure's
axial positions onto that curve, then placing each local group into the moving
frame as a rigid body. Because groups move rigidly, local stereochemistry is
preserved:

- **nucleic acids** are grouped as phosphate, sugar, and base units;
- **proteins / unknown residues** are grouped as whole residues.

The rotation-minimizing frame avoids the spurious extra twist that a naive
Frenet frame would introduce, so the helix follows the path smoothly. Optional
controls add deliberate helix **phase** rotation and extra **twist**, choose how
the structure is **scaled** onto the curve, and allow **interpolation** of the
curve before fitting.

Curve It supports **open** and **closed** curves. With `--scale-mode none` it
preserves native axial spacing (open curves must be at least as long as the
structure; closed curves may wrap periodically); with `--scale-mode
helix_to_curve` it distributes the unscaled structure over the whole curve; or
you can give a numeric target length in Å.

### 7.2 Usage

**Show version / launch GUI:**

```bash
python3 curve_it.py --version
python3 curve_it.py            # or: python3 curve_it.py --gui
```

**Bend a structure onto a curve (CLI):**

```bash
python3 curve_it.py input.pdb                                   # default planar ring
python3 curve_it.py input.pdb curve.xyz -o output_curved.pdb
python3 curve_it.py input.pdb curve.xyz --path-type closed -o out.pdb
python3 curve_it.py input.pdb curve.xyz --scale-mode none -o out.pdb
python3 curve_it.py input.pdb curve.xyz --scale-mode 340.0 --path-type closed
python3 curve_it.py input.pdb curve.xyz --helix_phase 90 --twist 360
python3 curve_it.py input.pdb curve.xyz --interp-mode n --interp-n 400
```

**Curve file format.** Plain whitespace `x y z` lines, or XYZ-like files with a
count/comment header and element labels. Multiple components separated by blank
lines are labeled `A`, `B`, `C`, … and concatenated in file order by default;
choose a subset with `--curve-components A` / `B,C` / `A-C` (CLI) or **Select
components…** (GUI).

**Interpolation** changes the curve actually used for the run (fitting, length,
curvature/writhe, viewer, and the optional `<curve>_interpolated` helper file).
`--interp-mode n` gives exactly `--interp-n` arc-length-even points;
`--interp-mode p` inserts `--interp-p` points between each original pair.

**Outputs.** The curved model goes to `-o/--output-pdb` or `<input>_curved.pdb`;
a rescaled input curve is saved as `<curve>_rescaled.xyz`; a GUI-interpolated
curve is saved as `<curve>_interpolated.xyz`.

**Protein note.** Protein PDBs work when the structure has a meaningful straight
principal axis (helix, coiled coil, elongated filament); residues move as whole
rigid units. This is not a folding tool, and compact globular proteins have no
useful single axis.

### 7.3 Bundled tools (`curve_it_lib/` and the GUI **Tools** area)

- **Convert XYZ…** — converts between coordinate XYZ/txt, molecular XYZ, and
  "fake-PDB" (each point becomes one `ALA`/`CA` atom; blank-line components
  become chains; closed chains can get `LINK` records), with an optional output
  scale factor.
- **Generate helical curve…** (`generate_helix_xyzV2.py`) — writes a circular
  helix curve `x=R cos(t+φ)`, `y=±R sin(t+φ)`, `z=z0+c·t`, one point per line;
  can derive `c` from `R` and pitch angle, or vice versa.
- **Local curvature/torsion…** (`cal_xyz_local_curvature_torsionV3_1.py`) —
  writes a CSV of normalized path position, coordinates, local curvature,
  regularized torsion, local writhe density, and diagnostics; includes a built-in
  `(2,3)` torus-knot (trefoil) example.
- **Curved Connector…** (`curved_connectorV3_4.py`) — screens curved nucleic-acid
  connectors between two target helical end base-pairs using a straight duplex
  template. It builds a clamped Euler-elastica proxy centerline per candidate
  length, ranks by destination-end fit, and writes ranked assemblies plus
  `connector_summary.tsv`. V3_4 adds an optional sampled local-curvature cap
  (`--max-local-curvature`, i.e. a minimum bend radius `1/kappa_max`) with capped
  optimizer controls. Note `twist_mismatch_deg` is an endpoint base-pair
  orientation mismatch, not integrated torsion or twist energy.
- **Plane It…** (`plane_it.py` launcher → `plane_itV3_8.py`) — projects selected
  atoms/points from PDB/XYZ/text into 2D SVG via PCA or current XY, with optional
  connecting lines, base-pair lines (via DSSR), a projection-basis xy-plane, a
  projected-length scale bar, and depth ordering.

**Representative CLI usage:**

```bash
python3 curve_it_lib/generate_helix_xyzV2.py -R 10 -c 2 -L 200 -n 1000 -o helix.xyz
python3 curve_it_lib/cal_xyz_local_curvature_torsionV3_1.py --example-trefoil --no-plot
python3 curve_it_lib/curved_connectorV3_4.py target.pdb template.pdb --source-bp A33,B1 --dest-bp E1,F33 --top-k 5
python3 plane_it.py input.pdb --atom-type P --draw-lines --draw-base-pairs
```

*(See `curve_it/README.md` for the full Plane It option set and helper-module
list.)*

---

## 8. A worked cross-tool example

Building a small closed DNA ring illustrates how the tools compose.

1. **Build blocks (BNP-NA).** Generate the straight B-DNA duplexes you need with
   `Generate`, each aligned to +Z and placed. Add terminal phosphates with the
   *Add phosphates* helper if a downstream ligation needs them.
2. **Wire the topology (Re-Helix).** Align neighboring duplexes to the target
   inter-axis geometry and apply `double`/`bowtie` reciprocal exchanges to create
   the crossovers or the closing junction. Use *Add PDB LINK Record* to
   circularize and rebuild topology, then *Get Phenix Restraints* to emit the
   restraint files for minimization.
3. **Curve it (Curve It).** Generate a ring or super-helix path with *Generate
   helical curve…* (or supply your own XYZ), then bend the wired assembly onto it
   with `--path-type closed`. Verify the geometry with *Local curvature/torsion…*
   and visualize a projection with *Plane It*.

Each stage writes standard PDB files with provenance `REMARK`s, so the output of
one tool is directly the input of the next, and the embedded logs record the
exact commands for reproducibility.

---

## 9. Troubleshooting quick reference

| Symptom | Likely cause / fix |
| --- | --- |
| `x3dna-dssr: NOT FOUND` (BNP-NA) | Install DSSR; put `x3dna-dssr` on `PATH` or at `/usr/local/bin/x3dna-dssr`. |
| DSSR rebuild failed | Wrong alphabet for the type (DNA uses `T`, RNA uses `U`); inspect the `.txt` table in `tmp_file/`. |
| Invalid Z-DNA length | Must be positive and even (`10`, `20`, `42` work; `0`, `15`, `abc` fail). |
| Phenix minimization failed | Phenix not installed/params missing; add to `PATH` or set `PHENIX_ENV`. |
| B-Z builder order/phase error | Inputs must alternate `B Z B Z…` starting with B; Z chains start pyrimidine, end purine (enable auto-trim or make Z 2 bp long). |
| Triplex range/partner error | `antiparallel` needs an all-`G` strand-I range; `parallel` needs all-`A`; use *Refresh strand info* to preview. |
| GUI won't start | Tkinter missing for GUI mode — CLI/`--version` still work; install your platform's Tk package. |
| Re-Helix exchange does nothing expected | Check residue-token order and kind (`d/s/b`); confirm chains with the pair preview or `--axis_range`/`--axis_move`. |
| Curve It: curve too short (open path) | With `--scale-mode none`, the open curve must be ≥ the structure's axis length; lengthen the curve, use a numeric target, or `helix_to_curve`. |
| Plane It base-pair lines missing | DSSR not available; install `x3dna-dssr` or place a DSSR `.out` at the default `tmp_file/` path. |

---

*This manual is a combined reference. For version-by-version detail, exhaustive
option tables, and packaging/PyInstaller instructions, see each tool's own
`README.md` and `CHANGELOG.md`. AZBMOST is released under the MIT License.*
