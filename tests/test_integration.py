"""Smoke tests for the single-source integration with biofilm-processing.

biofilm-embeddings imports biofilm-processing's `multiWellAnalysis.processing`
(it no longer ships its own copy). These tests catch the two ways that contract
can break — loudly, on the first run / in CI, instead of silently corrupting
embeddings. See INTEGRATION_PLAN.md.
"""
import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SUBMODULE_ROOT = REPO_ROOT / 'external' / 'biofilm-processing'


def _pinnedVersion():
    """The `biofilm-processing==X` pin from pyproject.toml."""
    text = (REPO_ROOT / 'pyproject.toml').read_text()
    m = re.search(r'"biofilm-processing==([^"]+)"', text)
    assert m, 'no `biofilm-processing==` pin found in pyproject.toml'
    return m.group(1)


def test_processing_is_biofilm_not_a_local_fork():
    """`multiWellAnalysis.processing` must resolve to the pinned submodule.

    Checking only for the substring 'biofilm-processing' is NOT enough: a sibling
    clone at ~/biofilm-processing satisfies it while completely bypassing the pin,
    which is exactly how a v1.0.0 working tree once got loaded under a v0.5.0 pin.
    Anchor on the submodule's real path instead.
    """
    import multiWellAnalysis.processing.analysis_main as am
    resolved = Path(am.__file__).resolve()
    assert 'biofilm_embeddings' not in resolved.as_posix(), (
        f'processing resolved to {resolved} — a local fork crept back into '
        'the biofilm_embeddings package; it must import biofilm-processing, not copy it.'
    )
    assert resolved.is_relative_to(SUBMODULE_ROOT), (
        f'processing resolved to {resolved}, which is NOT under the pinned submodule '
        f'at {SUBMODULE_ROOT}. Some other biofilm-processing checkout (e.g. a sibling '
        f'clone at ~/biofilm-processing) is installed, so the version pin is not in '
        f'effect and the render is unverified. Re-run: '
        f'pip install -e external/biofilm-processing'
    )


def test_installed_processing_version_matches_pin():
    """The installed engine's version must equal the `==` pin.

    Complements the path check: catches a non-editable install of the wrong
    version, where the module path alone can't prove provenance.
    """
    from importlib.metadata import version
    pinned = _pinnedVersion()
    installed = version('biofilm-processing')
    assert installed == pinned, (
        f'biofilm-processing {installed} is installed but pyproject pins =={pinned}. '
        'The frozen render is not what the embeddings assume. Advance the submodule '
        'and the pin together, or reinstall from external/biofilm-processing.'
    )


def test_submodule_checked_out_at_pinned_tag():
    """The submodule working tree must actually be populated (a fresh clone
    without --recurse-submodules leaves it empty, which fails confusingly later)."""
    assert (SUBMODULE_ROOT / 'pyproject.toml').is_file(), (
        f'{SUBMODULE_ROOT} is empty — run: git submodule update --init --recursive'
    )
    text = (SUBMODULE_ROOT / 'pyproject.toml').read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    assert m and m.group(1) == _pinnedVersion(), (
        f'submodule is checked out at version {m.group(1) if m else "?"} but '
        f'pyproject pins {_pinnedVersion()}.'
    )


def test_timelapse_signature_contract():
    """Every keyword biofilm_embeddings's GUI passes to timelapseProcessing must
    still exist in biofilm-processing's signature (catches API drift)."""
    from multiWellAnalysis.processing.analysis_main import timelapseProcessing
    have = set(inspect.signature(timelapseProcessing).parameters)
    passed = {  # mirror of gui/tabs/run.py:_processOneWell's call
        'images', 'blockDiameter', 'ntimepoints', 'shiftThresh', 'fixedThresh',
        'dustCorrection', 'outdir', 'filename', 'imageRecords', 'fftStride',
        'downsample', 'skipOverlay', 'workers',
    }
    missing = passed - have
    assert not missing, (
        f'timelapseProcessing no longer accepts {missing}; update the call in '
        'biofilm_embeddings/gui/tabs/run.py to match biofilm-processing.'
    )


def test_metadata_and_preprocessing_entrypoints_exist():
    from multiWellAnalysis.processing.image_metadata import probePlateMeta  # noqa
    from multiWellAnalysis.processing.preprocessing import normalizeLocalContrast  # noqa


def test_embeddings_import():
    """biofilm_embeddings's own layer imports (needs torch — skipped if absent)."""
    pytest.importorskip('torch')
    pytest.importorskip('transformers')
    import biofilm_embeddings.embeddings.extractor  # noqa
    import biofilm_embeddings.embeddings.extract_one_plate  # noqa
