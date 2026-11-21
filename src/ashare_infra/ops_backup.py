"""Copy an explicit set of operational files and verify an isolated restore."""

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

MANIFEST = "backup_manifest.json"
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _check_sqlite(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError(f"SQLite integrity check failed for {path.name}")


def _copy(source, target, *, sqlite_snapshot=False):
    target.parent.mkdir(parents=True, exist_ok=True)
    if sqlite_snapshot:
        # Read committed data and the WAL, if present, as one database snapshot.
        with (
            closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src,
            closing(sqlite3.connect(target)) as dst,
        ):
            src.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE").fetchone()
        _check_sqlite(target)
    else:
        shutil.copyfile(source, target)
    target.chmod(0o600)


def _safe_target(path):
    if path.is_symlink():
        raise ValueError("destination must not be a symlink")
    path = path.resolve()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError("destination must be a new or empty directory")
    if not path.parent.is_dir():
        raise ValueError("destination parent must already exist")
    return path


def _regular_files(root, paths):
    for path in paths:
        if not path.exists() and not path.is_symlink():
            continue
        entries = path.rglob("*") if path.is_dir() else [path]
        for entry in entries:
            relative = entry.relative_to(root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if entry.name.lower().endswith(("-wal", "-shm", "-journal", ".tmp")):
                continue
            if entry.is_symlink() or not entry.resolve().is_relative_to(root):
                raise ValueError(f"backup input is a symlink: {relative}")
            if entry.is_file():
                yield relative


def backup(root, destination, paths):
    target = _safe_target(destination)
    if target == root or root.is_relative_to(target):
        raise ValueError("backup destination would contain the source")
    if any(target.is_relative_to(path.resolve()) for path in paths if path.is_dir()):
        raise ValueError("backup destination overlaps a selected data directory")
    files = sorted(set(_regular_files(root, paths)))
    if not files:
        raise ValueError("no operational files found for backup")
    with TemporaryDirectory(prefix=".t1-backup-", dir=target.parent) as stage:
        staging = Path(stage)
        payload = staging / "payload"
        payload.mkdir(mode=0o700)
        entries = []
        for relative in files:
            source, output = root / relative, payload / relative
            sqlite = relative.suffix.lower() in SQLITE_SUFFIXES
            _copy(source, output, sqlite_snapshot=sqlite)
            entries.append(
                {"path": relative.as_posix(), "sha256": digest(output), "sqlite": sqlite}
            )
        manifest = payload / MANIFEST
        manifest.write_text(
            json.dumps({"version": 1, "files": entries}, indent=2), encoding="utf-8"
        )
        manifest.chmod(0o600)
        payload.rename(_safe_target(target))
    return {"status": "pass", "files": len(entries), "destination": str(target)}


def restore(source, destination):
    target = _safe_target(destination)
    source = source.resolve()
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("backup source and restore destination must be disjoint")
    manifest = source / MANIFEST
    if manifest.is_symlink():
        raise ValueError("backup manifest must be a regular file")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    entries = metadata["files"]
    if metadata.get("version") != 1 or not entries:
        raise ValueError("invalid backup manifest")
    seen = set()
    with TemporaryDirectory(prefix=".t1-restore-", dir=target.parent) as stage:
        payload = Path(stage) / "payload"
        payload.mkdir(mode=0o700)
        for entry in entries:
            relative = Path(entry["path"])
            if (
                not relative.parts
                or relative.is_absolute()
                or relative.as_posix() != entry["path"]
                or any(part.startswith(".") for part in relative.parts)
                or relative.name == MANIFEST
                or relative in seen
            ):
                raise ValueError(f"invalid backup path: {relative}")
            seen.add(relative)
            original = source / relative
            if original.is_symlink() or original.resolve() != original or not original.is_file():
                raise ValueError(f"missing or unsafe backup member: {relative}")
            output = payload / relative
            _copy(original, output)
            if digest(output) != entry["sha256"]:
                raise ValueError(f"checksum mismatch for {relative}")
            if relative.suffix.lower() in SQLITE_SUFFIXES:
                _check_sqlite(output)
        payload.rename(_safe_target(target))
    return {"status": "pass", "files": len(entries), "destination": str(target)}
