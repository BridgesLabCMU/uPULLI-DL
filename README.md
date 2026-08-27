# biofilm-embeddings

[![CI](https://github.com/BridgesLabCMU/uPULLI-DL/actions/workflows/ci.yml/badge.svg)](https://github.com/BridgesLabCMU/uPULLI-DL/actions/workflows/ci.yml)

**Deep-learning embeddings for biofilm timelapse microscopy of 96-well plates.**

biofilm-embeddings turns per-well image stacks from a Cytation5 microscope into **DINOv2 vision-transformer embeddings** — a numerical fingerprint of what each well looks like at every timepoint. Instead of hand-picking features like "biomass" or "texture," a frozen pretrained model describes each frame with 768 numbers, giving you a trajectory through embedding space for every well. Those trajectories feed downstream analysis: fPCA, UMAP, clustering, path signatures.

It runs as a desktop GUI, or headlessly from the command line for big batches on a GPU machine.

> **New here? Skip straight to [Quick start](#quick-start).** Installation takes ~15 minutes. You'll need `git`, Miniconda, and realistically a GPU — no GitHub account or credentials required.

---

## Table of contents

- [How it works](#how-it-works)
- [Quick start](#quick-start)
  - [1. Install Miniconda (one-time)](#1-install-miniconda-one-time)
  - [2. Download biofilm-embeddings](#2-download-biofilm-embeddings)
  - [3. Install it](#3-install-it)
  - [4. Check your GPU](#4-check-your-gpu)
  - [5. Make a desktop shortcut](#5-make-a-desktop-shortcut-optional)
- [Using the GUI](#using-the-gui)
- [What gets produced](#what-gets-produced)
- [Keeping embeddings comparable](#keeping-embeddings-comparable)
- [Running without the GUI](#running-without-the-gui)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [Advanced](#advanced)
- [Authors & license](#authors--license)

---

## How it works

There are two phases, and they're deliberately separate buttons.

**Phase 1 — image processing.** Raw Cytation TIFFs become registered, contrast-normalized, segmented `_processed.tif` stacks. This is the slow, expensive part.

**Phase 2 — embedding extraction.** A frozen DINOv2 model reads every processed stack and writes one cache file of embeddings.

They're separate so you can re-extract with a different model or image size **without reprocessing your images**. Phase 1 output is the durable artifact; phase 2 is cheap to redo.

If your images have *already* been processed by [biofilm-processing](https://github.com/BridgesLabCMU/uPULLI-I), you can skip phase 1 entirely and just run phase 2 over the existing output — see [Running without the GUI](#running-without-the-gui).

> **A note on the processing engine.** biofilm-embeddings does not contain its own copy of the image-processing code. It uses biofilm-processing itself, frozen at a specific version (v1.0.0, the paper-locked release), included automatically as part of the download. This matters scientifically: a vision transformer is *very* sensitive to how images are rendered, so if the processing changed underneath you, embeddings from different batches would stop being comparable in ways that look like biology but aren't.

---

## Quick start

### 1. Install Miniconda (one-time)

Miniconda gives you an isolated Python environment so this package's dependencies don't conflict with anything else on your computer. **If you already have Anaconda or Miniconda, skip to step 2.**

- **Windows / macOS / Linux:** download and run the installer from <https://www.anaconda.com/download/success> (pick "Miniconda" — it's smaller than Anaconda and works the same way).
- Accept all defaults.
- After install, open the **"Anaconda Prompt"** (Windows) or your normal **Terminal** (macOS / Linux). All commands below get typed there.

### 2. Download biofilm-embeddings

**This step needs Git — a "Download ZIP" will not work.** The processing engine is not copied into this repository; it is referenced as a Git submodule, and a ZIP leaves that reference empty, so the install fails partway through with `external/biofilm-processing does not appear to be a Python project`. Cloning with `--recurse-submodules` fetches both parts together:

```bash
git clone --recurse-submodules https://github.com/BridgesLabCMU/uPULLI-DL.git
cd uPULLI-DL
```

No GitHub account, SSH key, or login is needed.

Don't have Git? Install it from <https://git-scm.com/downloads> (Windows/macOS), or `sudo apt install git` on Ubuntu/Debian.

> Already cloned without `--recurse-submodules`? Run `git submodule update --init --recursive` from inside the folder.

### 3. Install it

```bash
conda create -n biofilm-embeddings python=3.11 -y
conda activate biofilm-embeddings
bash scripts/setup.sh
```

What these do:
- `conda create …` — makes a new Python environment named `biofilm-embeddings`.
- `conda activate biofilm-embeddings` — switches into it. **You'll need to do this every time you open a fresh terminal**, unless you use the desktop shortcut (step 5).
- `bash scripts/setup.sh` — fetches the processing engine and installs everything in the right order. This downloads PyTorch and several GB of CUDA libraries, so expect it to take a while.

The order matters, which is the whole reason `setup.sh` exists: the processing engine isn't on PyPI, so it has to be installed *before* this package. If you install by hand and get a "No matching distribution found" error, that's why.

Once it finishes, launch the app:

```bash
biofilm-embeddings-gui
```

### 4. Check your GPU

Phase 2 runs a vision transformer over every frame of every well. On a GPU that's minutes to hours; on a CPU it's hours to days. It's worth confirming your GPU actually works **before** starting a real run:

```bash
python -c "import torch; x=torch.randn(8,8,device='cuda'); print('GPU OK:', float((x@x).sum()))"
```

If that prints `GPU OK: …`, you're set.

If it fails with **`no kernel image is available for execution on the device`**, your graphics card is older than the PyTorch build that got installed. This is a common and confusing one, because `torch.cuda.is_available()` still says `True` and the card still shows up by name — it only breaks at the first real computation. Fix for Pascal-generation cards (Quadro P6000, GTX 10-series, Titan Xp):

```bash
pip install "torch==2.13.0+cu126" \
  --index-url https://download.pytorch.org/whl/cu126 \
  --extra-index-url https://pypi.org/simple
```

Then re-run the check above. See [Troubleshooting](#troubleshooting) for the details and for other card generations.

### 5. Make a desktop shortcut (optional)

If you'd rather not open a terminal each time:

```bash
python scripts/installDesktopShortcut.py
```

This detects your conda environment and creates a clickable icon:

| Platform | What it makes |
|---|---|
| Linux   | `.desktop` file on Desktop + entry in the app menu |
| macOS   | `biofilm-embeddings.app` bundle on Desktop |
| Windows | `.bat` launcher + `.lnk` shortcut on Desktop |

On macOS and Windows, JPG isn't a valid icon format, so convert the icon first and re-run the installer:

- macOS: `sips -s format icns assets/dora5.jpg --out assets/dora5.icns`
- Windows: `magick convert assets/dora5.jpg -define icon:auto-resize=256,128,64,48,32,16 assets/dora5.ico`

---

## Using the GUI

Six tabs, worked through roughly left to right.

| Tab | What you do |
|---|---|
| **Setup** | Point at a folder of plates, pick plates and magnifications, choose where output goes |
| **Parameters** | Preprocessing settings, plus which DINOv2 model and settings to embed with |
| **Preview** | Live preview of raw / normalized / mask images at your current settings |
| **Conditions** | Label the well grid with experimental conditions |
| **Test Well** | Run both phases on one well as a sanity check |
| **Run** | **Start** runs phase 1; **Extract DINOv2 embeddings** runs phase 2 |

### Setup tab

1. Click **Browse** and pick the root directory containing your plate folders. Plates are auto-discovered.
2. Tick the plates to include.
3. **Magnifications** are auto-detected from each plate's Cytation metadata. Tick the one you want.
4. Set the output directory.

> **Pick one magnification.** Different objectives image at different physical scales, and embeddings from different objectives are not comparable — they can't share a cache. If a plate folder holds both 4x and 10x, run them separately.

### Parameters tab

Preprocessing settings (block diameter, threshold, dust correction) behave exactly as in biofilm-processing. The section that's specific to this app is **DINOv2**:

| Setting | Default | What it does |
|---|---|---|
| Model | `facebook/dinov2-base` | Which pretrained model. `-small` is faster, `-giant` is slower and ~4 GB to download. |
| Image size | 518 | Each frame is resized to this square before the model sees it. Lower it to 364 if you run out of GPU memory. |
| Patch grid size | 3 | Patch tokens are pooled to a 3×3 grid, giving coarse spatial detail alongside the whole-image summary. |
| Wells per batch | 4 | How many wells go to the GPU at once. Lower this first if you hit out-of-memory errors. |
| Loader workers | 3 | CPU processes reading TIFFs in the background. |

**NAS mirror** (optional) changes how a run is staged. With it on, each plate is processed, embedded, copied to your network drive, and deleted locally before moving to the next plate — so you never need disk space for the whole experiment at once. Leave it off for ordinary local runs.

### Run tab

**Start** runs phase 1 across every plate. **Extract DINOv2 embeddings** runs phase 2 over everything that's been processed. Tick **Extract embeddings when done** to chain phase 2 automatically after phase 1 finishes.

Both phases are **resumable** — if a run is stopped or crashes, starting it again picks up where it left off rather than redoing finished work.

---

## What gets produced

Phase 1 writes per-well files under each plate, the same layout biofilm-processing uses:

```
<output>/<plate>/processedImages/
    index.csv                  which wells exist, and where their files are
    A1_processed.tif           contrast-normalized stack (this is what gets embedded)
    A1_registered_raw.tif      drift-corrected raw stack
    A1_masks.npz               binary segmentation masks
    A1_overlay.mp4             mask overlay video
```

Phase 2 writes one cache for the whole run:

```
<output>/embeddings/
    cls_cache.pt               the embeddings
    index.csv                  which well is which row
    excluded_short_wells.csv   wells skipped for having too few frames (if any)
```

To load the embeddings in Python:

```python
from biofilm_embeddings.embeddings.extractor import loadCache, indexToFrame

cache = loadCache('embeddings/cls_cache.pt')

cache['cls']        # (wells, frames, 768) — whole-image embedding per frame
cache['patches']    # (wells, frames, 9, 768) — 3x3 spatial grid per frame
cache['wells']      # well IDs, e.g. 'A1_03'
cache['plates']     # plate for each well
cache['model']      # which model made this

index = indexToFrame(cache['index'])   # DataFrame: magnification, objective, paths
```

Row *i* of `cls` corresponds to `wells[i]` and `plates[i]`.

> **On loading caches safely.** A `.pt` file is executable content, not inert data — `torch.load`'s default pickle protocol runs code on unpickling. Since caches get read from shared network storage and passed between groups, `loadCache` loads them with `weights_only=True`, which permits only tensors and primitives. That is also why `cache['index']` is stored as plain columns rather than a pickled DataFrame; `indexToFrame` rebuilds it. Caches written before this change fail with an explanatory error — re-extract them, or pass `allowUnsafe=True` if you trust every machine that could have written the file.

---

## Keeping embeddings comparable

This is the part worth reading before a real run. Embeddings are only comparable to each other if they were made the same way.

**Use the same number of frames.** Every well in one cache is embedded over the same number of timepoints. Wells with *more* frames get truncated; wells with **fewer are skipped entirely** and listed in `excluded_short_wells.csv`. Check that file after a run — if a whole plate is missing, this is usually why.

**Use one magnification per cache.** 4x and 10x images are different physical scales. Never mix them.

**Use the same model settings.** Model, image size, and patch grid size all have to match across any datasets you plan to compare.

**Different experiments usually aren't comparable.** Species, magnification, and timecourse length all differ between datasets — a 4x 25-frame *Klebsiella* set and a 10x 31-frame *V. cholerae* set are separate embedding spaces, not one.

---

## Running without the GUI

For big batches on a GPU machine, or for images already processed by biofilm-processing, use the headless command. It skips image processing and just embeds what's already on disk:

```bash
conda activate biofilm-embeddings

# Always look first — reports wells, plates, magnification, frame count. No GPU used.
biofilm-embeddings-run /path/to/output --dry-run

# Small test before committing to hours of compute
biofilm-embeddings-run /path/to/output --limit 8

# The real run
biofilm-embeddings-run /path/to/output --well-batch 24
```

Useful options:

| Option | Why |
|---|---|
| `--dry-run` | Report what would be embedded and stop. Always do this first. |
| `--n-frames 31` | Pin the frame count instead of guessing from the first stack. Recommended for anything that matters. |
| `--mag _03` | Embed only one magnification, when a folder holds several. |
| `--cache-dir /local/scratch` | Write results somewhere other than the source folder (e.g. when the source is read-only). |
| `--limit 8` | Embed only the first N wells, as a smoke test. |
| `--well-batch 24` | More wells per GPU batch. Raise it on a big GPU, lower it if you run out of memory. |

### Per-dataset scripts

`scripts/examples/` holds two templates. Copy the one that matches your data and fill in the header block:

| Template | Use when |
|---|---|
| `extract_dataset_template.sh` | One magnification — the common case. Writes a single cache at `<root>/embeddings/`. |
| `extract_multi_mag_template.sh` | The plates were imaged at two or more objectives. Runs one pass per magnification into separate caches, because mixing scales in one cache is invalid. |

Both take the data root as their first argument, pin the frame count in the script, detach with `nohup`, and pass any extra flags through to `biofilm-embeddings-run`.

Keeping one script per dataset is the point: the script *is* the reproducible record. It pins the frame count and any non-default model settings, so re-running it a year later reproduces the same cache rather than whatever the defaults have drifted to. Record the dataset's shape — organism, plate and well counts, magnification, frame count — in the header block while you still remember it.

---

## Updating

```bash
conda activate biofilm-embeddings
cd /path/to/uPULLI-DL
git pull
git submodule sync --recursive            # picks up any change to the engine's location
git submodule update --init --recursive   # moves the engine to the pinned version
bash scripts/setup.sh                     # picks up any new dependencies
```

The submodule steps matter: the processing engine is pinned to an exact version, and `git pull` alone won't move it. Run `sync` before `update` — it re-reads where the engine lives from `.gitmodules`, which an existing clone otherwise ignores.

---

## Troubleshooting

**`biofilm-embeddings-gui: command not found`** — you forgot to activate the environment. Run `conda activate biofilm-embeddings` first.

**`could not read Username for 'https://github.com'`** — your copy of the repository recorded a different submodule location than the one it now specifies, and is asking for credentials it doesn't need. A clone keeps whichever URL it was created with, so refresh it:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

**`Server does not allow request for unadvertised object <sha>`** — your copy records a version of the processing engine that the engine repository no longer publishes. `git pull` to pick up the current pinned version, then `git submodule sync --recursive && git submodule update --init --recursive`.

**`external/biofilm-processing does not appear to be a Python project`** — the processing engine folder is empty, usually because the repo was downloaded as a ZIP or cloned without `--recurse-submodules`. Fix with `git submodule update --init --recursive`, then re-run `bash scripts/setup.sh`.

**`No matching distribution found for biofilm-processing==1.0.0`** — the engine wasn't installed before this package. Run `bash scripts/setup.sh`, which does it in the right order. If you just changed which engine version is pinned, you also need to `git add external/biofilm-processing` so the new version is the one that gets installed.

**`CUDA error: no kernel image is available for execution on the device`** — your GPU is older than the PyTorch build that got installed. Current PyTorch defaults to a CUDA 13 build supporting sm_75 and newer (Turing onward); CUDA 13 dropped support for Pascal and older. The confusing part is that `torch.cuda.is_available()` returns `True` and the card reports its name correctly — it only fails at the first real computation. Check what your install supports with:

```bash
python -c "import torch; print(torch.cuda.get_arch_list()); print(torch.cuda.get_device_name(0))"
```

For Pascal cards (Quadro P6000, GTX 10-series, Titan Xp — compute capability 6.1), install the CUDA 12.6 build:

```bash
pip install "torch==2.13.0+cu126" \
  --index-url https://download.pytorch.org/whl/cu126 \
  --extra-index-url https://pypi.org/simple
```

Specify the exact `+cu126` version. Plain `torch==2.13.0` looks "already satisfied" to pip and it will do nothing.

**Out of GPU memory** — lower **Wells per batch** in the Parameters tab (try 2, or 1), or `--well-batch` on the command line. Then try image size 364 instead of 518, or switch to `facebook/dinov2-small`.

**Extraction says it skipped every well** — the frame count it inferred is larger than the frames your stacks actually have. Run with `--dry-run` to see the counts, then pin the right one with `--n-frames`.

**A whole plate is missing from the results** — check `embeddings/excluded_short_wells.csv`. A plate acquired with one fewer timepoint than the rest gets skipped wholesale to keep frames aligned.

**The first run stalls for a long time with no output** — it's downloading model weights from HuggingFace (~350 MB for `dinov2-base`, ~4 GB for `dinov2-giant`). This happens once; afterwards they're cached. It needs internet access the first time.

**No GPU at all** — everything still works, just slowly. Phase 2 falls back to the CPU, where a few hundred wells takes hours to days. Fine for a smoke test, not for real runs.

---

## Advanced

### Where the embeddings come from

Each frame is resized to 518×518, converted to 3-channel grayscale, normalized with ImageNet statistics, and passed through a frozen DINOv2 ViT. Two things are kept per frame: the **CLS token** (768 numbers summarizing the whole image) and the **patch tokens**, average-pooled to a 3×3 grid (9 × 768) to retain coarse spatial structure. Nothing is fine-tuned — the model is used purely as a fixed feature extractor, so results are deterministic given the same input and settings.

### Per-plate pipelined mode

Turning on **NAS mirror** switches the Run tab to a different flow: each plate is processed, embedded in a separate process, copied to the network drive, and deleted locally before the next plate starts. Per-plate caches are stitched into one master cache at the end, with exactly the same format as a single-pass run. This is what makes large experiments possible on a machine that can't hold the whole dataset at once.

### Project structure

```
src/biofilm_embeddings/
    gui/                  PySide6 GUI (app.py is the entry point)
      tabs/               one module per tab; run.py holds both phase workers
    embeddings/
      dataset.py          reads _processed.tif, normalizes for the model
      extractor.py        the GPU pass, resumable checkpoints, cache writing
      extract_run.py      the biofilm-embeddings-run command
      extract_one_plate.py  single-plate extraction used by NAS mirror mode
external/biofilm-processing   the pinned processing engine (a git submodule)
scripts/                  installer, desktop shortcut, per-dataset run scripts
```

Developer-facing notes on invariants and internals live in `CLAUDE.md`; open photometric questions are in `ISSUES.md`.

---

## Authors & license

**Author:** Seh Na Mellick
CMU Ray and Stephanie Lane Computational Biology Department · CMU Department of Biological Sciences

Built on [biofilm-processing](https://github.com/BridgesLabCMU/uPULLI-I) (Seh Na Mellick, Jojo Prentice, Andrew Bridges) and Meta AI's [DINOv2](https://github.com/facebookresearch/dinov2).

**License:** MIT. Copyright (c) 2026 Carnegie Mellon University — full text in [`LICENSE`](LICENSE).
