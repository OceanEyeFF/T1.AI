---
name: doc-catch-up-worker-skill
description: 当工作追踪需要把已验证实现事实追平到正确文档层，减少后续开发引用过期上下文时，使用这个技能。
---

# 文档追平 Worker 技能

## 概览

本技能是 Harness 执行平面的文档追平 worker。它负责在每个 worktrack 的实现或验证事实稳定后，把事实同步到正确的长期文档层，减少后续开发因为引用旧文档、旧计数、旧路径或旧操作流程导致的错误。

本技能只追平已经验证的事实；写入 `docs/` 的内容仅限已验证事实；推测、计划或未通过验证的中间结论必须在输出中显式暴露并标记为待验证，留待后续验证通过后再追平。本技能的输出是文档基线对齐；设计、review、gate 或 repo-goal 变更必须路由到对应专用技能。

它也负责 `version fact sync`：当 package 版本、approval lock、CLI 版本输出、npm dist-tag、registry artifact 或 GitHub Release 事实发生变化时，把已验证版本事实同步到 release/channel/testing/usage 文档，并明确哪些入口不需要更新。

## 何时使用

当满足以下任一条件时使用：

- 当前 worktrack 已改变 operator-facing 行为、部署流程、验证命令、skill set、目录结构或治理规则
- 当前 worktrack 改变 package version、release approval lock、publish workflow、dist-tag、registry artifact、CLI `--version` 输出或 GitHub Release 事实
- publish workflow 成功后，需要把 npm registry 的 `latest` / `next` / `canary`、published version、`gitHead` 和 tarball 事实写回治理文档
- 实现已通过匹配验证，但长期文档仍引用旧路径、旧数量、旧命令或旧边界
- closeout 前需要确认文档是否与已验证事实一致
- 一个任务完成后需要为后续 worktrack 拉平上下文基线

不适用于：

- 写未验证的设计愿景
- 把研究草稿直接升格为长期真相
- 大范围改写 docs 叙事结构
- 替 `repo-change-goal-skill` 修改 Repo 级目标
- 替 `gate-skill` 做最终放行判断

## 输入约定

调用本技能时，任务 Prompt 至少应包含：

- `已验证事实`
- `触及实现或配置`
- `可能过期的文档范围`
- `应同步的 truth layer`
- `不应同步的内容`
- `验证证据`
- `完成信号`

如果任务是 `version fact sync`，Prompt 还应包含：

- `source version facts`：root/package `package.json`、approval lock、CLI `--version`、release tag
- `vcs tracking facts`：git branch、commit SHA、tag、remote ref
- `published version facts`：`npm view servo-installer dist-tags --json`，以及相关 `npm view servo-installer@<tag-or-version> version gitHead dist.tarball --json`
- `release evidence`：GitHub Release、publish workflow run、npx/package smoke 结果
- `doc update decision`：哪些根入口、governance、testing、usage-help 文档需要更新，哪些不需要更新及理由

默认 truth layer：

- 项目维护规则、governance、deploy、usage-help 写入 `docs/project-maintenance/`
- Harness doctrine、workflow family、artifact 与 adjacent-system 合同写入 `docs/harness/`
- 可执行合同写入 `product/` 或 `toolchain/`
- 长期事实的写入目标仅限 `docs/`、`product/` 和 `toolchain/`；长期事实写入 `.agents/`、`.claude/`、`.nav/` 的行为必须返回 blocked

## 工作流

1. 读取任务 Prompt、当前 diff 和验证证据，提取已验证事实。
2. 定位最小文档范围，优先更新承接层正文和最近入口页。
3. 查找旧路径、旧数量、旧命令、旧行为描述和旧准入条件。
4. 只写入已验证事实；对未验证事项保留为待办或不写入长期文档。
5. 如果涉及版本事实，先区分 `source version`、`published version` 和 `docs freshness`，再更新对应文档；version fact 的输出只能映射到对应的权威来源：本地 candidate 只能出现在 source version 字段中，registry artifact 只能出现在 published version 字段中，registry fact 只能写入已复核的页面；把本地 candidate 写成 registry artifact 或把 registry fact 写进未复核页面的行为必须返回 blocked。
6. 更新文档 frontmatter 的 `updated` / `last_verified`，仅限本轮实际复核过的文档。
7. 运行与文档和治理面匹配的检查。
8. 返回文档追平报告，不输出 gate 判定。

## Version Fact Sync

版本事实同步是本技能的专用模式，触发时机固定在这些节点：

- `harness entry observation`：`harness-skill` 启动一轮控制回路时，如发现 package/release/VCS 文档事实与当前代码或 registry 证据可能不一致，先记录 freshness risk，并在不阻塞主流程的前提下排入文档追平任务。
- `pre-publish readiness`：approval lock 或 package version 变更后，publish 前确认 root README、release channel、pre-publish、testing/usage docs 没有指向旧 selector 或旧行为。
- `post-publish verification`：publish workflow 成功并完成 registry 查询后，更新 registry fact、dist-tag、published version、`gitHead`、tarball URL 和后续 immutable version 约束。
- `post-smoke closeout`：registry npx / local `.tgz` smoke 通过后，必要时更新 testing docs 的 selector、命令矩阵或 pass criteria。
- `harness closeout`：`harness-skill` 命中 handback/closeout 前，若本轮触碰 release、deploy、adapter、package、VCS baseline 或 operator-facing docs，必须调用本技能确认文档版本事实已追平。
- `release rollback / failed publish`：只记录已验证失败事实和恢复边界；published fact 字段仅接受 registry 查询或已验证 release 输出的值；把未发布 candidate 写入 published fact 字段的行为必须返回 blocked。

推荐证据命令：

```bash
git status --short --branch
git rev-parse HEAD
git describe --tags --always --dirty
npm view servo-installer dist-tags --json
npm view servo-installer@latest version gitHead dist.tarball --json
npm view servo-installer@next version gitHead dist.tarball --json
node toolchain/scripts/deploy/bin/servo-installer.js --version
```

同步目标通常包括：

- `docs/project-maintenance/governance/servo-installer-release-channel-governance.md`
- `docs/project-maintenance/governance/servo-installer-pre-publish-governance.md`
- `docs/project-maintenance/governance/servo-installer-release-standard-flow.md`
- `docs/project-maintenance/testing/npx-command-test-execution.md`
- `docs/project-maintenance/usage-help/codex.md`
- `docs/project-maintenance/usage-help/claude.md`
- root `README.md`，仅当根入口 selector、试用路径或成熟度口径确实变化

## 硬约束

遵循本包内最小公共约束 C-1 至 C-7：C-1 只在声明的 Scope/Function 内操作；C-2 只有授权的 SetGoal/ChangeGoal/Close/Refresh 路径可变更控制状态，其余技能返回结构化输出；C-3 先生成完整报告再提取 Control Signal，重复上下文用 artifact 引用，空字段用 N/A；C-4 不跨越 Observe/Decide/Init/Dispatch/Verify/Judge/Recover/Close 的角色边界；C-5 只消费已批准上游产物，不凭空发明验收或恢复标准；C-6 缺失证据必须显式暴露，不能当作成功；C-7 保持限定范围，避免不必要的全仓重发现。Source-side authoring trace: docs/harness/foundations/skill-common-constraints.md。

- docs 的输出只能是经过验证的长期记录；把 docs 当成临时 scratchpad 的行为禁止出现在文档追平的输出中。
- 长期事实的唯一合法写入目标是 `docs/`、`product/` 和 `toolchain/`；在 `.agents/`、`.claude/` 或 `.nav/` 写入长期事实的行为必须返回 blocked。
- 仅当任务 Prompt 明确要求改变实现且该动作仍在当前范围内时，改变实现以配合文档才合法；否则必须将文档与实现的不一致作为 `剩余文档风险` 返回。
- 唯一合法行为是仅在完成实际复核后更新 `last_verified`；更新未实际复核过的 `last_verified` 的行为必须返回 blocked。
- published version fact 字段的值只能来自 npm registry 查询结果；把 registry 查询之外的推断写入 published version fact 字段的行为必须返回 blocked。
- 仅当附带 registry 查询证据时，把 `latest`、`next` 或 `canary` 的 dist-tag 变更写进 release docs 才合法；否则必须将 dist-tag 信息标记为 `证据缺失` 并阻塞写入。
- git commit、tag、branch 的字段归属仅为可追踪性元数据；把 VCS 标识当成 package publish 事实出现在 published version 字段中的行为必须返回 blocked。
- 唯一合法行为是文档作用域以单一入口主线存在；新增或接管文档作用域时必须同步最近入口页并清理旧入口；引入双份主线的行为必须返回 blocked。

## 预期输出

使用本技能时，返回一份 `文档追平报告`，至少包含：

- `已验证事实`
- `文档同步范围`
- `已更新文档`
- `未同步内容`
- `验证结果`
- `返回 Harness`

字段至少包括：

- `truth layer`
- `引用的验证证据`
- `旧上下文清理`
- `version fact sync`（如适用：source version、published version、VCS tracking facts、docs freshness、未更新文档及理由）
- `剩余文档风险`
- `建议下一动作`

## 资源

使用当前 worktrack 的实现 diff、验证命令输出、`AGENTS.md`、`docs/README.md`、`docs/project-maintenance/README.md`、`docs/harness/README.md` 和相关承接层文档作为输入。
