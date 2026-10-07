---
name: matt-red-team
description: Adversarially review a specification before implementation. Use when a plan needs pressure-testing for ambiguity, failure modes, unsafe assumptions, or missing acceptance evidence.
---

# Red team

Attack the proposed behavior before anyone builds it. The purpose is to find expensive misunderstandings while they are still cheap to resolve.

## Review loop

1. Read the request, intent brief, specification, glossary, ADRs, and acceptance criteria that define the proposal.
2. Reconstruct the intended behavior and list the assumptions the proposal relies on.
3. Test the boundaries: empty, duplicate, delayed, repeated, concurrent, unauthorized, partially failed, migrated, and rolled-back cases where relevant.
4. Look for contradictions, missing ownership, unsafe defaults, unobservable success claims, and tests that could pass while the behavior is wrong.
5. Report findings with evidence, consequence, severity, and the smallest question or change that would resolve each one.

Do not redesign the proposal silently or manufacture unlikely edge cases. Separate confirmed contradictions from risks that need an answer. The user decides whether to change the specification. Stop when the remaining objections are either resolved, explicitly accepted, or out of scope.
