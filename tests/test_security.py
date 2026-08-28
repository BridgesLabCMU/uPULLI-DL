"""Regression tests for the two hardening fixes in the embeddings layer.

Both guard against the same shape of problem: files under `<root>/embeddings/`
and `<plate>/processedImages/` are routinely read from shared network storage
that several machines write to, and (once this is published) from datasets
obtained from other groups. Neither `index.csv` nor a `.pt` cache is trusted
input just because it is on disk.
"""
import pytest

torch = pytest.importorskip('torch')
pd = pytest.importorskip('pandas')

from biofilm_embeddings.embeddings.extractor import (  # noqa: E402
    _INDEX_FORMAT,
    indexToFrame,
    loadCache,
    resolveProcessedPath,
)


# --- CWE-22: index.csv must not be able to point outside its own directory ---

def test_resolve_processed_path_accepts_a_neighbouring_file(tmp_path):
    """The normal case: the stack sits beside the index.csv that names it."""
    stack = tmp_path / 'A1_02_processed.tif'
    stack.write_bytes(b'not really a tif')
    assert resolveProcessedPath(str(tmp_path), 'A1_02_processed.tif') == str(stack)


def test_resolve_processed_path_reresolves_a_dead_absolute_path(tmp_path):
    """The NAS-mirror case: the stored absolute path is dead (that staging dir
    was deleted after sync, or never existed on this machine), but the file is
    present next to the index. This must still resolve — it is the whole reason
    the function exists."""
    stack = tmp_path / 'A1_02_processed.tif'
    stack.write_bytes(b'not really a tif')
    stale = '/staging/on/some/other/machine/A1_02_processed.tif'
    assert resolveProcessedPath(str(tmp_path), stale) == str(stack)


@pytest.mark.parametrize('hostile', [
    '/etc/passwd',
    '../../../../../../etc/passwd',
    '~/.ssh/id_ed25519',
    '/proc/self/environ',
])
def test_resolve_processed_path_refuses_to_escape_the_index_dir(tmp_path, hostile):
    """A crafted index.csv must not turn into an arbitrary file read."""
    got = resolveProcessedPath(str(tmp_path), hostile)
    assert got == '', f'{hostile!r} escaped confinement and resolved to {got!r}'


def test_resolve_processed_path_empty_is_empty(tmp_path):
    assert resolveProcessedPath(str(tmp_path), '') == ''


# --- CWE-502: caches must load without running pickled code ---

def _writeCacheNewFormat(path):
    """A cache shaped the way extractAll writes them now."""
    df = pd.DataFrame([
        {'plate': 'P1', 'well': 'A1_02', 'mag': '_02', 'processed': '/x/A1.tif'},
        {'plate': 'P1', 'well': 'A2_02', 'mag': '_02', 'processed': '/x/A2.tif'},
    ])
    torch.save({
        'cls': torch.zeros(2, 3, 8),
        'patches': torch.zeros(2, 3, 9, 8),
        'wells': ['A1_02', 'A2_02'],
        'plates': ['P1', 'P1'],
        'index': {c: df[c].astype(str).tolist() for c in df.columns},
        'indexFormat': _INDEX_FORMAT,
        'gridSize': 3,
        'model': 'facebook/dinov2-base',
    }, path)


def test_new_format_cache_loads_with_weights_only(tmp_path):
    """The point of the format change: no pickle execution path on load."""
    p = tmp_path / 'cls_cache.pt'
    _writeCacheNewFormat(p)

    cache = loadCache(p)
    assert cache['indexFormat'] == _INDEX_FORMAT
    assert tuple(cache['cls'].shape) == (2, 3, 8)

    # Belt and braces: the restricted unpickler accepts it directly too.
    torch.load(p, weights_only=True)


def test_index_survives_the_round_trip_with_dtypes_intact(tmp_path):
    """Columns must come back as strings. A CSV round-trip would turn '_02'
    fine but empty strings into NaN and numeric-looking columns into floats,
    which breaks downstream filtering on `mag`."""
    p = tmp_path / 'cls_cache.pt'
    _writeCacheNewFormat(p)

    df = indexToFrame(loadCache(p)['index'])
    assert list(df.columns) == ['plate', 'well', 'mag', 'processed']
    assert df['mag'].tolist() == ['_02', '_02']
    assert all(isinstance(v, str) for v in df['mag'])


def test_legacy_pickled_cache_is_refused_not_silently_loaded(tmp_path):
    """A cache with a pickled DataFrame (the old format) must fail loudly with
    an actionable message rather than fall back to unsafe loading."""
    p = tmp_path / 'legacy_cache.pt'
    torch.save({'cls': torch.zeros(1, 2, 4), 'index': pd.DataFrame([{'a': '1'}])}, p)

    with pytest.raises(RuntimeError, match='could not be loaded safely'):
        loadCache(p)

    # ...and the explicit opt-in still works, for a file you actually trust.
    cache = loadCache(p, allowUnsafe=True)
    assert indexToFrame(cache['index']).shape == (1, 1)


def test_index_to_frame_accepts_both_formats():
    df = pd.DataFrame([{'well': 'A1', 'mag': '_02'}])
    assert indexToFrame(df) is df
    assert indexToFrame({'well': ['A1'], 'mag': ['_02']}).equals(df)
