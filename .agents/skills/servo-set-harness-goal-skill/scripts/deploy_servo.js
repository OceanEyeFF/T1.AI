#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const SKILL_ROOT = path.resolve(__dirname, "..");
const DEFAULT_AW_DIRNAME = ".servo";
const DEFAULT_PROFILE = "full-deploy-bootstrap";
const DEFAULT_CLAUDE_SKILL_ROOT = path.join(".claude", "skills");
const DEFAULT_CLAUDE_SKILL_NAME = "servo-set-harness-goal-skill";
const SKILL_PACKAGE_EXCLUDED_NAMES = new Set([
  ".git",
  "__pycache__",
  ".pytest_cache",
  "aw.marker",
  "payload.json",
]);

const KEYED_LINE_PATTERN = /^(\s*)- ([a-z0-9_]+):\s*(.*)$/;
const CHECKBOX_LINE_PATTERN = /^(\d+)\. \[ \]\s*$/;
const HEADING_PATTERN = /^(#{1,6})\s+(.*?)\s*$/;

class DeployAwError extends Error {
  constructor(message) {
    super(message);
    this.name = "DeployAwError";
  }
}

function templateSpec(spec) {
  return {
    injectInstanceNote: true,
    requiredNestedKeyedFieldsBySection: {},
    ...spec,
  };
}

const TEMPLATE_SPECS = {
  "control-state": templateSpec({
    templateId: "control-state",
    sourceRelpath: "assets/control-state.md",
    outputRelpath: "control-state.md",
    artifactType: "control-state",
    title: "Harness Control State",
    instanceNote:
      "这是 `.servo/control-state.md` 的运行样例，用来维护当前 Harness supervisor 的控制面状态，不要把业务真相写进来。",
    requiredSections: [
      "Metadata",
      "Current Control Level",
      "Active Worktrack",
      "Baseline Branch",
      "Current Next Action",
      "Linked Formal Documents",
      "Approval Boundary",
      "User-Defined Servo Controls",
      "Continuation Authority",
      "Handback Guard",
      "Baseline Traceability",
      "Autonomy Ledger",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["updated", "owner"],
      "Current Control Level": ["repo_scope", "worktrack_scope"],
      "Linked Formal Documents": [
        "repo_snapshot",
        "repo_analysis",
        "worktrack_contract",
        "plan_task_queue",
        "gate_evidence",
      ],
      "Approval Boundary": ["needs_programmer_approval", "reason"],
      "User-Defined Servo Controls": [
        "continuous_progression_permission",
        "per_milestone_automatic_worktrack_budget",
        "default_servo_work_branch",
        "protected_branch_policy",
        "branch_mutation_policy",
        "auto_maintained_runtime_facts_not_asked",
      ],
      // Guard terms for auto-maintained runtime facts that initialization must not ask:
      // runtime facts, active_milestone, active_worktrack, observed_git_hash,
      // progress_counters, runtime_dispatch_profile, latest_observed_checkpoint,
      // last_doc_catch_up_checkpoint, milestone_pipeline_summary.
      "Baseline Traceability": [
        "last_verified_checkpoint",
        "latest_observed_checkpoint",
        "last_doc_catch_up_checkpoint",
        "checkpoint_type",
        "checkpoint_ref",
        "verified_at",
        "if_no_commit_reason",
        "alternative_traceability",
      ],
    },
  }),
  "goal-charter": templateSpec({
    templateId: "goal-charter",
    sourceRelpath: "assets/goal-charter.md",
    outputRelpath: "goal-charter.md",
    artifactType: "goal-charter",
    title: "Repo Goal / Charter",
    instanceNote:
      "这是 `.servo/goal-charter.md` 的运行样例，用来记录当前 repo 的长期目标和方向。Source-side authoring trace: docs/harness/artifact/repo/goal-charter.md。",
    requiredSections: [
      "Metadata",
      "Project Vision",
      "Core Product Goals",
      "Technical Direction",
      "Engineering Node Map",
      "Success Criteria",
      "System Invariants",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["repo", "owner", "updated", "status"],
      "Engineering Node Map": ["type", "if_worktrack_interrupted", "if_no_merge"],
    },
    requiredNestedKeyedFieldsBySection: {
      "Engineering Node Map": [
        "expected_count",
        "merge_required",
        "baseline_form",
        "gate_criteria",
        "if_interrupted_strategy",
      ],
    },
  }),
  "repo-snapshot-status": templateSpec({
    templateId: "repo-snapshot-status",
    sourceRelpath: "assets/repo/snapshot-status.md",
    outputRelpath: "repo/snapshot-status.md",
    artifactType: "repo-snapshot-status",
    title: "Repo Snapshot / Status",
    instanceNote:
      "这是 `.servo/repo/snapshot-status.md` 的运行样例，用来记录当前 repo 的慢变量观测面。Source-side authoring trace: docs/harness/artifact/repo/snapshot-status.md。",
    requiredSections: [
      "Metadata",
      "Mainline Status",
      "Architecture And Module Map",
      "Active Branches And Purpose",
      "Governance Status",
      "Known Issues And Risks",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["repo", "baseline_branch", "updated", "status"],
      "Mainline Status": [
        "baseline_branch",
        "last_verified_checkpoint",
        "checkpoint_ref",
        "checkpoint_type",
      ],
    },
  }),
  "repo-analysis": templateSpec({
    templateId: "repo-analysis",
    sourceRelpath: "assets/repo/analysis.md",
    outputRelpath: "repo/analysis.md",
    artifactType: "repo-analysis",
    title: "Repo Analysis",
    instanceNote:
      "这是 `.servo/repo/analysis.md` 的运行样例，用来记录 RepoScope 的阶段性分析与优先级判断。它是决策支撑 artifact，不是 goal truth。",
    requiredSections: [
      "Metadata",
      "Facts",
      "Inferences",
      "Unknowns",
      "Main Contradiction",
      "Priority Judgment",
      "Routing Projection",
      "Writeback Eligibility",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["repo", "baseline_branch", "baseline_ref", "updated", "analysis_status"],
      "Main Contradiction": ["current_main_contradiction", "main_aspect"],
      "Priority Judgment": [
        "current_highest_priority",
        "long_term_highest_priority",
        "do_not_do_now",
      ],
      "Routing Projection": [
        "recommended_repo_action",
        "recommended_next_route",
        "suggested_node_type",
        "continuation_ready",
        "continuation_blockers",
      ],
      "Writeback Eligibility": ["writeback_eligibility"],
    },
  }),
  "repo-discovery-input": templateSpec({
    templateId: "repo-discovery-input",
    sourceRelpath: "assets/repo/discovery-input.md",
    outputRelpath: "repo/discovery-input.md",
    artifactType: "repo-discovery-input",
    title: "Repo Discovery Input",
    instanceNote:
      "这是 `.servo/repo/discovery-input.md` 的运行样例，用于 Existing Code Project Adoption 模式下记录既有代码库的只读事实输入。它不是 goal truth。",
    requiredSections: [
      "Metadata",
      "Source Materials",
      "Repository Facts",
      "Architecture And Module Inventory",
      "Build, Test, And Runtime Signals",
      "Governance And Documentation Signals",
      "Risks And Unknowns",
      "Candidate Goal Signals",
      "Confirmation Questions",
      "Downstream Mapping Notes",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["repo", "owner", "updated", "adoption_mode", "source_scope", "generated_by"],
      "Source Materials": [
        "repository_path",
        "baseline_branch",
        "current_branch",
        "current_commit",
        "working_tree_state",
        "user_provided_context",
        "inspected_paths",
        "skipped_paths",
      ],
      "Repository Facts": [
        "primary_language_or_stack",
        "package_or_build_system",
        "runtime_entrypoints",
        "test_entrypoints",
        "deploy_or_release_entrypoints",
        "configuration_files",
      ],
      "Build, Test, And Runtime Signals": [
        "build_commands_seen",
        "test_commands_seen",
        "runtime_commands_seen",
        "commands_not_run",
      ],
      "Governance And Documentation Signals": [
        "existing_docs",
        "agent_or_harness_instructions",
        "ownership_or_layering_rules",
        "review_or_verify_rules",
        "known_policy_constraints",
      ],
      "Downstream Mapping Notes": [
        "goal_charter_inputs",
        "snapshot_status_inputs",
        "control_state_links",
      ],
    },
  }),
  "repo-temporary-understanding": templateSpec({
    templateId: "repo-temporary-understanding",
    sourceRelpath: "assets/repo/temporary-understanding.md",
    outputRelpath: "repo/temporary-understanding.md",
    artifactType: "repo-temporary-understanding",
    title: "Temporary Understanding",
    instanceNote:
      "这是 `.servo/repo/temporary-understanding.md` 的运行样例，用于弱文档 adoption / onboarding 场景记录 temporary-inferred 理解。它是 runtime evidence, not Goal Charter truth；promotion 需要 programmer confirmation 或 verified evidence，并记录 token-cost tradeoff。",
    requiredSections: [
      "Metadata",
      "Mode Selection",
      "Discovery Coverage",
      "Observed Facts",
      "Inferred Purpose",
      "Operational Purpose",
      "Known Risks",
      "Unknowns",
      "Confirmation Questions",
      "Promotion Plan",
      "Truth Boundary",
      "Handoff",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: [
        "repo",
        "owner",
        "updated",
        "adoption_mode",
        "temporary_understanding",
        "understanding_mode",
        "token_budget_note",
        "source_scope",
        "generated_by",
        "truth_status",
        "promotion_allowed",
      ],
      "Mode Selection": [
        "selected_mode",
        "selection_reason",
        "lightweight_mode",
        "full_mode",
        "recommended_next_mode",
      ],
      "Observed Facts": ["observed_facts"],
      "Inferred Purpose": [
        "inferred_purpose",
        "confidence",
        "evidence_refs",
        "competing_interpretations",
      ],
      "Operational Purpose": [
        "operational_purpose",
        "safe_first_slice",
        "allowed_until_confirmed",
        "not_allowed_until_confirmed",
      ],
      "Known Risks": [
        "known_risks",
        "high_risk_paths",
        "stale_or_missing_docs",
        "verification_risks",
      ],
      Unknowns: ["unknowns", "blockers", "assumptions_that_must_not_be_promoted"],
      "Confirmation Questions": [
        "confirmation_questions",
        "recommended_answers",
        "impact_if_wrong",
        "programmer_decisions_required",
      ],
      "Promotion Plan": [
        "promotion_plan",
        "promotable_now",
        "needs_programmer_confirmation",
        "needs_verified_evidence",
        "forbidden_promotion_targets",
      ],
      "Truth Boundary": [
        "truth_boundary",
        "long_lived_truth_targets",
        "runtime_evidence_targets",
        "goal_charter_promotion_rule",
        "docs_promotion_rule",
      ],
      Handoff: ["recommended_next_route", "handoff_summary", "required_context_for_next_step"],
    },
  }),
  "repo-complex-project-entry-gate": templateSpec({
    templateId: "repo-complex-project-entry-gate",
    sourceRelpath: "assets/repo/complex-project-entry-gate.md",
    outputRelpath: "repo/complex-project-entry-gate.md",
    artifactType: "complex-project-entry-gate",
    title: "Complex Project Entry Gate",
    instanceNote:
      "这是 `.servo/repo/complex-project-entry-gate.md` 的运行样例，用于 repo init / existing-code-adoption 期间记录 complex_project_entry_gate。它是 Milestone-side blocking gate, not fixed heavy mode；scanner output is evidence, not verdict。",
    requiredSections: [
      "Metadata",
      "Trigger Signals",
      "Project Understanding",
      "Operator Safety Policy",
      "Dialog Review Questions",
      "Boundary Before Confirmation",
      "Verdict",
      "Handoff",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: [
        "repo",
        "owner",
        "updated",
        "adoption_mode",
        "gate_id",
        "complex_project_entry_gate",
        "target_repo",
        "target_milestone_id",
        "trigger_source",
        "generated_by",
        "gate_truth_status",
      ],
      "Trigger Signals": [
        "trigger_conditions",
        "scanner_evidence_ref",
        "scanner_command",
        "scanner_output_role",
        "complexity_signals",
        "thresholds",
        "confidence",
      ],
      "Project Understanding": [
        "project_understanding",
        "service_workflow_boundary",
        "core_directories",
        "generated_or_low_trust_paths",
        "verification_authority",
        "unknowns",
      ],
      "Operator Safety Policy": ["operator_safety_policy"],
      "Dialog Review Questions": ["dialog_review_questions"],
      "Boundary Before Confirmation": [
        "allowed_before_confirmation",
        "forbidden_before_confirmation",
        "not_fixed_heavy_mode",
      ],
      Verdict: [
        "entry_verdict",
        "milestone_blocking_decision",
        "reinforcement_milestone_recommendation",
        "evidence_refs",
      ],
      Handoff: [
        "recommended_next_route",
        "handoff_to_init_milestone",
        "handoff_summary",
      ],
    },
    requiredNestedKeyedFieldsBySection: {
      "Trigger Signals": [
        "scanner_command_alternatives",
      ],
      "Operator Safety Policy": [
        "docker_compose_permission",
        "database_migration_permission",
        "deploy_network_permission",
        "destructive_cleanup_permission",
        "secrets_policy",
        "protected_paths",
        "protected_branches",
        "allowed_high_risk_command_modes",
      ],
      "Dialog Review Questions": [
        "id",
        "question",
        "why_it_matters",
        "recommended_answer",
        "tradeoff",
        "blocks_ready",
      ],
      Verdict: [
        "needed",
        "recommendation_status",
        "recommendation_type",
        "suggested_title",
        "suggested_purpose",
        "recommendation_reason",
        "temporary_understanding_ref",
        "confirmation_required",
        "blocks_implementation_until_resolved",
      ],
    },
  }),
  "worktrack-contract": templateSpec({
    templateId: "worktrack-contract",
    sourceRelpath: "assets/worktrack/contract.md",
    outputRelpath: "worktrack/contract.md",
    artifactType: "worktrack-contract",
    title: "Worktrack Contract",
    instanceNote:
      "这是 `.servo/worktrack/contract.md` 的运行样例，用来填写单个 worktrack 的局部状态转移合同。Source-side authoring trace: docs/harness/artifact/worktrack/contract.md。",
    requiredSections: [
      "Metadata",
      "Node Type",
      "Task Goal",
      "Scope",
      "Non-Goals",
      "Impacted Modules",
      "Planned Next State",
      "Acceptance Criteria",
      "Constraints",
      "Verification Requirements",
      "Rollback Conditions",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: [
        "worktrack_id",
        "branch",
        "baseline_branch",
        "baseline_ref",
        "owner",
        "updated",
        "contract_status",
      ],
      "Node Type": [
        "type",
        "source_from_goal_charter",
        "baseline_form",
        "merge_required",
        "gate_criteria",
        "if_interrupted_strategy",
      ],
    },
  }),
  "worktrack-plan-task-queue": templateSpec({
    templateId: "worktrack-plan-task-queue",
    sourceRelpath: "assets/worktrack/plan-task-queue.md",
    outputRelpath: "worktrack/plan-task-queue.md",
    artifactType: "worktrack-plan-task-queue",
    title: "Plan / Task Queue",
    instanceNote:
      "这是 `.servo/worktrack/plan-task-queue.md` 的运行样例，用来把 worktrack contract 展开成当前执行队列。",
    requiredSections: [
      "Metadata",
      "Task Window",
      "Task List",
      "Execution Order Notes",
      "Dependencies",
      "Current Blockers",
      "Current Next Action",
      "Dispatch Handoff Packet",
      "Readiness",
      "Notes",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["worktrack_id", "updated", "current_phase", "contract_ref", "queue_status"],
      "Task Window": [
        "task_window_id",
        "window_boundary",
        "window_status",
        "continuation_allowed",
        "continuation_stop_reason",
      ],
      "Current Next Action": [
        "selected_next_action_id",
        "selected_next_action",
        "selection_reason",
        "selected_task_acceptance",
        "selected_task_risk_level",
        "selected_task_stop_condition",
      ],
      "Dispatch Handoff Packet": [
        "dispatch_handoff_packet",
        "task",
        "task_id",
        "goal_for_this_round",
        "node_type",
        "gate_criteria_for_this_round",
        "baseline_policy",
        "constraints_for_this_round",
        "acceptance_criteria_for_this_round",
        "verification_requirements",
        "risk_level",
        "stop_condition",
        "runtime_dispatch_mode",
        "shared_fact_pack",
        "context_budget",
        "done_signal",
        "required_context",
        "return_to_schedule_if",
      ],
      Readiness: ["dispatch_packet_ready", "recommended_next_route"],
    },
  }),
  "worktrack-gate-evidence": templateSpec({
    templateId: "worktrack-gate-evidence",
    sourceRelpath: "assets/worktrack/gate-evidence.md",
    outputRelpath: "worktrack/gate-evidence.md",
    artifactType: "worktrack-gate-evidence",
    title: "Gate Evidence",
    instanceNote:
      "这是 `.servo/worktrack/gate-evidence.md` 的运行样例，用来记录当前 worktrack 的 gate 证据与裁决依据。",
    requiredSections: [
      "Metadata",
      "Review Lane",
      "Validation Lane",
      "Policy Lane",
      "Evidence Assessment",
      "Per-Surface Verdicts",
      "Recommended Next Route",
      "Follow-up Actions",
    ],
    requiredKeyedFieldsBySection: {
      Metadata: ["worktrack_id", "updated", "gate_round", "required_evidence_lanes"],
      "Review Lane": [
        "input_ref",
        "freshness",
        "review_subagent_lanes",
        "four_lane_dispatch_status",
        "static_semantic_review",
        "test_review",
        "project_security_review",
        "complexity_performance_review",
        "four_lane_fallback_reason",
        "confidence",
        "missing_evidence",
        "residual_risks",
        "upstream_constraint_signals",
        "low_severity_absorption_applied",
        "ready_for_gate",
      ],
      "Validation Lane": [
        "input_ref",
        "freshness",
        "confidence",
        "missing_evidence",
        "residual_risks",
        "upstream_constraint_signals",
        "low_severity_absorption_applied",
        "ready_for_gate",
      ],
      "Policy Lane": [
        "input_ref",
        "freshness",
        "confidence",
        "missing_evidence",
        "residual_risks",
        "upstream_constraint_signals",
        "low_severity_absorption_applied",
        "ready_for_gate",
      ],
      "Evidence Assessment": [
        "node_type",
        "node_type_source",
        "applied_gate_criteria",
        "fallback_used",
        "overall_confidence",
        "overall_confidence_reason",
        "freshness_blockers",
      ],
      "Per-Surface Verdicts": [
        "implementation_surface",
        "validation_surface",
        "policy_surface",
        "low_severity_absorption_reason",
      ],
      "Recommended Next Route": [
        "allowed_next_routes",
        "recommended_next_route",
        "approval_required",
        "approval_scope",
        "approval_reason",
        "needs_programmer_approval",
        "why",
      ],
    },
  }),
};

const STATIC_ASSET_SPECS = {
  "template-readme": {
    assetId: "template-readme",
    sourceRelpath: "assets/template/README.md",
    outputRelpath: "template/README.md",
  },
  "goal-charter-template": {
    assetId: "goal-charter-template",
    sourceRelpath: "assets/template/goal-charter.template.md",
    outputRelpath: "template/goal-charter.template.md",
  },
  "repo-readme": {
    assetId: "repo-readme",
    sourceRelpath: "assets/repo/README.md",
    outputRelpath: "repo/README.md",
  },
  "worktrack-readme": {
    assetId: "worktrack-readme",
    sourceRelpath: "assets/worktrack/README.md",
    outputRelpath: "worktrack/README.md",
  },
};

const PROFILE_TEMPLATES = {
  [DEFAULT_PROFILE]: [
    "control-state",
    "goal-charter",
    "repo-snapshot-status",
    "repo-analysis",
    "worktrack-contract",
    "worktrack-plan-task-queue",
    "worktrack-gate-evidence",
  ],
};

const PROFILE_STATIC_ASSETS = {
  [DEFAULT_PROFILE]: [
    "template-readme",
    "goal-charter-template",
    "repo-readme",
    "worktrack-readme",
  ],
};

const LINKED_PATH_FIELDS = {
  repo_snapshot: "repo-snapshot-status",
  repo_analysis: "repo-analysis",
  temporary_understanding: "repo-temporary-understanding",
  complex_project_entry_gate: "repo-complex-project-entry-gate",
  worktrack_contract: "worktrack-contract",
  plan_task_queue: "worktrack-plan-task-queue",
  gate_evidence: "worktrack-gate-evidence",
};

const SECTION_VALUE_FIELDS = {
  "Active Worktrack": "worktrack_id",
  "Baseline Branch": "baseline_branch",
};

function sourcePath(spec) {
  return path.join(SKILL_ROOT, spec.sourceRelpath);
}

function sourceDisplayPath(spec) {
  return path.join(path.basename(SKILL_ROOT), spec.sourceRelpath).split(path.sep).join("/");
}

function slugify(label) {
  const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  return slug || "value";
}

function placeholder(name) {
  return `TODO(${slugify(name)})`;
}

function usage() {
  return [
    "Generate and validate `.servo` bootstrap artifacts from set-harness-goal-skill-owned assets.",
    "",
    "Usage:",
    "  node deploy_servo.js list [--json]",
    "  node deploy_servo.js validate [--profile NAME | --template ID... | --all]",
    "  node deploy_servo.js generate [--deploy-path PATH] [--profile NAME | --template ID... | --all] [options]",
    "  node deploy_servo.js install-claude-skill [--deploy-path PATH] [options]",
    "",
    "Examples:",
    "  node deploy_servo.js validate",
    "  node deploy_servo.js generate --deploy-path \"$DEPLOY_PATH\" --owner servo-kernel",
    "  node deploy_servo.js generate --deploy-path \"$DEPLOY_PATH\" --adoption-mode existing-code-adoption --weak-doc-onboarding",
    "  node deploy_servo.js generate --deploy-path \"$DEPLOY_PATH\" --adoption-mode existing-code-adoption --complex-project-entry-gate",
    "  node deploy_servo.js generate --deploy-path \"$DEPLOY_PATH\" --install-claude-skill",
    "  node deploy_servo.js install-claude-skill --deploy-path \"$DEPLOY_PATH\"",
  ].join("\n");
}

function todayLocalIsoDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseArgs(argv) {
  if (argv.includes("--help") || argv.includes("-h")) {
    console.log(usage());
    process.exit(0);
  }
  const mode = argv[0];
  if (!mode || !["list", "validate", "generate", "install-claude-skill"].includes(mode)) {
    throw new DeployAwError("missing or unsupported mode: expected list, validate, generate, or install-claude-skill");
  }
  const args = {
    mode,
    json: false,
    profile: undefined,
    template: [],
    all: false,
    deployPath: undefined,
    force: false,
    dryRun: false,
    installClaudeSkill: false,
    noStaticAssets: false,
    adoptionMode: "new-goal-initialization",
    weakDocOnboarding: false,
    complexProjectEntryGate: false,
    repo: undefined,
    owner: undefined,
    updated: todayLocalIsoDate(),
    baselineBranch: undefined,
    worktrackId: undefined,
    branch: undefined,
    claudeRoot: undefined,
  };

  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    const nextValue = () => {
      index += 1;
      if (index >= argv.length) {
        throw new DeployAwError(`missing value for ${token}`);
      }
      return argv[index];
    };
    if (token === "--json") args.json = true;
    else if (token === "--profile") args.profile = nextValue();
    else if (token === "--template") args.template.push(nextValue());
    else if (token === "--all") args.all = true;
    else if (token === "--deploy-path") args.deployPath = nextValue();
    else if (token === "--force") args.force = true;
    else if (token === "--dry-run") args.dryRun = true;
    else if (token === "--install-claude-skill") args.installClaudeSkill = true;
    else if (token === "--no-static-assets") args.noStaticAssets = true;
    else if (token === "--adoption-mode") args.adoptionMode = nextValue();
    else if (token === "--weak-doc-onboarding") args.weakDocOnboarding = true;
    else if (token === "--complex-project-entry-gate") args.complexProjectEntryGate = true;
    else if (token === "--repo") args.repo = nextValue();
    else if (token === "--owner") args.owner = nextValue();
    else if (token === "--updated") args.updated = nextValue();
    else if (token === "--baseline-branch") args.baselineBranch = nextValue();
    else if (token === "--worktrack-id") args.worktrackId = nextValue();
    else if (token === "--branch") args.branch = nextValue();
    else if (token === "--claude-root") args.claudeRoot = nextValue();
    else throw new DeployAwError(`unsupported option: ${token}`);
  }

  if (args.profile && !PROFILE_TEMPLATES[args.profile]) {
    throw new DeployAwError(`unknown profile: ${args.profile}`);
  }
  for (const templateId of args.template) {
    if (!TEMPLATE_SPECS[templateId]) {
      throw new DeployAwError(`unknown template: ${templateId}`);
    }
  }
  if (!["new-goal-initialization", "existing-code-adoption"].includes(args.adoptionMode)) {
    throw new DeployAwError(`unsupported adoption mode: ${args.adoptionMode}`);
  }
  if (args.weakDocOnboarding && args.adoptionMode !== "existing-code-adoption") {
    throw new DeployAwError("--weak-doc-onboarding requires --adoption-mode existing-code-adoption");
  }
  if (args.complexProjectEntryGate && args.adoptionMode !== "existing-code-adoption") {
    throw new DeployAwError("--complex-project-entry-gate requires --adoption-mode existing-code-adoption");
  }
  return args;
}

function resolveSelectedSpecs(args) {
  let selectionModes = 0;
  if (args.profile) selectionModes += 1;
  if (args.template.length) selectionModes += 1;
  if (args.all) selectionModes += 1;
  if (selectionModes > 1) {
    throw new DeployAwError("choose only one of --profile, --template, or --all");
  }

  let templateIds;
  if (args.template.length) templateIds = [...args.template];
  else if (args.profile) templateIds = [...PROFILE_TEMPLATES[args.profile]];
  else if (args.all) templateIds = Object.keys(TEMPLATE_SPECS);
  else if (args.mode === "generate") templateIds = [...PROFILE_TEMPLATES[DEFAULT_PROFILE]];
  else templateIds = Object.keys(TEMPLATE_SPECS);

  if (
    args.mode === "generate" &&
    args.adoptionMode === "existing-code-adoption" &&
    !args.template.length &&
    !templateIds.includes("repo-discovery-input")
  ) {
    const insertAt = templateIds.indexOf("repo-snapshot-status");
    templateIds.splice(insertAt >= 0 ? insertAt : 0, 0, "repo-discovery-input");
  }
  if (
    args.mode === "generate" &&
    args.adoptionMode === "existing-code-adoption" &&
    args.weakDocOnboarding &&
    !args.template.length &&
    !templateIds.includes("repo-temporary-understanding")
  ) {
    const insertAt = templateIds.indexOf("repo-analysis");
    templateIds.splice(insertAt >= 0 ? insertAt : templateIds.length, 0, "repo-temporary-understanding");
  }
  if (
    args.mode === "generate" &&
    args.adoptionMode === "existing-code-adoption" &&
    (args.weakDocOnboarding || args.complexProjectEntryGate) &&
    !args.template.length &&
    !templateIds.includes("repo-complex-project-entry-gate")
  ) {
    const insertAt = templateIds.indexOf("repo-analysis");
    templateIds.splice(insertAt >= 0 ? insertAt : templateIds.length, 0, "repo-complex-project-entry-gate");
  }

  const seen = new Set();
  const selected = [];
  for (const templateId of templateIds) {
    if (seen.has(templateId)) continue;
    seen.add(templateId);
    selected.push(TEMPLATE_SPECS[templateId]);
  }
  return selected;
}

function resolveStaticAssetSpecs(args) {
  if (args.noStaticAssets || args.template.length) return [];
  const profile = args.profile || DEFAULT_PROFILE;
  return (PROFILE_STATIC_ASSETS[profile] || []).map((assetId) => STATIC_ASSET_SPECS[assetId]);
}

function resolveDeployPath(args) {
  const rawValue = args.deployPath || process.env.DEPLOY_PATH;
  if (!rawValue) {
    throw new DeployAwError("missing deploy path: pass --deploy-path <repo-or-worktree-root> or set DEPLOY_PATH");
  }
  const deployPath = path.resolve(rawValue.replace(/^~/, process.env.HOME || "~"));
  if (!fs.existsSync(deployPath)) {
    throw new DeployAwError(`deploy path does not exist: ${deployPath}`);
  }
  if (!fs.statSync(deployPath).isDirectory()) {
    throw new DeployAwError(`deploy path must be a directory: ${deployPath}`);
  }
  return deployPath;
}

function runGitOutput(repoRoot, args) {
  const completed = spawnSync("git", ["-C", repoRoot, ...args], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  });
  if (completed.error || completed.status !== 0) return null;
  const value = completed.stdout.trim();
  return value || null;
}

function gitRefExists(repoRoot, ref) {
  const completed = spawnSync("git", ["-C", repoRoot, "show-ref", "--verify", "--quiet", ref], {
    stdio: "ignore",
  });
  return !completed.error && completed.status === 0;
}

function resolveBaselineBranch(args, deployPath) {
  if (args.baselineBranch && args.baselineBranch.trim()) return args.baselineBranch.trim();
  const envValue = (process.env.SERVO_BASELINE_BRANCH || "").trim();
  if (envValue) return envValue;

  const originHead = runGitOutput(deployPath, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"]);
  if (originHead) {
    const baseline = originHead.replace(/^origin\//, "").trim();
    if (baseline) return baseline;
  }

  const remoteCandidates = ["main", "master"].filter((branch) =>
    gitRefExists(deployPath, `refs/remotes/origin/${branch}`),
  );
  if (remoteCandidates.length === 1) return remoteCandidates[0];
  if (remoteCandidates.length > 1) {
    throw new DeployAwError("ambiguous remote baseline branches: both origin/main and origin/master exist; pass --baseline-branch");
  }

  const localCandidates = ["main", "master"].filter((branch) =>
    gitRefExists(deployPath, `refs/heads/${branch}`),
  );
  if (localCandidates.length === 1) return localCandidates[0];
  if (localCandidates.length > 1) {
    throw new DeployAwError("ambiguous local baseline branches: both main and master exist; pass --baseline-branch");
  }

  throw new DeployAwError(
    "unable to resolve baseline branch: pass --baseline-branch or set SERVO_BASELINE_BRANCH; origin/HEAD is unavailable and no unique main/master branch ref could verify a baseline",
  );
}

function parseTemplateStructure(text) {
  let heading = null;
  const sections = new Set();
  const keyedFieldsBySection = new Map();
  const nestedKeyedFieldsBySection = new Map();
  let currentSection = null;

  for (const line of text.split(/\r?\n/)) {
    const headingMatch = line.match(HEADING_PATTERN);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const title = headingMatch[2].trim();
      if (level === 1) {
        if (heading === null) heading = title;
        currentSection = null;
      } else if (level === 2) {
        currentSection = title;
        sections.add(title);
        if (!keyedFieldsBySection.has(title)) keyedFieldsBySection.set(title, new Set());
      }
      continue;
    }
    if (currentSection === null) continue;
    const keyedMatch = line.match(KEYED_LINE_PATTERN);
    if (!keyedMatch) continue;
    const target = keyedMatch[1] ? nestedKeyedFieldsBySection : keyedFieldsBySection;
    if (!target.has(currentSection)) target.set(currentSection, new Set());
    target.get(currentSection).add(keyedMatch[2]);
  }
  return { heading, sections, keyedFieldsBySection, nestedKeyedFieldsBySection };
}

function validateTemplateSource(spec) {
  const templatePath = sourcePath(spec);
  if (!fs.existsSync(templatePath) || !fs.statSync(templatePath).isFile()) {
    return [`missing template source: ${templatePath}`];
  }
  const text = fs.readFileSync(templatePath, "utf8");
  const parsed = parseTemplateStructure(text);
  const issues = [];
  if (parsed.heading !== spec.title) issues.push(`expected title '${spec.title}', got '${parsed.heading}'`);

  for (const section of spec.requiredSections) {
    if (!parsed.sections.has(section)) issues.push(`missing required section: ${section}`);
  }
  for (const [sectionName, requiredFields] of Object.entries(spec.requiredKeyedFieldsBySection)) {
    if (!parsed.sections.has(sectionName)) continue;
    const actualFields = parsed.keyedFieldsBySection.get(sectionName) || new Set();
    for (const fieldName of requiredFields) {
      if (!actualFields.has(fieldName)) issues.push(`missing keyed field in section ${sectionName}: ${fieldName}`);
    }
  }
  for (const [sectionName, requiredFields] of Object.entries(spec.requiredNestedKeyedFieldsBySection)) {
    if (!parsed.sections.has(sectionName)) continue;
    const actualFields = parsed.nestedKeyedFieldsBySection.get(sectionName) || new Set();
    for (const fieldName of requiredFields) {
      if (!actualFields.has(fieldName)) issues.push(`missing nested keyed field in section ${sectionName}: ${fieldName}`);
    }
  }
  return issues;
}

function validateStaticAssetSource(spec) {
  const assetPath = sourcePath(spec);
  if (!fs.existsSync(assetPath) || !fs.statSync(assetPath).isFile()) {
    return [`missing static asset source: ${assetPath}`];
  }
  if (spec.assetId !== "goal-charter-template") return [];

  const text = fs.readFileSync(assetPath, "utf8");
  const parsed = parseTemplateStructure(text);
  const issues = [];
  if (parsed.heading !== "Repo Goal / Charter Answer Template") {
    issues.push(`expected title 'Repo Goal / Charter Answer Template', got '${parsed.heading}'`);
  }
  for (const section of [
    "Metadata",
    "Project Vision",
    "Core Product Goals",
    "Technical Direction",
    "Engineering Node Map",
    "Success Criteria",
    "System Invariants",
    "Notes",
  ]) {
    if (!parsed.sections.has(section)) issues.push(`missing required section: ${section}`);
  }
  const engineeringFields = parsed.keyedFieldsBySection.get("Engineering Node Map") || new Set();
  for (const fieldName of ["type", "if_worktrack_interrupted", "if_no_merge"]) {
    if (!engineeringFields.has(fieldName)) issues.push(`missing keyed field in section Engineering Node Map: ${fieldName}`);
  }
  const nestedEngineeringFields = parsed.nestedKeyedFieldsBySection.get("Engineering Node Map") || new Set();
  for (const fieldName of [
    "expected_count",
    "merge_required",
    "baseline_form",
    "gate_criteria",
    "if_interrupted_strategy",
  ]) {
    if (!nestedEngineeringFields.has(fieldName)) {
      issues.push(`missing nested keyed field in section Engineering Node Map: ${fieldName}`);
    }
  }
  return issues;
}

function resolveKeyedValue(key, selectedTemplateIds, args) {
  const weakDocReinforcementNeeded = Boolean(args.weakDocOnboarding);
  const directValues = {
    repo: args.repo,
    owner: args.owner || placeholder("owner"),
    updated: args.updated,
    adoption_mode: args.adoptionMode,
    gate_id: "complex_project_entry_gate",
    complex_project_entry_gate: "complex_project_entry_gate",
    target_repo: args.deployPath || placeholder("target_repo"),
    target_milestone_id: placeholder("target_milestone_id"),
    trigger_source: "repo-init",
    trigger_conditions: "pending_observed_signal_review",
    understanding_mode: placeholder("lightweight_or_full"),
    token_budget_note: "lightweight is low-token and quick; full is deeper and may require a separate discovery milestone or worktrack",
    source_scope: placeholder("source_scope"),
    generated_by: "set-harness-goal-skill",
    truth_status: "temporary-inferred",
    gate_truth_status: "runtime-evidence",
    scanner_command: "PYTHONDONTWRITEBYTECODE=1 python3 .agents/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py --repo <repo> --json",
    scanner_command_alternatives: "PYTHONDONTWRITEBYTECODE=1 python3 .claude/skills/servo-set-harness-goal-skill/scripts/complexity_signal_scanner.py --repo <repo> --json",
    scanner_output_role: "scanner output is evidence, not verdict",
    docker_compose_permission: "pending_programmer_confirmation",
    database_migration_permission: "pending_programmer_confirmation",
    deploy_network_permission: "pending_programmer_confirmation",
    destructive_cleanup_permission: "pending_programmer_confirmation",
    secrets_policy: "pending_programmer_confirmation",
    protected_paths: "pending_programmer_confirmation",
    protected_branches: "pending_programmer_confirmation",
    allowed_high_risk_command_modes: "pending_programmer_confirmation",
    allowed_before_confirmation: "read_only_discovery_and_scanner_evidence_collection",
    forbidden_before_confirmation: "milestone_activation_worktrack_derivation_high_risk_commands_deploy_database_destructive_or_secret_operations",
    not_fixed_heavy_mode: "true",
    entry_verdict: "blocked",
    milestone_blocking_decision: "block_create, block_upsert, block_activate, block_derive_worktrack",
    reinforcement_milestone_recommendation: "structured_reinforcement_milestone_recommendation",
    needed: weakDocReinforcementNeeded ? "true" : "false",
    recommendation_status: weakDocReinforcementNeeded
      ? "pending_operator_review"
      : "not_needed",
    recommendation_type: weakDocReinforcementNeeded ? "project_understanding" : "N/A",
    suggested_title: weakDocReinforcementNeeded
      ? "Reinforcement Documentation / Project Understanding"
      : "N/A",
    suggested_purpose: weakDocReinforcementNeeded
      ? "Confirm repo purpose, core directories, verification authority, service boundaries, and safety policy before implementation-oriented Worktrack derivation."
      : "N/A",
    recommendation_reason: weakDocReinforcementNeeded
      ? "weak-doc or insufficient-understanding signals require programmer confirmation or verified evidence before implementation."
      : "explicit complex-project gate requested; reinforcement milestone is not required unless weak-doc or insufficient-understanding evidence is observed.",
    temporary_understanding_ref: selectedTemplateIds.has("repo-temporary-understanding")
      ? "temporary-understanding.md"
      : "N/A",
    confirmation_required: weakDocReinforcementNeeded ? "true" : "false",
    blocks_implementation_until_resolved: weakDocReinforcementNeeded ? "true" : "false",
    promotion_allowed: "false",
    repository_path: args.deployPath || placeholder("repository_path"),
    baseline_branch: args.baselineBranch || placeholder("baseline_branch"),
    baseline_ref: placeholder("baseline_ref"),
    worktrack_id: args.worktrackId || placeholder("worktrack_id"),
    branch: args.branch || placeholder("branch"),
    status: placeholder("status"),
    current_phase: placeholder("current_phase"),
    gate_round: placeholder("gate_round"),
    repo_scope: "active",
    worktrack_scope: "closed",
    needs_programmer_approval: placeholder("needs_programmer_approval"),
    reason: placeholder("reason"),
    why: placeholder("why"),
    pass: "pending",
  };
  if (Object.prototype.hasOwnProperty.call(directValues, key)) return directValues[key];
  const linkedTemplateId = LINKED_PATH_FIELDS[key];
  if (linkedTemplateId) {
    const linkedSpec = TEMPLATE_SPECS[linkedTemplateId];
    return selectedTemplateIds.has(linkedTemplateId) ? linkedSpec.outputRelpath.split(path.sep).join("/") : placeholder(key);
  }
  return placeholder(key);
}

function resolveBlankValue(section, args) {
  const aliasedKey = SECTION_VALUE_FIELDS[section];
  if (aliasedKey === "worktrack_id" && args.worktrackId) return args.worktrackId;
  if (aliasedKey === "baseline_branch" && args.baselineBranch) return args.baselineBranch;
  return placeholder(section);
}

function renderFrontmatter(spec, args) {
  const frontmatter = {
    title: spec.title,
    artifact_type: spec.artifactType,
    generated_from: sourceDisplayPath(spec),
    updated: args.updated,
    owner: args.owner || placeholder("owner"),
  };
  const rendered = ["---"];
  for (const [key, value] of Object.entries(frontmatter)) {
    rendered.push(`${key}: ${JSON.stringify(String(value))}`);
  }
  rendered.push("---");
  return rendered.join("\n");
}

function renderTemplate(spec, selectedTemplateIds, args) {
  const issues = validateTemplateSource(spec);
  if (issues.length) {
    throw new DeployAwError(`${sourceDisplayPath(spec)} failed validation: ${issues.join("; ")}`);
  }
  const sourceText = fs.readFileSync(sourcePath(spec), "utf8");
  const renderedLines = [];
  let currentSection = "";
  let h1Seen = false;
  let noteRewritten = false;
  for (const line of sourceText.split(/\r?\n/)) {
    if (line.startsWith("# ")) {
      h1Seen = true;
      renderedLines.push(line);
      continue;
    }
    if (spec.injectInstanceNote && h1Seen && !noteRewritten && line.startsWith("> ")) {
      renderedLines.push(`> ${spec.instanceNote}`);
      noteRewritten = true;
      continue;
    }
    if (line.startsWith("## ")) {
      currentSection = line.slice(3).trim();
      renderedLines.push(line);
      continue;
    }
    const keyedMatch = line.match(KEYED_LINE_PATTERN);
    if (keyedMatch) {
      const [, indent, key] = keyedMatch;
      renderedLines.push(`${indent}- ${key}: ${resolveKeyedValue(key, selectedTemplateIds, args)}`);
      continue;
    }
    const checkboxMatch = line.match(CHECKBOX_LINE_PATTERN);
    if (checkboxMatch) {
      const index = checkboxMatch[1];
      renderedLines.push(`${index}. [ ] ${placeholder(`task_${index}`)}`);
      continue;
    }
    if (line === "-" || line === "- ") {
      renderedLines.push(`- ${resolveBlankValue(currentSection, args)}`);
      continue;
    }
    renderedLines.push(line);
  }
  return `${renderFrontmatter(spec, args)}\n\n${renderedLines.join("\n").trimEnd()}\n`;
}

function preflightOutputPaths(selectedSpecs, staticAssets, outputRoot, force) {
  for (const spec of [...selectedSpecs, ...staticAssets]) {
    const outputPath = path.join(outputRoot, spec.outputRelpath);
    if (fs.existsSync(outputPath) && !force) {
      throw new DeployAwError(`refusing to overwrite existing file without --force: ${outputPath}`);
    }
  }
}

function writeRenderedTemplate(spec, renderedText, outputRoot, force, dryRun) {
  const outputPath = path.join(outputRoot, spec.outputRelpath);
  if (fs.existsSync(outputPath) && !force) {
    throw new DeployAwError(`refusing to overwrite existing file without --force: ${outputPath}`);
  }
  if (dryRun) {
    console.log(`would write ${outputPath}`);
    return;
  }
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, renderedText, "utf8");
  console.log(`wrote ${outputPath}`);
}

function copyStaticAsset(spec, outputRoot, force, dryRun) {
  const outputPath = path.join(outputRoot, spec.outputRelpath);
  if (fs.existsSync(outputPath) && !force) {
    throw new DeployAwError(`refusing to overwrite existing file without --force: ${outputPath}`);
  }
  if (dryRun) {
    console.log(`would copy ${outputPath}`);
    return;
  }
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.copyFileSync(sourcePath(spec), outputPath);
  console.log(`copied ${outputPath}`);
}

function claudeSkillRootFor(args, deployPath) {
  return path.resolve(args.claudeRoot || path.join(deployPath, DEFAULT_CLAUDE_SKILL_ROOT));
}

function claudeSkillTargetDirFor(args, deployPath) {
  return path.join(claudeSkillRootFor(args, deployPath), DEFAULT_CLAUDE_SKILL_NAME);
}

function shouldCopySkillPackagePath(filePath) {
  const relativeParts = path.relative(SKILL_ROOT, filePath).split(path.sep);
  if (relativeParts.some((part) => SKILL_PACKAGE_EXCLUDED_NAMES.has(part))) return false;
  const stat = fs.lstatSync(filePath);
  return stat.isFile() && ![".pyc", ".pyo"].includes(path.extname(filePath));
}

function collectSkillPackageFiles() {
  const packageFiles = [];
  function walk(root) {
    for (const name of fs.readdirSync(root).sort()) {
      const child = path.join(root, name);
      const stat = fs.lstatSync(child);
      if (stat.isDirectory()) walk(child);
      else if (shouldCopySkillPackagePath(child)) packageFiles.push([child, path.relative(SKILL_ROOT, child)]);
    }
  }
  walk(SKILL_ROOT);
  if (!packageFiles.length) throw new DeployAwError(`no skill package files found under ${SKILL_ROOT}`);
  return packageFiles;
}

function absolutePathWithoutResolve(rawPath) {
  return path.resolve(rawPath);
}

function isCurrentSkillDir(candidatePath) {
  if (fs.existsSync(candidatePath) && fs.lstatSync(candidatePath).isSymbolicLink()) return false;
  return absolutePathWithoutResolve(candidatePath) === absolutePathWithoutResolve(SKILL_ROOT) ||
    (fs.existsSync(candidatePath) && fs.realpathSync(candidatePath) === fs.realpathSync(SKILL_ROOT));
}

function preflightClaudeSkillTargetPath(targetSkillDir) {
  const parts = path.resolve(targetSkillDir).split(path.sep);
  let candidate = parts[0] === "" ? path.sep : parts[0];
  for (const part of parts.slice(candidate === path.sep ? 1 : 1)) {
    candidate = path.join(candidate, part);
    if (fs.existsSync(candidate)) {
      const stat = fs.lstatSync(candidate);
      if (stat.isSymbolicLink() && !fs.statSync(candidate).isDirectory()) {
        throw new DeployAwError(`Claude skill target ancestor is not a directory: ${candidate}`);
      }
      if (!stat.isSymbolicLink() && !stat.isDirectory()) {
        throw new DeployAwError(`Claude skill target ancestor is not a directory: ${candidate}`);
      }
    }
  }
}

function walkExistingTreeNoSymlink(root) {
  if (!fs.existsSync(root)) return;
  for (const name of fs.readdirSync(root)) {
    const child = path.join(root, name);
    const stat = fs.lstatSync(child);
    if (stat.isSymbolicLink()) {
      throw new DeployAwError(`refusing to install through symlinked Claude skill directory: ${child}`);
    }
    if (stat.isDirectory()) walkExistingTreeNoSymlink(child);
  }
}

function preflightClaudeSkillCopyTarget(targetPath, targetSkillDir, force) {
  if (fs.existsSync(targetPath) && fs.lstatSync(targetPath).isSymbolicLink()) {
    throw new DeployAwError(`refusing to overwrite symlinked Claude skill file: ${targetPath}`);
  }
  let candidate = path.dirname(targetPath);
  while (path.resolve(candidate).startsWith(path.resolve(targetSkillDir))) {
    if (fs.existsSync(candidate)) {
      const stat = fs.lstatSync(candidate);
      if (stat.isSymbolicLink()) {
        throw new DeployAwError(`refusing to install through symlinked Claude skill directory: ${candidate}`);
      }
      if (!stat.isDirectory()) {
        throw new DeployAwError(`Claude skill target ancestor is not a directory: ${candidate}`);
      }
    }
    if (path.resolve(candidate) === path.resolve(targetSkillDir)) break;
    candidate = path.dirname(candidate);
  }
  if (fs.existsSync(targetPath)) {
    const stat = fs.lstatSync(targetPath);
    if (stat.isDirectory()) throw new DeployAwError(`Claude skill target file path is a directory: ${targetPath}`);
    if (!force) throw new DeployAwError(`refusing to overwrite existing Claude skill file without --force: ${targetPath}`);
  }
}

function preflightClaudeSkillInstall(packageFiles, targetSkillDir, force) {
  if (fs.existsSync(targetSkillDir) && fs.lstatSync(targetSkillDir).isSymbolicLink()) {
    throw new DeployAwError(`refusing to install into symlinked Claude skill dir: ${targetSkillDir}`);
  }
  preflightClaudeSkillTargetPath(targetSkillDir);
  if (isCurrentSkillDir(targetSkillDir)) return;
  if (fs.existsSync(targetSkillDir) && !fs.statSync(targetSkillDir).isDirectory()) {
    throw new DeployAwError(`Claude skill target exists but is not a directory: ${targetSkillDir}`);
  }
  walkExistingTreeNoSymlink(targetSkillDir);
  for (const [, relativePath] of packageFiles) {
    preflightClaudeSkillCopyTarget(path.join(targetSkillDir, relativePath), targetSkillDir, force);
  }
}

function installClaudeSkillPackage(packageFiles, targetSkillDir, force, dryRun) {
  preflightClaudeSkillInstall(packageFiles, targetSkillDir, force);
  if (isCurrentSkillDir(targetSkillDir)) {
    console.log(`Claude skill already installed at ${targetSkillDir}`);
    return;
  }
  if (dryRun) {
    console.log(`would install Claude skill ${DEFAULT_CLAUDE_SKILL_NAME} -> ${targetSkillDir}`);
    for (const [, relativePath] of packageFiles) console.log(`would copy ${path.join(targetSkillDir, relativePath)}`);
    return;
  }
  for (const [source, relativePath] of packageFiles) {
    const targetPath = path.join(targetSkillDir, relativePath);
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    preflightClaudeSkillCopyTarget(targetPath, targetSkillDir, force);
    fs.copyFileSync(source, targetPath);
    if (fs.lstatSync(targetPath).isSymbolicLink()) {
      throw new DeployAwError(`refusing to chmod symlinked Claude skill file: ${targetPath}`);
    }
    fs.chmodSync(targetPath, 0o644);
  }
  console.log(`installed Claude skill ${DEFAULT_CLAUDE_SKILL_NAME} -> ${targetSkillDir}`);
}

function runList(jsonMode) {
  if (jsonMode) {
    const payload = {
      profiles: Object.fromEntries(Object.entries(PROFILE_TEMPLATES).map(([profileName, templateIds]) => [
        profileName,
        {
          templates: templateIds,
          static_assets: PROFILE_STATIC_ASSETS[profileName] || [],
        },
      ])),
      templates: Object.fromEntries(Object.entries(TEMPLATE_SPECS).map(([templateId, spec]) => [
        templateId,
        {
          source: sourceDisplayPath(spec),
          output: spec.outputRelpath,
          artifact_type: spec.artifactType,
        },
      ])),
      static_assets: Object.fromEntries(Object.entries(STATIC_ASSET_SPECS).map(([assetId, spec]) => [
        assetId,
        {
          source: sourceDisplayPath(spec),
          output: spec.outputRelpath,
        },
      ])),
    };
    console.log(JSON.stringify(payload, null, 2));
    return 0;
  }
  console.log("profiles:");
  for (const [profileName, templateIds] of Object.entries(PROFILE_TEMPLATES)) {
    console.log(`  - ${profileName}: render [${templateIds.join(", ")}] copy [${(PROFILE_STATIC_ASSETS[profileName] || []).join(", ") || "(none)"}]`);
  }
  console.log("templates:");
  for (const [templateId, spec] of Object.entries(TEMPLATE_SPECS)) {
    console.log(`  - ${templateId}: ${sourceDisplayPath(spec)} -> ${spec.outputRelpath}`);
  }
  console.log("static assets:");
  for (const [assetId, spec] of Object.entries(STATIC_ASSET_SPECS)) {
    console.log(`  - ${assetId}: ${sourceDisplayPath(spec)} -> ${spec.outputRelpath}`);
  }
  return 0;
}

function runValidate(selectedSpecs, staticAssets) {
  let hadIssue = false;
  for (const spec of selectedSpecs) {
    const issues = validateTemplateSource(spec);
    if (issues.length) {
      hadIssue = true;
      console.log(`[${spec.templateId}] invalid: ${sourceDisplayPath(spec)}`);
      for (const issue of issues) console.log(`  - ${issue}`);
    } else {
      console.log(`[${spec.templateId}] ok: ${sourceDisplayPath(spec)}`);
    }
  }
  for (const spec of staticAssets) {
    const issues = validateStaticAssetSource(spec);
    if (issues.length) {
      hadIssue = true;
      console.log(`[${spec.assetId}] invalid: ${sourceDisplayPath(spec)}`);
      for (const issue of issues) console.log(`  - ${issue}`);
    } else {
      console.log(`[${spec.assetId}] ok: ${sourceDisplayPath(spec)}`);
    }
  }
  return hadIssue ? 1 : 0;
}

function ensureGitignoreServo(deployPath, dryRun) {
  const gitignorePath = path.join(deployPath, ".gitignore");
  const servoEntry = `${DEFAULT_AW_DIRNAME}/`;
  let existing = "";
  if (fs.existsSync(gitignorePath)) {
    existing = fs.readFileSync(gitignorePath, "utf8");
  }
  const lines = existing.split(/\r?\n/);
  const alreadyPresent = lines.some((line) => line.trim() === servoEntry);
  if (alreadyPresent) {
    console.log(`[gitignore] ${servoEntry} already present`);
    return;
  }
  const updated = existing.trimEnd() + "\n" + servoEntry + "\n";
  if (dryRun) {
    console.log(`[gitignore] dry-run: would add ${servoEntry} to ${gitignorePath}`);
    return;
  }
  fs.writeFileSync(gitignorePath, updated, "utf8");
  console.log(`[gitignore] added ${servoEntry} to ${gitignorePath}`);
}

function runGenerate(selectedSpecs, staticAssets, args) {
  const deployPath = resolveDeployPath(args);
  args.deployPath = deployPath;
  const outputRoot = path.join(deployPath, DEFAULT_AW_DIRNAME);
  const installClaudeSkill = args.installClaudeSkill;
  const claudePackageFiles = installClaudeSkill ? collectSkillPackageFiles() : [];
  const claudeTargetDir = installClaudeSkill ? claudeSkillTargetDirFor(args, deployPath) : null;
  args.repo = args.repo || path.basename(deployPath);
  args.baselineBranch = resolveBaselineBranch(args, deployPath);
  const selectedTemplateIds = new Set(selectedSpecs.map((spec) => spec.templateId));
  const renderedTemplates = selectedSpecs.map((spec) => [
    spec,
    renderTemplate(spec, selectedTemplateIds, args),
  ]);
  for (const spec of staticAssets) {
    const issues = validateStaticAssetSource(spec);
    if (issues.length) throw new DeployAwError(`${sourceDisplayPath(spec)} failed validation: ${issues.join("; ")}`);
  }
  preflightOutputPaths(selectedSpecs, staticAssets, outputRoot, args.force);
  if (installClaudeSkill) preflightClaudeSkillInstall(claudePackageFiles, claudeTargetDir, args.force);
  ensureGitignoreServo(deployPath, args.dryRun);
  for (const [spec, rendered] of renderedTemplates) writeRenderedTemplate(spec, rendered, outputRoot, args.force, args.dryRun);
  for (const spec of staticAssets) copyStaticAsset(spec, outputRoot, args.force, args.dryRun);
  if (installClaudeSkill) installClaudeSkillPackage(claudePackageFiles, claudeTargetDir, args.force, args.dryRun);
  return 0;
}

function runInstallClaudeSkill(args) {
  const deployPath = resolveDeployPath(args);
  const packageFiles = collectSkillPackageFiles();
  const targetSkillDir = claudeSkillTargetDirFor(args, deployPath);
  installClaudeSkillPackage(packageFiles, targetSkillDir, args.force, args.dryRun);
  return 0;
}

function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.mode === "list") return runList(args.json);
  if (args.mode === "install-claude-skill") return runInstallClaudeSkill(args);
  const selectedSpecs = resolveSelectedSpecs(args);
  const staticAssets = resolveStaticAssetSpecs(args);
  if (args.mode === "validate") return runValidate(selectedSpecs, staticAssets);
  if (args.mode === "generate") return runGenerate(selectedSpecs, staticAssets, args);
  throw new DeployAwError(`unsupported mode: ${args.mode}`);
}

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    if (error instanceof DeployAwError) {
      console.error(`error: ${error.message}`);
      process.exitCode = 1;
    } else {
      throw error;
    }
  }
}

module.exports = {
  TEMPLATE_SPECS,
  STATIC_ASSET_SPECS,
  parseArgs,
  resolveSelectedSpecs,
  validateTemplateSource,
  validateStaticAssetSource,
  renderTemplate,
  main,
};
