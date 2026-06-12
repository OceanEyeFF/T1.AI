# Harness Init Assets / Repo

这里承接 `set-harness-goal-skill` 自带的 `.servo/repo/` repo 级初始化模板。

当前入口：

- [analysis.md](./analysis.md)
- [discovery-input.md](./discovery-input.md)
- [complex-project-entry-gate.md](./complex-project-entry-gate.md)
- [snapshot-status.md](./snapshot-status.md)
- [temporary-understanding.md](./temporary-understanding.md)

`discovery-input.md` 只在 Existing Code Project Adoption 模式下生成到 `.servo/repo/discovery-input.md`，用于保存既有代码库的只读事实输入。它不是 goal truth；确认后的长期目标仍写入 `.servo/goal-charter.md`，初始化后的 repo 慢变量状态仍写入 `.servo/repo/snapshot-status.md`。

`temporary-understanding.md` 只在弱文档 adoption / onboarding 场景下生成到 `.servo/repo/temporary-understanding.md`；使用 deploy helper 时需显式传入 `--weak-doc-onboarding`。它用于记录 lightweight / full 发现模式、token-cost tradeoff、观察事实、推断目的、运行目的、风险、未知项、确认问题和 truth boundary。它是 runtime evidence，不是 goal truth；未经 programmer confirmation 或 verified evidence 的 inferred purpose 不得写入 Goal Charter 或 docs truth layer。

`complex-project-entry-gate.md` 在 repo-init / Existing Code Project Adoption 命中 complex-project trigger 时生成到 `.servo/repo/complex-project-entry-gate.md`；使用 deploy helper 可显式传入 `--complex-project-entry-gate`，而 `--weak-doc-onboarding` 会自动包含它。它记录 `complex_project_entry_gate`、`scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 和结构化 `reinforcement_milestone_recommendation`。它是 Milestone-side blocking gate, not fixed heavy mode；scanner output is evidence, not verdict。生成样例默认 `pending_programmer_confirmation`、`block_create, block_upsert, block_activate, block_derive_worktrack`、`needed = true` 和 `blocks_implementation_until_resolved = true`，不会预授权 `normal`、`autoreview` 或 `yolo`。scanner 随 skill payload 分发为 `scripts/complexity_signal_scanner.py`；安装后路径为 `.agents/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py` 或 `.claude/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py`。

`analysis.md` 是 RepoScope 的阶段性决策支撑 artifact，用于事实 / 推断 / 未知项、主要矛盾、优先级与路由投影；它不是 goal truth，也不是 worktrack queue。
