# Harness Init Assets

`set-harness-goal-skill/assets/` 是 `set-harness-goal-skill` 自带的 `.servo` 初始化资产包。

这里存放的是 `.servo/` 运行目录所需的模板来源，用来在 deploy 后或初始化时生成 `.servo/` 目录结构，以及少量直接属于 Harness 运行管理面的文档。它们是本技能的 canonical executable resources，不是独立的源码根，也不会替代 `docs/harness/` 的 artifact contract 真相层。

当前入口：

- [control-state.md](./control-state.md)
- [goal-charter.md](./goal-charter.md)
- [repo/README.md](./repo/README.md)
- [worktrack/README.md](./worktrack/README.md)
- [template/README.md](./template/README.md)

规则：

- 这些资产只服务 `set-harness-goal-skill` 的 `.servo` 初始化流程
- 默认初始化会生成 [repo/analysis.md](./repo/analysis.md)，作为 RepoScope 的阶段性决策支撑 artifact
- Existing Code Project Adoption 模式可以额外生成 [repo/discovery-input.md](./repo/discovery-input.md)，把既有代码库观察结果写入 `.servo/repo/discovery-input.md`
- `repo/discovery-input.md` 是只读事实输入，不是 goal truth；它只能作为 `goal-charter.md` 和 `snapshot-status.md` 的候选来源
- 弱文档 adoption / onboarding 场景可以通过 `--weak-doc-onboarding` 额外生成 [repo/temporary-understanding.md](./repo/temporary-understanding.md)，把 lightweight / full 模式选择、token-cost tradeoff、observed_facts、inferred_purpose、operational_purpose、known_risks、unknowns、confirmation_questions、promotion_plan 和 truth_boundary 写成 runtime evidence；它不是 goal truth
- repo-init 命中 complex-project trigger 时，可以通过 `--complex-project-entry-gate` 额外生成 [repo/complex-project-entry-gate.md](./repo/complex-project-entry-gate.md)；`--weak-doc-onboarding` 会自动生成该 gate。它记录 `complex_project_entry_gate`、`scanner_evidence_ref`、`complexity_signals`、`operator_safety_policy`、`dialog_review_questions`、`milestone_blocking_decision` 和结构化 `reinforcement_milestone_recommendation`；它是 Milestone-side blocking gate, not fixed heavy mode；scanner output is evidence, not verdict。生成样例默认 `pending_programmer_confirmation`、`block_create, block_upsert, block_activate, block_derive_worktrack`、`needed = true`、`blocks_implementation_until_resolved = true`，不会预授权 `normal`、`autoreview` 或 `yolo`。scanner 随 skill payload 分发为 `scripts/complexity_signal_scanner.py`；安装后路径为 `.agents/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py` 或 `.claude/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py`
- 建议通过 [../scripts/deploy_servo.js](../scripts/deploy_servo.js) 生成 `.servo/` 样例，而不是手工复制这些文件
- 用法固定为把目标 repo / worktree 根作为 `--deploy-path` 传入；脚本会在 `<deploy-path>/.servo/` 下生成文件
- 如果目标 repo 也要给 Claude Code 暴露本技能，可在 `generate` 时追加 `--install-claude-skill`，或单独运行 `install-claude-skill` 子命令；目标路径是 `<deploy-path>/.claude/skills/servo-set-harness-goal-skill/`
- Claude install 允许 root 层 symlink / mount，但拒绝目标 skill 目录本身或其内部已有 symlink；完整边界见 `SKILL.md` 与 Claude usage help
- 如果目标 skill 目录本身不是 symlink，但经允许的 root symlink / mount 解析后就是当前运行的技能包，安装视为 already installed 并 no-op
- 需要完整参数说明时，直接运行 `node scripts/deploy_servo.js generate --help`
- 资产 owner 已固定在本技能；不要再为它们建立独立的 `.servo` 模板源码根
- goal 修正文档不进入 `.servo/` 路径，只作为 Codex 对话回答流模板存在
- 不要把 doctrine、运行协议或 backend wrapper 写到这里
- 不要把这些资产误当成 `docs/` 真相层
- 运行协议与 artifact 定义的 source-side authoring truth 位于上游 `docs/harness/`；本技能执行时只依赖随包分发的 `SKILL.md`、`assets/` 和 `scripts/`

示例：

```bash
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --owner servo-kernel
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption --weak-doc-onboarding
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --adoption-mode existing-code-adoption --complex-project-entry-gate
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --install-claude-skill
node scripts/deploy_servo.js install-claude-skill --deploy-path "$DEPLOY_PATH"
node scripts/deploy_servo.js generate --deploy-path "$DEPLOY_PATH" --baseline-branch "$BASELINE_BRANCH" --force --dry-run
```
