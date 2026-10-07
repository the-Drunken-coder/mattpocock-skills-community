---
name: matt-refactor
description: Simplify existing code or configuration while preserving required behavior. Use for deletion, dead-code removal, dependency removal, zero-based redesign, or behavior-preserving cleanup.
---

# Refactor

Use deletion as a design operation. The goal is the smallest understandable implementation that preserves the contract, not a smaller diff at any cost.

## Protocol

1. Name the contract. Read the target and its nearest callers, tests, docs, configuration, runtime paths, and public behavior. State what must remain.
2. Create a deletion ledger. Classify complexity as contract-bearing, duplicated, obsolete, accidental, or uncertain. Retain uncertain code until evidence resolves it.
3. Trace the removal through code, configuration, generated files, serialization, reflection, scripts, and documentation.
4. Delete one coherent slice and its exclusive enablers: unreachable branches, wrappers, flags, registrations, imports, and stale docs.
5. Prove the absence. Run the focused check, then the narrowest relevant test, typecheck, lint, build, or executable check available.
6. Report the preserved contract, what disappeared, why retained pieces earned their place, and the validation performed.

Preserve compatibility, security, observability, and operational safeguards unless the request changes them. Do not widen a cleanup into unrelated redesign. Apply the same ledger to prompts and skills: keep trigger branches, required steps, completion criteria, and safety boundaries that change behavior.
