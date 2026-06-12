---
title: "Composite Acceptance Report: {{milestone_id}}"
artifact_type: composite-acceptance-report
milestone_id: "{{milestone_id}}"
updated: "{{updated}}"
---

# Composite Acceptance Report

## Summary

- milestone_id: {{milestone_id}}
- review_depth: standard | deep
- git_checkpoint: {{git_checkpoint}}
- composite_acceptance_verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- milestone_gate_effect: pass | soft-fail | hard-fail | blocked
- final_acceptance_ready: yes | no
- programmer_final_acceptance_required: yes

## Dispatch / Fallback

- subagent_dispatch_available: yes | no | unknown
- required_lane_count: 6
- delegated_lane_count: 0
- current_carrier_lane_count: 0
- fallback_summary: none

## Lanes

### code-review

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

### feature-completeness

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

### related-influence

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

### intent-completeness

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

### operator-simulation

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

### professional-review

- carrier: subagent | current-carrier | human
- delegation_attempted: true | false
- fallback_reason: null
- verdict: accepted | accepted_with_residual_risk | needs_followup_worktrack | blocked
- severity: none | low | medium | high
- evidence_refs:
  - pending
- findings:
  - pending
- residual_risks:
  - pending
- required_followups:
  - pending

## Gate Mapping

- accepted lanes contribute to Milestone Gate pass.
- accepted_with_residual_risk contributes to pass only when residual risks are recorded for programmer handback.
- needs_followup_worktrack blocks final acceptance unless the programmer explicitly accepts deferral or adds the follow-up worktrack.
- blocked blocks Milestone Gate.
- any high severity lane finding blocks final acceptance.

## Programmer Handback

- handback_required: yes
- final_acceptance_owner: programmer
- harness_may_mark_completed_without_programmer_acceptance: no
- recommended_next_action: programmer final acceptance | add follow-up worktrack | recover blocked lane
