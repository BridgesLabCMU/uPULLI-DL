"""uint16 `_processed.tif` (biofilm-processing --processed-dtype uint16) is read as float32 [0, 1];
unmarked uint16 (raw camera frames) is still refused by the dataset's range check."""
import numpy as np
import pytest
import tifffile

from biofilm_embeddings.embeddings.dataset import _readProcessed, ProcessedTifDataset


def _stack(seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(0.5 + 0.02 * rng.standard_normal((4, 64, 64)), 0, 1).astype(np.float32)


def test_marked_uint16_reads_as_unit_float(tmp_path):
    ref = _stack()
    p = tmp_path / 'w_processed.tif'
    tifffile.imwrite(p, np.round(ref * 65535).astype(np.uint16), compression='zlib', predictor=2,
                     metadata={'processedScale': 65535})
    out = _readProcessed(str(p))
    assert out.dtype == np.float32
    assert np.abs(out - ref).max() <= 0.5 / 65535 + 1e-7


def test_float32_unchanged(tmp_path):
    ref = _stack(1)
    p = tmp_path / 'w_processed.tif'
    tifffile.imwrite(p, ref)
    assert np.array_equal(_readProcessed(str(p)), ref)


def test_unmarked_uint16_still_refused(tmp_path):
    p = tmp_path / 'raw.tif'
    tifffile.imwrite(p, (_stack(2) * 65535).astype(np.uint16))
    ds = ProcessedTifDataset([{'processed': str(p)}], nFrames=4, imageSize=56)
    with pytest.raises(ValueError):
        ds[0]
