from __future__ import annotations

from scripts.build_sequence_dataset import _dataset_fingerprint


def test_dataset_fingerprint_is_content_based_not_path_based() -> None:
    checksums = {
        "train": "a" * 64,
        "valid": "b" * 64,
        "test": "c" * 64,
    }
    first = {
        name: {"path": f"workspace/a/{name}.parquet", "rows": 10, "sha256": checksum}
        for name, checksum in checksums.items()
    }
    moved = {
        name: {"path": f"/tmp/moved/{name}.parquet", "rows": 10, "sha256": checksum}
        for name, checksum in checksums.items()
    }
    changed = {
        name: {"path": f"/tmp/moved/{name}.parquet", "rows": 11, "sha256": checksum}
        for name, checksum in checksums.items()
    }

    assert _dataset_fingerprint(first) == _dataset_fingerprint(moved)
    assert _dataset_fingerprint(first) != _dataset_fingerprint(changed)
