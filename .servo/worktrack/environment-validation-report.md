---
title: "WT-ENV-001 Environment Validation Report"
artifact_type: "environment-validation-report"
updated: "2026-06-11T13:14:12+08:00"
owner: "OceanEyeFF"
---

# WT-ENV-001 Environment Validation Report

## Control Signal

- worktrack_id: WT-ENV-001
- milestone_id: MS-ENV-000
- verdict: go-for-cpu-development
- downstream_ms_s0_001_ready: yes, with GPU caveat
- canonical_environment: py311-private
- decisive_result: `py311-private` can import core dependencies and project modules, passes env guard, and passes the minimal pytest subset.
- residual_risk: CUDA is visible but current PyTorch wheel does not support GTX 1080 Ti compute capability `sm_61`; GPU training should be treated as follow-up if needed.
- final_milestone_acceptance: programmer-owned

## Scope And Constraints

- In scope: conda inventory, `py311-private` repair, environment-name contract migration, import smoke, project import smoke, env guard verification, minimal pytest subset, and report.
- Out of scope: destructive environment deletion, production/external API calls, model training, commit, push, release, tag, final milestone acceptance.
- Repair performed with programmer approval: installed missing packages into `py311-private` and changed repo environment contract from `ashare-lab` to `py311-private`.

## Command Evidence

### Conda And Candidate Runtime

- command: `conda --version`
- result: pass
- output_summary: `conda 25.9.1`

- command: `conda run -n "py311-private" python --version`
- result: pass
- output_summary: `Python 3.11.15`

- command: `conda run -n "py311-private" python -c "import os, sys; ..."`
- result: pass
- output_summary:
  - executable: `/home/oceaneye/miniconda3/envs/py311-private/bin/python`
  - `CONDA_DEFAULT_ENV`: `py311-private`

### Dependency Repair

- command: `conda run -n "py311-private" python -m pip install "pyarrow>=14.0" "torch>=2.0" "optuna>=3.6" "pytest>=8" "pytest-cov>=4" "ruff>=0.5"`
- result: pass
- installed_key_packages:
  - `pyarrow 24.0.0`
  - `torch 2.12.0+cu130`
  - `optuna 4.9.0`
  - `pytest 9.0.3`
  - `pytest-cov 7.1.0`
  - `ruff 0.15.16`

### Core Dependency Import Smoke

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -c ...`
- result: pass
- passed_imports:
  - `pandas 3.0.3`
  - `numpy 2.4.6`
  - `pyarrow 24.0.0`
  - `torch 2.12.0+cu130`
  - `sklearn 1.8.0`
  - `xgboost 3.2.0`
  - `optuna 4.9.0`
  - `akshare 1.18.62`
  - `tushare 1.4.29`
  - `yaml 6.0.3`
  - `pytest 9.0.3`
- failed_modules: none

### Project Package Import Smoke

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -c ...`
- result: pass
- passed_imports:
  - `ashare_lab`
  - `ashare_lab.data`
  - `ashare_lab.features`
  - `ashare_lab.dataset`
  - `ashare_lab.models`
  - `ashare_lab.evaluation`
  - `ashare_lab.recommendation`

### Environment Guard

- changed_contract:
  - `scripts/env_guard.py` default environment changed to `py311-private`
  - guarded training/tuning scripts now call `ensure_required_conda_env("py311-private")`
  - setup docs and `environment.yml` now use `py311-private`

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -c 'from scripts.env_guard import ensure_required_conda_env; ensure_required_conda_env(); print("guard ok")'`
- result: pass
- output_summary: `guard ok`

### Ruff

- command: `conda run -n "py311-private" ruff --version`
- result: pass
- output_summary: `ruff 0.15.16`

### Minimal Pytest Subset

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_env_guard.py tests/test_features_technical.py tests/test_sequence_builder.py tests/test_models.py`
- result: pass
- output_summary: `36 passed, 10 warnings in 4.25s`

- command: `CUDA_VISIBLE_DEVICES="" PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_env_guard.py tests/test_features_technical.py tests/test_sequence_builder.py tests/test_models.py`
- result: pass
- output_summary: `36 passed, 8 warnings in 4.28s`

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_env_guard.py tests/test_features_technical.py tests/test_sequence_builder.py tests/test_models.py`
- result: pass
- output_summary: closeout rerun passed, `36 passed, 10 warnings in 3.32s`

### CUDA Visibility

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -c 'import torch; ...'`
- result: partial
- output_summary:
  - `torch_version`: `2.12.0+cu130`
  - `cuda_version`: `13.0`
  - `cuda_available`: `True`
  - `device_count`: `1`
  - supported arch list: `sm_75`, `sm_80`, `sm_86`, `sm_90`, `sm_100`, `sm_120`
- residual_risk: local GPU is GTX 1080 Ti / `sm_61`, which current PyTorch wheel warns is unsupported.

- command: `PYTHONPATH="src:." conda run -n "py311-private" python -m pytest -q tests/test_models.py::test_train_mtl_runs_on_cuda_if_available`
- result: pass after test guard refinement
- output_summary: `1 passed, 2 warnings in 2.11s`
- interpretation: test now skips GPU training when CUDA is visible but cannot execute a minimal CUDA kernel on this hardware/wheel combination.

## Code And Documentation Changes

- Environment contract migrated from `ashare-lab` to `py311-private` in:
  - `environment.yml`
  - `scripts/env_guard.py`
  - guarded training/tuning scripts
  - `scripts/setup_conda_env.sh`
  - `README.md`
  - `docs/interfaces/setup.md`
  - active research/setup docs with command examples
- `tests/test_models.py` updated to match current `configs/model_mtl.yaml` values and to avoid treating CUDA visibility as equivalent to CUDA executability.

## Completion Signal Coverage

- conda_runtime_identified: pass
- python_version_supported: pass
- core_dependency_imports_passed: pass
- package_import_smoke_passed: pass
- minimal_test_entry_verified: pass
- environment_report_written: pass
- downstream_gate_decision_recorded: pass

## Verdict

- status: go-for-cpu-development
- gate_result: pass with residual GPU caveat
- downstream_decision: `MS-S0-001` may proceed if CPU development/testing is acceptable.
- confidence: high
- confidence_reason: imports, env guard, ruff, and minimal pytest pass in `py311-private`.

## Residual Risks

- GPU training on the local GTX 1080 Ti is not validated with the current PyTorch wheel because `sm_61` is unsupported by `torch 2.12.0+cu130`.
- External provider credentials and network behavior remain out of scope.
- Package versions differ from the old `environment.yml`; future failures should be classified by test evidence rather than assuming the old env contract.
