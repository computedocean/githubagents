# Playbook: final quality review

Used by every agent before it reports. This expands the "Before you finish" shared rule.

## Checklist

- [ ] The request is answered, or the reason it could not be is stated.
- [ ] Every completion criterion in the profile is met, or the unmet ones are listed.
- [ ] Every `path:line` and URL cited was opened in this task.
- [ ] Every command result quoted was actually run in this task. Nothing is predicted.
- [ ] Facts, assumptions, recommendations, and open questions are kept separate.
- [ ] No secret value, token, or personal data appears in the output or the diff.
- [ ] Read-only agents: no files changed. Editing agents: changes are within the profile's boundary.
- [ ] No temporary files, debug output, or generated artifacts are left behind.
- [ ] No action from the shared rules' "Stop and ask a human first" list was taken without approval.
- [ ] Work outside this agent's scope is handed off by name, not done.

## Self-critique questions

- What would a sceptical reviewer check first, and did I check it?
- Which claim am I least sure of? Is it labelled that way?
- Did I take the narrowest reasonable reading of the request? Is that assumption stated?
