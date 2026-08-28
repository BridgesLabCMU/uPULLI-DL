#!/usr/bin/env python3
"""One-shot setup for biofilm-embeddings. Works on Windows, macOS and Linux.

Run it from an activated environment:

    conda create -n biofilm-embeddings python=3.11 -y
    conda activate biofilm-embeddings
    python scripts/setup.py

Why this is Python and not a shell script: on Windows the documented terminal is the
Anaconda Prompt (cmd.exe), which has no `bash`, while Git Bash has `bash` but usually no
initialized `conda`. Neither shell alone can run the old setup.sh flow. Every machine that
can install this package already has the interpreter, so the interpreter is the one shell
that is always available. scripts/setup.sh now delegates here so there is a single
implementation to keep correct.

The order below is the whole point of the script: the processing engine is not on PyPI and
pyproject.toml pins it with `==`, so it must be fetched (git submodule) and installed
BEFORE this package, or `pip install -e .` cannot resolve the pin.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / 'external' / 'biofilm-processing'
IS_WINDOWS = os.name == 'nt'


def step(msg):
    print(f'\n==> {msg}', flush=True)


def run(args, **kw):
    """Run a command, echoing it. Raises SystemExit with context on failure."""
    print('    $ ' + ' '.join(str(a) for a in args), flush=True)
    result = subprocess.run(args, cwd=kw.pop('cwd', REPO), **kw)
    if result.returncode != 0:
        raise SystemExit(
            f'\nERROR: command failed (exit {result.returncode}):\n'
            f'  {" ".join(str(a) for a in args)}\n'
        )
    return result


def pip(*args):
    # sys.executable, not a bare `pip`: guarantees the install lands in the environment
    # this script is running under, even when PATH points at a different pip.
    run([sys.executable, '-m', 'pip', *args])


def ensureMahotasOnWindows():
    """Pre-install mahotas from conda-forge on Windows.

    The engine depends on mahotas, a C extension with no Windows wheel for the pinned
    range, so pip tries to compile it and fails unless Visual Studio Build Tools are
    present. conda-forge ships a built package, so installing it first turns the most
    common Windows install failure into a no-op. Only runs on Windows, only when mahotas
    is missing, and only when conda is actually available.
    """
    if not IS_WINDOWS:
        return
    try:
        import mahotas  # noqa: F401
        return
    except ImportError:
        pass

    conda = shutil.which('conda')
    if conda is None:
        print(
            '    NOTE: mahotas is not installed and conda was not found on PATH.\n'
            '    If the engine install below fails while building mahotas, either run\n'
            '      conda install -c conda-forge mahotas -y\n'
            '    or install the Visual Studio Build Tools ("Desktop development with C++")\n'
            '    from https://visualstudio.microsoft.com/visual-cpp-build-tools/',
            flush=True,
        )
        return

    step('Windows: installing mahotas from conda-forge (it has no wheel and needs a compiler)')
    try:
        run([conda, 'install', '-c', 'conda-forge', 'mahotas', '-y'])
    except SystemExit:
        print(
            '    WARNING: conda could not install mahotas. Continuing anyway — if the\n'
            '    engine install fails below, install the Visual Studio Build Tools.',
            flush=True,
        )


def main():
    if shutil.which('git') is None:
        raise SystemExit(
            'ERROR: git was not found on PATH.\n'
            '  The processing engine is a git submodule, so git is required.\n'
            '  Install it from https://git-scm.com/downloads and reopen your terminal.'
        )

    step('Fetching the pinned processing submodule (external/biofilm-processing)')
    # sync first so a clone made when the engine lived elsewhere picks up the current URL
    run(['git', 'submodule', 'sync', '--recursive'])
    run(['git', 'submodule', 'update', '--init', '--recursive'])

    if not (ENGINE / 'pyproject.toml').is_file():
        raise SystemExit(
            f'ERROR: {ENGINE} is still empty after the submodule update.\n'
            '  A "Download ZIP" of this repository does not include the engine — you need\n'
            '  a git clone. From an existing clone, try:\n'
            '    git submodule update --init --recursive'
        )

    ensureMahotasOnWindows()

    step('Installing the processing engine first (editable)')
    pip('install', '-e', str(ENGINE))

    step('Installing biofilm-embeddings (editable)')
    pip('install', '-e', str(REPO))

    step('Done. Launch the GUI with:  biofilm-embeddings-gui')
    print('    (or run headlessly:      biofilm-embeddings-run <output_root> --dry-run)')


if __name__ == '__main__':
    main()
