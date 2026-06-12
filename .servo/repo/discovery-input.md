---
title: "Repo Discovery Input"
artifact_type: "repo-discovery-input"
generated_from: "servo-set-harness-goal-skill/assets/repo/discovery-input.md"
updated: "2026-06-09"
owner: "OceanEyeFF"
---

# Repo Discovery Input

> 这是 `.servo/repo/discovery-input.md` 的运行状态，用于 Existing Code Project Adoption 模式下记录既有代码库的只读事实输入。它不是 goal truth。

## Metadata

- repo: T1.AI
- owner: OceanEyeFF
- updated: 2026-06-09
- adoption_mode: existing-code-adoption
- source_scope: local_repo_readonly_plus_current_conversation
- generated_by: set-harness-goal-skill

## Source Materials

- repository_path: /home/oceaneye/github/T1.AI
- baseline_branch: develop
- current_branch: develop
- current_commit: b1c1f82bb87ae2ce32223ad2edb69ca501296c5b
- working_tree_state:
  - before_servo_bootstrap: clean except prior `.gitignore` update for `.serena/`
  - after_servo_bootstrap: uncommitted Servo install files and `.gitignore` updates
- user_provided_context:
  - user is the developer of both Servo and this A-share repo
  - use latest Servo test version via `npx servo-installer@next`
  - consolidate to a single worktree and work from the current branch
  - `.serena/` should be ignored/local and may be deleted
- inspected_paths:
  - README.md
  - NEXT_STEPS.md
  - ROADMAP.md
  - pyproject.toml
  - docs/modules/system_io_and_architecture_spec.md
  - git branch/status/worktree metadata
  - Servo installed skill assets
- skipped_paths:
  - data caches and generated datasets
  - model checkpoints
  - output reports/recommendations
  - runtime logs
  - external provider credentials

## Repository Facts

- primary_language_or_stack: Python
- package_or_build_system:
  - setuptools build backend
  - `pyproject.toml`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `environment.yml`
- runtime_entrypoints:
  - `scripts/build_universe.py`
  - `scripts/run_backtest.py`
  - `scripts/daily_pipeline.py`
  - `scripts/generate_daily_recommendations.py`
  - `scripts/validate_recommendations.py`
  - `scripts/evaluate_recommendation.py`
- test_entrypoints:
  - `pytest`
  - `scripts/run_develop_min_regression.sh`
  - targeted tests under `tests/`
- deploy_or_release_entrypoints:
  - `deployment/`
  - `scripts/daily_pipeline.sh`
  - pipeline and scheduler docs under `docs/modules`
- configuration_files:
  - `configs/data_source.yaml`
  - `configs/pipeline.yaml`
  - `configs/protocol.yaml`
  - `configs/model_mtl.yaml`
  - `configs/datasets/*.toml`
  - `configs/experiments/*.toml`
  - `configs/stock_pools/*.toml`

## Architecture And Module Inventory

- `src/ashare_lab/data`: data source connectors.
- `src/ashare_lab/dataset`: dataset and sequence builders.
- `src/ashare_lab/features`: feature modules.
- `src/ashare_lab/labels`: label generation.
- `src/ashare_lab/models`: model definitions.
- `src/ashare_lab/training`: training and finetuning.
- `src/ashare_lab/evaluation`: metrics and sanity checks.
- `src/ashare_lab/recommendation`: recommendation engine, history, validation, trend aggregation.
- `src/ashare_lab/backtest`: backtest book and engine.
- `src/ashare_lab/pipeline`: orchestrator and monitoring.
- `src/ashare_lab/stock_pool`: stock pool registry.
- `docs`: route, architecture, interface, research, and governance documents.
- `scripts`: CLI/script layer for data, training, evaluation, recommendation, and daily pipeline tasks.

## Build, Test, And Runtime Signals

- build_commands_seen:
  - `python -m pip install -e ".[dev]" --no-deps`
  - `conda env create -f environment.yml`
- test_commands_seen:
  - `pytest`
  - `scripts/run_develop_min_regression.sh`
- runtime_commands_seen:
  - `python scripts/build_universe.py`
  - `python scripts/run_backtest.py --symbols ...`
  - `python scripts/daily_pipeline.py`
- commands_not_run:
  - project test suite was not run during Servo bootstrap
  - no backtest was run during Servo bootstrap
  - no production/external API operation was run during Servo bootstrap

## Governance And Documentation Signals

- existing_docs:
  - README.md
  - NEXT_STEPS.md
  - ROADMAP.md
  - docs/README.md
  - docs/interfaces/*
  - docs/modules/*
  - docs/overview/*
  - docs/research/*
- agent_or_harness_instructions:
  - AGENTS-style local instructions supplied in conversation require Simplified Chinese responses and no unsolicited git commit/branch operations.
  - Servo harness skills installed under `.agents/skills` and `.claude/skills`.
- ownership_or_layering_rules:
  - execution layer currently has priority over model expansion
  - default mainline model is `3d/5d/10d`
  - `1d` is independent and must not contaminate default mainline scoring/reporting
  - pipeline-first architecture; no full-chain black-box E2E
- review_or_verify_rules:
  - changes should include focused validation proportional to risk
  - execution changes require diagnostics/evidence, not only net-value output
  - model changes require comparable windows and stable reports
- known_policy_constraints:
  - A-share T+1, limit-up/limit-down, failed fills, long-only, fees, and low-turnover constraints
  - no hidden production API calls
  - no destructive operations or git publishing without explicit instruction

## Risks And Unknowns

- Execution-layer closure remains incomplete.
- User-defined Servo work habit controls are not fully decided.
- `.servo/` versioning policy is undecided because the deploy helper added `.servo/` to `.gitignore`.
- Current Servo harness version and installed harness asset VERSION differ in naming:
  - installer observed: `0.6.1-rc.2`
  - harness skill VERSION observed: `0.5.1-rc.1`
- Tests were not run after installation.

## Candidate Goal Signals

> 只记录从既有代码、文档或用户说明中可追溯的候选目标信号。不要把这些条目写成已确认目标；确认后的长期目标只能进入 `.servo/goal-charter.md`。

- Build an auditable A-share low-frequency research/execution system.
- Prioritize execution-layer closure before adding model complexity.
- Stabilize mainline `3d/5d/10d` and keep `1d` independent.
- Consolidate local development into one worktree/current branch.
- Use Servo as the control-plane framework for milestone/worktrack governance.

## Confirmation Questions

- Should `.servo/` remain local-only, or should Servo control artifacts be versioned in this repo?
- Should `develop` be treated as a protected branch even though you are the solo developer?
- May Servo create local feature branches inside the single worktree when a worktrack warrants it?
- How many worktracks may Servo open automatically inside one confirmed milestone?
- Should Servo stop after each autonomous slice, or continue until the milestone budget is exhausted?
- Should SubAgent dispatch stay `auto`, be forced to delegated execution, or use the current carrier by default?

## Downstream Mapping Notes

- goal_charter_inputs:
  - README, NEXT_STEPS, ROADMAP, and system I/O docs provide enough confirmed project direction for the initial charter.
- snapshot_status_inputs:
  - git status, branch/worktree metadata, pyproject, module inventory, and installed Servo outputs.
- control_state_links:
  - user-defined controls remain pending unless explicitly confirmed by the programmer.

## Notes

- Discovery input is intentionally conservative: observed facts and candidate signals are separated from approved long-term truth.
