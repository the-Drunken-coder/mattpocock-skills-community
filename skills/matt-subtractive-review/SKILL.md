---
name: matt-subtractive-review
description: Review a change or design for unnecessary concepts, code, process, and dependencies that can be removed without losing required behavior. Use when a result feels overbuilt or after a feature is working.
---

# Subtractive review

Look for what the change does not need. This is a review lens, not permission to delete blindly.

For each meaningful piece of the change, ask:

- Which observable behavior or contract does it protect?
- Is that protection already provided elsewhere?
- Is it duplicated, speculative, obsolete, or accidental?
- What is the smallest evidence needed to remove it safely?

Review implementation, tests, configuration, dependencies, documentation, and workflow steps. Prefer one coherent deletion over leaving forwarding wrappers, unused flags, compatibility shells, or dead prose. Preserve security controls, observability, compatibility, and operational safeguards when evidence says they matter.

Report candidates as `remove`, `collapse`, `retain`, or `needs evidence`, with the protected behavior and validation needed. If the user approves removals, hand the execution to `matt-refactor`.
