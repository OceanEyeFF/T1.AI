#!/usr/bin/env python3
"""Emit read-only complex-project signal evidence for Harness gates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

sys.dont_write_bytecode = True


SCHEMA_VERSION = "complexity-signal-scanner/v1"
EVIDENCE_DISCLAIMER = "scanner output is evidence, not verdict"
SECRET_SAFETY_NOTE = (
    "skips secret-like paths and does not emit file contents; bounded reads still inspect "
    "non-secret-like text/code files for aggregate signals"
)
MAX_TEXT_BYTES = 512_000
MAX_CODE_BYTES_PER_FILE = 2_000_000
MAX_RECORDED_PATHS = 40
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".servo",
    ".aw",
    ".autoworkflow",
    ".spec-workflow",
    ".agents",
    ".claude",
    ".logs",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "env",
    "target",
}
CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
TEXT_EXTENSIONS = CODE_EXTENSIONS | {
    ".cfg",
    ".conf",
    ".ini",
    ".json",
    ".md",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PACKAGE_MANAGER_FILES = {
    "package.json": "node",
    "pnpm-lock.yaml": "node",
    "yarn.lock": "node",
    "package-lock.json": "node",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "poetry.lock": "python",
    "Pipfile": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "jvm",
    "build.gradle": "jvm",
    "build.gradle.kts": "jvm",
    "composer.json": "php",
    "Gemfile": "ruby",
    "mix.exs": "elixir",
}
COMPOSE_FILE_RE = re.compile(r"(^|[-_.])(?:docker-)?compose(?:[-_.].*)?\.ya?ml$", re.IGNORECASE)
DOCKERFILE_RE = re.compile(r"(^|/)Dockerfile(?:[.-].*)?$")
SERVICE_DIR_RE = re.compile(
    r"^(api|app|apps|backend|client|frontend|gateway|server|service|services|worker|web|packages)$",
    re.IGNORECASE,
)
SECRET_PATH_RE = re.compile(
    r"(^|/)(\.env(?:[./_-].*)?|.*(secret|secrets|credential|credentials|token|private[_-]?key|"
    r"id_rsa|id_dsa|\.pem|\.p12|\.pfx|keystore).*)$",
    re.IGNORECASE,
)
DEBT_MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|WORKAROUND|DEPRECATED)\b")
MIGRATION_PATH_RE = re.compile(
    r"(^|/)(migrations?|db/migrate|alembic|prisma/migrations|schema\.sql|seed|seeds|fixtures?)(/|$)",
    re.IGNORECASE,
)
DEPLOY_PATH_RE = re.compile(
    r"(^|/)(\.github/workflows|\.gitlab-ci\.ya?ml|Jenkinsfile|Dockerfile|docker-compose|compose|"
    r"k8s|kubernetes|helm|terraform|deploy|deployment|vercel\.json|netlify\.toml)(/|$|[._-])",
    re.IGNORECASE,
)
THRESHOLDS = {
    "compose_files": {"medium": 1, "high": 2},
    "compose_services": {"medium": 2, "high": 5},
    "package_managers": {"medium": 2, "high": 4},
    "service_like_dirs": {"medium": 3, "high": 8},
    "code_files": {"medium": 500, "high": 2000},
    "code_lines": {"medium": 50_000, "high": 200_000},
    "ci_deploy_hints": {"medium": 2, "high": 6},
    "migration_data_hints": {"medium": 1, "high": 5},
    "debt_proxy_markers": {"medium": 20, "high": 100},
}


@dataclass(frozen=True)
class RepoFile:
    path: Path
    relative_path: str
    is_symlink: bool


def rel_path(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def is_secret_like(relative_path: str) -> bool:
    return bool(SECRET_PATH_RE.search(relative_path))


def iter_repo_files(repo_root: Path) -> Iterable[RepoFile]:
    for root_name, dirs, files in os.walk(repo_root):
        root = Path(root_name)
        dirs[:] = sorted(
            dirname
            for dirname in dirs
            if not should_skip_dir(root / dirname)
            and not (root / dirname).is_symlink()
        )
        for filename in sorted(files):
            path = root / filename
            yield RepoFile(
                path=path,
                relative_path=rel_path(path, repo_root),
                is_symlink=path.is_symlink(),
            )


def read_text_bounded(path: Path, max_bytes: int = MAX_TEXT_BYTES) -> tuple[str, bool]:
    data = path.read_bytes()[: max_bytes + 1]
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="ignore"), truncated


def recorded(paths: Iterable[str]) -> list[str]:
    return sorted(paths)[:MAX_RECORDED_PATHS]


def level_for(value: int, threshold: dict[str, int]) -> str:
    if value >= threshold["high"]:
        return "high"
    if value >= threshold["medium"]:
        return "medium"
    if value > 0:
        return "low"
    return "none"


def signal(signal_id: str, value: int, description: str) -> dict[str, object]:
    threshold = THRESHOLDS[signal_id]
    return {
        "signal": signal_id,
        "observed_value": value,
        "threshold": threshold,
        "level": level_for(value, threshold),
        "description": description,
    }


def scan_compose_file(path: Path) -> dict[str, object]:
    text, truncated = read_text_bounded(path)
    services: set[str] = set()
    in_services = False
    services_indent = 0
    service_indent: int | None = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if re.match(r"^services\s*:\s*$", stripped):
            in_services = True
            services_indent = indent
            service_indent = None
            continue
        if in_services:
            if indent <= services_indent and not stripped.startswith("-"):
                in_services = False
                service_indent = None
                continue
            match = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(?:#.*)?$", stripped)
            if match and indent > services_indent:
                if service_indent is None:
                    service_indent = indent
                if indent != service_indent:
                    continue
                name = match.group(1)
                if not name.startswith("x-"):
                    services.add(name)
    keys = {
        "build": len(re.findall(r"(?m)^\s*build\s*:", text)),
        "build_context": len(re.findall(r"(?m)^\s*context\s*:", text)),
        "ports": len(re.findall(r"(?m)^\s*ports\s*:", text)),
        "volumes": len(re.findall(r"(?m)^\s*volumes\s*:", text)),
        "env_file": len(re.findall(r"(?m)^\s*env_file\s*:", text)),
    }
    return {
        "services": sorted(services),
        "service_count": len(services),
        "keys": keys,
        "truncated": truncated,
    }


def count_code_lines(path: Path) -> tuple[int, bool]:
    total = 0
    read_bytes = 0
    truncated = False
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            read_bytes += len(chunk)
            if read_bytes > MAX_CODE_BYTES_PER_FILE:
                truncated = True
                break
            total += chunk.count(b"\n")
    return total, truncated


def scan_repo(repo_root: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError(f"repo path is not a directory: {repo_root}")

    files = list(iter_repo_files(repo_root))
    skipped_symlink_files = [item.relative_path for item in files if item.is_symlink]
    skipped_secret_like_files = [
        item.relative_path
        for item in files
        if not item.is_symlink and is_secret_like(item.relative_path)
    ]
    readable_files = [
        item
        for item in files
        if not item.is_symlink and not is_secret_like(item.relative_path)
    ]

    compose_details: dict[str, object] = {}
    compose_paths: list[str] = []
    compose_services = 0
    compose_key_totals = Counter()
    package_managers: dict[str, list[str]] = {}
    service_like_dirs: set[str] = set()
    ci_deploy_hints: set[str] = set()
    migration_data_hints: set[str] = set()
    debt_proxy_markers = 0
    debt_marker_files: set[str] = set()
    code_files = 0
    code_lines = 0
    truncated_code_files: list[str] = []
    truncated_text_files: list[str] = []

    for item in readable_files:
        path = item.path
        relative = item.relative_path
        name = path.name
        suffix = path.suffix.lower()

        if COMPOSE_FILE_RE.search(name):
            compose_paths.append(relative)
            detail = scan_compose_file(path)
            compose_details[relative] = detail
            compose_services += int(detail["service_count"])
            compose_key_totals.update(detail["keys"])

        if name in PACKAGE_MANAGER_FILES:
            package_managers.setdefault(PACKAGE_MANAGER_FILES[name], []).append(relative)

        if DEPLOY_PATH_RE.search(relative) or DOCKERFILE_RE.search(relative):
            ci_deploy_hints.add(relative)

        if MIGRATION_PATH_RE.search(relative) or suffix == ".sql":
            migration_data_hints.add(relative)

        if suffix in CODE_EXTENSIONS:
            code_files += 1
            line_count, truncated = count_code_lines(path)
            code_lines += line_count
            if truncated:
                truncated_code_files.append(relative)

        if suffix in TEXT_EXTENSIONS:
            text, truncated = read_text_bounded(path)
            marker_count = len(DEBT_MARKER_RE.findall(text))
            if marker_count:
                debt_proxy_markers += marker_count
                debt_marker_files.add(relative)
            if truncated:
                truncated_text_files.append(relative)

        parts = Path(relative).parts
        for index, part in enumerate(parts[:-1], start=1):
            if SERVICE_DIR_RE.match(part):
                service_like_dirs.add(Path(*parts[:index]).as_posix())

    observations = {
        "compose_files": recorded(compose_paths),
        "compose_details": compose_details,
        "compose_services": compose_services,
        "compose_key_totals": dict(sorted(compose_key_totals.items())),
        "package_managers": {
            name: recorded(paths) for name, paths in sorted(package_managers.items())
        },
        "service_like_dirs": recorded(service_like_dirs),
        "ci_deploy_hints": recorded(ci_deploy_hints),
        "migration_data_hints": recorded(migration_data_hints),
        "debt_proxy_signals": {
            "marker_count": debt_proxy_markers,
            "sample_files": recorded(debt_marker_files),
        },
        "code_size": {
            "file_count": code_files,
            "line_count": code_lines,
            "line_count_mode": "bounded-read",
            "truncated_files": recorded(truncated_code_files),
        },
    }
    signals = [
        signal("compose_files", len(compose_paths), "Compose file count."),
        signal("compose_services", compose_services, "Service definitions observed in compose files."),
        signal("package_managers", len(package_managers), "Distinct package manager ecosystems."),
        signal("service_like_dirs", len(service_like_dirs), "Service-like directory names."),
        signal("code_files", code_files, "Code file count under scanner traversal roots."),
        signal("code_lines", code_lines, "Bounded code line count under scanner traversal roots."),
        signal("ci_deploy_hints", len(ci_deploy_hints), "CI, deployment, container, or infrastructure path hints."),
        signal("migration_data_hints", len(migration_data_hints), "Migration, SQL, seed, or data-risk path hints."),
        signal("debt_proxy_markers", debt_proxy_markers, "TODO/FIXME/HACK/XXX style debt markers."),
    ]
    strongest = max((item["level"] for item in signals), key=["none", "low", "medium", "high"].index)
    return {
        "schema_version": SCHEMA_VERSION,
        "target_repo": str(repo_root),
        "scanner": {
            "name": "complexity_signal_scanner.py",
            "evidence_only": True,
            "verdict": "not_provided",
            "semantics": EVIDENCE_DISCLAIMER,
        },
        "thresholds": THRESHOLDS,
        "signals": signals,
        "complexity_signals": signals,
        "observations": observations,
        "safety": {
            "read_only": True,
            "no_network": True,
            "no_service_start": True,
            "no_docker_database_deploy_execution": True,
            "no_destructive_writes": True,
            "file_content_read_mode": "bounded_text_and_code_reads",
            "secret_like_path_content_read": False,
            "file_contents_emitted": False,
            "secret_safety_note": SECRET_SAFETY_NOTE,
            "skipped_secret_like_files": recorded(skipped_secret_like_files),
            "skipped_symlink_files": recorded(skipped_symlink_files),
            "skipped_directories": sorted(SKIP_DIR_NAMES),
            "truncated_text_files": recorded(truncated_text_files),
        },
        "summary": {
            "signal_count": sum(1 for item in signals if item["level"] != "none"),
            "strongest_signal_level": strongest,
            "scanner_output_role": EVIDENCE_DISCLAIMER,
            "review_required": "LLM/Gate must judge these signals with programmer confirmations and operator_safety_policy.",
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a repository for read-only complex-project signal evidence."
    )
    parser.add_argument("--repo", type=Path, default=Path("."), help="Repository root to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON evidence.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = scan_repo(args.repo)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"{result['scanner']['name']}: {result['summary']['scanner_output_role']}")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
